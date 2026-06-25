"""DAG execution engine — runs workflows by dispatching nodes in dependency order.

Supports review-gate pause/resume: when a ReviewGateNode returns
``pending_review``, the engine pauses the workflow and prevents downstream
nodes from executing.  A human can later approve, reject, or request changes,
and the engine will resume (or abort) accordingly.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4

from decision_system.workflow_engine.engine.dag import DAGValidator, TopologicalSort
from decision_system.workflow_engine.engine.events import ExecutionEvent
from decision_system.workflow_engine.models import (
    ErrorPolicy,
    ExecutionContext,
    ExecutionState,
    NodeConfig,
    NodeExecutionState,
    RetryConfig,
    WorkflowDefinition,
    WorkflowNode,
)
from decision_system.workflow_engine.nodes.registry import NodeRegistry
from decision_system.workflow_engine.providers.store import ProviderStore
from decision_system.workflow_engine.stores.base import (
    ExecutionStore,
    WorkflowStore,
)


class DAGEngine:
    """Main workflow execution engine.

    Takes a WorkflowDefinition, validates the DAG, topologically sorts it,
    and executes nodes layer by layer with optional parallel dispatch.
    Supports review-gate pause/resume.
    """

    def __init__(
        self,
        registry: NodeRegistry,
        workflow_store: WorkflowStore,
        execution_store: ExecutionStore,
        provider_store: ProviderStore | None = None,
    ) -> None:
        self.registry = registry
        self.workflow_store = workflow_store
        self.execution_store = execution_store
        self._provider_store = provider_store or ProviderStore()
        self._event_handlers: list[Callable[[ExecutionEvent], None]] = []

    def on_event(self, handler: Callable[[ExecutionEvent], None]) -> None:
        """Register an event handler for execution events."""
        self._event_handlers.append(handler)

    def _emit(self, event: ExecutionEvent) -> None:
        """Emit an event to all registered handlers."""
        for handler in self._event_handlers:
            try:
                handler(event)
            except Exception:
                pass

    async def execute(
        self,
        workflow: WorkflowDefinition,
        global_inputs: dict[str, Any] | None = None,
        workspace_id: str | None = None,
        schedule_id: str | None = None,
    ) -> ExecutionState:
        """Execute a workflow definition. Returns the final ExecutionState."""
        now = datetime.now(timezone.utc)
        state = ExecutionState(
            execution_id=str(uuid4()),
            workflow_id=workflow.id,
            workspace_id=workspace_id or workflow.workspace_id,
            status="running",
            started_at=now,
            node_states={n.id: NodeExecutionState(node_id=n.id) for n in workflow.nodes},
        )
        self.execution_store.save(state)

        self._emit(
            ExecutionEvent(
                execution_id=state.execution_id,
                event_type="workflow_started",
                data={"workflow_id": workflow.id, "workflow_name": workflow.name},
            )
        )

        try:
            # Validate
            errors = DAGValidator.validate(workflow)
            if errors:
                return self._fail_workflow(state, "; ".join(str(e) for e in errors))

            # Topo sort
            layers = TopologicalSort.sort(workflow)
            node_configs = {n.id: n for n in workflow.nodes}

            # Build dependency map for input routing
            deps: dict[str, list[tuple[str, str, str]]] = {n.id: [] for n in workflow.nodes}
            for conn in workflow.connections:
                if conn.target_node in deps:
                    deps[conn.target_node].append(
                        (conn.source_node, conn.source_output, conn.target_input)
                    )

            # Execute layer by layer
            for layer_idx, layer in enumerate(layers):
                if state.status == "failed":
                    break

                tasks = []
                for node_id in layer:
                    # If this node is downstream of a paused review gate, skip it
                    node_has_paused_dep = False
                    for src_node, _, _ in deps[node_id]:
                        src_state = state.node_states.get(src_node)
                        if src_state and src_state.status == "awaiting_review":
                            node_has_paused_dep = True
                            break
                    if node_has_paused_dep:
                        continue

                    tasks.append(
                        self._execute_node(
                            state,
                            node_id,
                            node_configs[node_id],
                            deps[node_id],
                            global_inputs,
                            schedule_id,
                        )
                    )

                if not tasks:
                    continue

                await asyncio.gather(*tasks)

                # After each layer, check for review-gate pause
                for node_id in layer:
                    ncfg = node_configs.get(node_id)
                    if ncfg and ncfg.type == "decision_system.review_gate":
                        ns = state.node_states.get(node_id)
                        if ns and ns.outputs and ns.outputs.get("status") == "pending_review":
                            await self._pause_for_review(
                                state, node_id, ns, workflow, layers, layer_idx
                            )

                # If paused for review, stop executing further layers
                if state.status == "awaiting_review":
                    break

            if state.status == "running":
                state.status = "completed"
                state.completed_at = datetime.now(timezone.utc)
                self.execution_store.save(state)
            elif state.status in ("failed", "rejected"):
                state.completed_at = datetime.now(timezone.utc)
                self.execution_store.save(state)
            elif state.status != "awaiting_review":
                self.execution_store.save(state)
            self._emit(
                ExecutionEvent(
                    execution_id=state.execution_id,
                    event_type="workflow_completed",
                    data={"status": state.status},
                )
            )

        except Exception as exc:
            self._fail_workflow(state, f"{type(exc).__name__}: {exc}")

        return state

    async def resume(
        self,
        execution_id: str,
        action: str = "resume",
        modified_data: dict[str, Any] | None = None,
    ) -> ExecutionState | None:
        """Resume a paused execution after review resolution.

        Args:
            execution_id: The ID of the paused execution.
            action: "resume" to continue, "reject" to end.
            modified_data: Optional modified data from reviewer.

        Returns:
            The updated ExecutionState, or None if not found or not paused.
        """
        state = self.execution_store.load(execution_id)
        if state is None:
            return None
        if state.status != "awaiting_review":
            return None

        if action == "reject":
            state.status = "rejected"
            state.completed_at = datetime.now(timezone.utc)
            self.execution_store.save(state)
            self._emit(
                ExecutionEvent(
                    execution_id=execution_id,
                    event_type="workflow_rejected",
                    data={"reason": "Review rejected"},
                )
            )
            return state

        # Resume: load the workflow and continue from paused node
        workflow = self.workflow_store.load(state.workflow_id)
        if workflow is None:
            state.status = "failed"
            state.error = "Workflow definition not found for resume"
            state.completed_at = datetime.now(timezone.utc)
            self.execution_store.save(state)
            return state

        # Mark the paused node as completed with reviewer's data
        paused_node_id = state.paused_node_id
        if paused_node_id and paused_node_id in state.node_states:
            ns = state.node_states[paused_node_id]
            ns.status = "completed"
            ns.completed_at = datetime.now(timezone.utc)
            if modified_data is not None:
                ns.outputs = ns.outputs or {}
                ns.outputs["data"] = modified_data
                ns.outputs["approved"] = True

        state.status = "running"
        state.review_id = None
        self.execution_store.save(state)

        self._emit(
            ExecutionEvent(
                execution_id=execution_id,
                event_type="workflow_resumed",
                data={"paused_node_id": paused_node_id},
            )
        )

        # Continue executing remaining layers
        try:
            layers = TopologicalSort.sort(workflow)
            node_configs = {n.id: n for n in workflow.nodes}

            deps: dict[str, list[tuple[str, str, str]]] = {n.id: [] for n in workflow.nodes}
            for conn in workflow.connections:
                if conn.target_node in deps:
                    deps[conn.target_node].append(
                        (conn.source_node, conn.source_output, conn.target_input)
                    )

            for layer in layers:
                if state.status == "failed":
                    break

                tasks = []
                for node_id in layer:
                    ns = state.node_states.get(node_id)
                    # Skip already completed nodes (including the resume point)
                    if ns and ns.status == "completed":
                        continue
                    if ns and ns.status == "awaiting_review":
                        continue

                    # Skip nodes with paused dependencies
                    node_has_paused_dep = False
                    for src_node, _, _ in deps.get(node_id, []):
                        src_state = state.node_states.get(src_node)
                        if src_state and src_state.status == "awaiting_review":
                            node_has_paused_dep = True
                            break
                    if node_has_paused_dep:
                        continue

                    tasks.append(
                        self._execute_node(
                            state,
                            node_id,
                            node_configs[node_id],
                            deps.get(node_id, []),
                            {},
                            None,
                        )
                    )

                if not tasks:
                    continue

                await asyncio.gather(*tasks)

                # Check for new review gates
                for node_id in layer:
                    ncfg = node_configs.get(node_id)
                    if ncfg and ncfg.type == "decision_system.review_gate":
                        ns = state.node_states.get(node_id)
                        if ns and ns.outputs and ns.outputs.get("status") == "pending_review":
                            await self._pause_for_review(state, node_id, ns, workflow, layers, 0)

                if state.status == "awaiting_review":
                    break

            if state.status == "running":
                state.status = "completed"
                state.completed_at = datetime.now(timezone.utc)
                self.execution_store.save(state)
            elif state.status in ("failed", "rejected"):
                state.completed_at = datetime.now(timezone.utc)
                self.execution_store.save(state)
            elif state.status != "awaiting_review":
                self.execution_store.save(state)

        except Exception as exc:
            self._fail_workflow(state, f"{type(exc).__name__}: {exc}")

        return state

    async def _pause_for_review(
        self,
        state: ExecutionState,
        node_id: str,
        ns: NodeExecutionState,
        workflow: WorkflowDefinition,
        layers: list[list[str]],
        current_layer_idx: int,
    ) -> None:
        """Pause the workflow for a review gate."""
        outputs = ns.outputs or {}
        ns.status = "awaiting_review"
        state.status = "awaiting_review"
        state.review_id = outputs.get("review_id")
        state.paused_node_id = node_id
        state.pending_inputs = ns.inputs or {}
        state.review_instructions = outputs.get("instructions", "")
        state.review_created_at = datetime.now(timezone.utc)

        # Record downstream nodes that should not start
        downstream = []
        for layer in layers[current_layer_idx + 1 :]:
            for nid in layer:
                downstream.append(nid)
        state.downstream_nodes_not_started = downstream

        self.execution_store.save(state)
        self._emit(
            ExecutionEvent(
                execution_id=state.execution_id,
                event_type="workflow_paused",
                node_id=node_id,
                data={
                    "review_id": state.review_id,
                    "reason": "awaiting_review",
                },
            )
        )

    def _fail_workflow(self, state: ExecutionState, error: str) -> ExecutionState:
        """Mark execution as failed and persist."""
        state.status = "failed"
        state.error = error
        state.completed_at = datetime.now(timezone.utc)
        self.execution_store.save(state)
        self._emit(
            ExecutionEvent(
                execution_id=state.execution_id,
                event_type="workflow_failed",
                data={"error": error},
            )
        )
        return state

    async def _execute_node(
        self,
        state: ExecutionState,
        node_id: str,
        config: NodeConfig,
        dependencies: list[tuple[str, str, str]],
        global_inputs: dict[str, Any] | None,
        schedule_id: str | None = None,
    ) -> None:
        """Execute a single node: resolve inputs, dispatch, handle errors."""
        ns = state.node_states[node_id]
        ns.status = "running"
        ns.started_at = datetime.now(timezone.utc)
        ns.attempts += 1
        self.execution_store.save(state)

        self._emit(
            ExecutionEvent(
                execution_id=state.execution_id,
                event_type="node_started",
                node_id=node_id,
                data={"node_type": config.type},
            )
        )

        try:
            # Collect inputs from upstream nodes
            inputs: dict[str, Any] = {}
            if global_inputs:
                inputs.update(global_inputs)
            for src_node, src_output, target_input in dependencies:
                src_state = state.node_states.get(src_node)
                if src_state and src_state.outputs:
                    if target_input == "default":
                        inputs.update(src_state.outputs)
                    else:
                        inputs[target_input] = src_state.outputs.get(src_output)

            ns.inputs = inputs

            # Instantiate and execute
            node_cls = self.registry.get(config.type)
            ctx = ExecutionContext(
                workflow_id=state.workflow_id,
                execution_id=state.execution_id,
                schedule_id=schedule_id,
                workspace_id=state.workspace_id,
            )
            ctx._provider_store = self._provider_store
            node: WorkflowNode = node_cls(id=node_id, type=config.type, config=config.config)
            outputs = await node.execute(inputs, ctx)

            ns.outputs = outputs
            ns.status = "completed"
            ns.completed_at = datetime.now(timezone.utc)
            self.execution_store.save(state)

            self._emit(
                ExecutionEvent(
                    execution_id=state.execution_id,
                    event_type="node_completed",
                    node_id=node_id,
                    data={"outputs": outputs},
                )
            )

        except Exception as exc:
            error_msg = f"{type(exc).__name__}: {exc}"
            ns.error = error_msg
            ns.completed_at = datetime.now(timezone.utc)

            if config.error_policy == ErrorPolicy.SKIP:
                ns.status = "skipped"
                self.execution_store.save(state)
                self._emit(
                    ExecutionEvent(
                        execution_id=state.execution_id,
                        event_type="node_failed",
                        node_id=node_id,
                        data={"error": error_msg, "action": "skipped"},
                    )
                )

            elif config.error_policy == ErrorPolicy.RETRY:
                retry_cfg = config.retry_config or RetryConfig()
                if ns.attempts < retry_cfg.max_attempts:
                    delay = min(
                        retry_cfg.base_delay * (retry_cfg.backoff_multiplier ** (ns.attempts - 1)),
                        retry_cfg.max_delay,
                    )
                    await asyncio.sleep(delay)
                    await self._execute_node(
                        state, node_id, config, dependencies, global_inputs, schedule_id
                    )
                else:
                    ns.status = "failed"
                    state.status = "failed"
                    state.error = error_msg
                    self.execution_store.save(state)
                    self._emit(
                        ExecutionEvent(
                            execution_id=state.execution_id,
                            event_type="node_failed",
                            node_id=node_id,
                            data={"error": error_msg, "action": "failed"},
                        )
                    )

            elif config.error_policy == ErrorPolicy.FAIL_NODE:
                ns.status = "failed"
                self.execution_store.save(state)
                self._emit(
                    ExecutionEvent(
                        execution_id=state.execution_id,
                        event_type="node_failed",
                        node_id=node_id,
                        data={"error": error_msg, "action": "failed_continue"},
                    )
                )

            else:  # FAIL_WORKFLOW (default)
                ns.status = "failed"
                state.status = "failed"
                state.error = error_msg
                self.execution_store.save(state)
                self._emit(
                    ExecutionEvent(
                        execution_id=state.execution_id,
                        event_type="node_failed",
                        node_id=node_id,
                        data={"error": error_msg, "action": "failed_workflow"},
                    )
                )
