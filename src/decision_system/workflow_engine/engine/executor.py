"""DAG execution engine — runs workflows by dispatching nodes in dependency order."""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4

from decision_system.workflow_engine.models import (
    WorkflowDefinition, NodeConfig, ExecutionState, NodeExecutionState,
    ExecutionContext, ErrorPolicy, RetryConfig,
)
from decision_system.workflow_engine.engine.dag import DAGValidator, TopologicalSort
from decision_system.workflow_engine.engine.events import ExecutionEvent
from decision_system.workflow_engine.nodes.registry import NodeRegistry
from decision_system.workflow_engine.stores.base import (
    WorkflowStore, ExecutionStore,
)


class DAGEngine:
    """Main workflow execution engine.

    Takes a WorkflowDefinition, validates the DAG, topologically sorts it,
    and executes nodes layer by layer with optional parallel dispatch.
    """

    def __init__(
        self,
        registry: NodeRegistry,
        workflow_store: WorkflowStore,
        execution_store: ExecutionStore,
    ) -> None:
        self.registry = registry
        self.workflow_store = workflow_store
        self.execution_store = execution_store
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
    ) -> ExecutionState:
        """Execute a workflow definition. Returns the final ExecutionState."""
        state = ExecutionState(
            execution_id=str(uuid4()),
            workflow_id=workflow.id,
            status="running",
            started_at=datetime.now(timezone.utc),
            node_states={n.id: NodeExecutionState(node_id=n.id) for n in workflow.nodes},
        )
        self.execution_store.save(state)

        try:
            # Validate
            errors = DAGValidator.validate(workflow)
            if errors:
                error_msg = "; ".join(str(e) for e in errors)
                state.status = "failed"
                state.error = error_msg
                state.completed_at = datetime.now(timezone.utc)
                self.execution_store.save(state)
                self._emit(ExecutionEvent(
                    execution_id=state.execution_id,
                    event_type="workflow_failed",
                    data={"error": error_msg},
                ))
                return state

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
            for layer in layers:
                tasks = []
                for node_id in layer:
                    tasks.append(self._execute_node(
                        state, node_id, node_configs[node_id],
                        deps[node_id], global_inputs,
                    ))
                # Wait for all nodes in this layer
                await asyncio.gather(*tasks)

                # Check if we should stop (fail_workflow policy triggered)
                if state.status == "failed":
                    break

            if state.status == "running":
                state.status = "completed"
            state.completed_at = datetime.now(timezone.utc)
            self.execution_store.save(state)
            self._emit(ExecutionEvent(
                execution_id=state.execution_id,
                event_type="workflow_completed",
                data={"status": state.status},
            ))

        except Exception as exc:
            state.status = "failed"
            state.error = str(exc)
            state.completed_at = datetime.now(timezone.utc)
            self.execution_store.save(state)
            self._emit(ExecutionEvent(
                execution_id=state.execution_id,
                event_type="workflow_failed",
                data={"error": str(exc)},
            ))

        return state

    async def _execute_node(
        self,
        state: ExecutionState,
        node_id: str,
        config: NodeConfig,
        dependencies: list[tuple[str, str, str]],
        global_inputs: dict[str, Any] | None,
    ) -> None:
        """Execute a single node: resolve inputs, dispatch, handle errors."""
        ns = state.node_states[node_id]
        ns.status = "running"
        ns.started_at = datetime.now(timezone.utc)
        ns.attempts += 1
        self.execution_store.save(state)

        self._emit(ExecutionEvent(
            execution_id=state.execution_id,
            event_type="node_started",
            node_id=node_id,
            data={"node_type": config.type},
        ))

        try:
            # Collect inputs from upstream nodes
            inputs: dict[str, Any] = {}
            if global_inputs:
                inputs.update(global_inputs)
            for src_node, src_output, target_input in dependencies:
                src_state = state.node_states.get(src_node)
                if src_state and src_state.outputs:
                    if target_input == "default":
                        # Merge entire upstream output for default port
                        inputs.update(src_state.outputs)
                    else:
                        # Route named port value
                        inputs[target_input] = src_state.outputs.get(src_output)

            ns.inputs = inputs

            # Instantiate and execute
            node_cls = self.registry.get(config.type)
            ctx = ExecutionContext(
                workflow_id=state.workflow_id,
                execution_id=state.execution_id,
            )
            node = node_cls(id=node_id, type=config.type, config=config.config)
            outputs = await node.execute(inputs, ctx)

            ns.outputs = outputs
            ns.status = "completed"
            ns.completed_at = datetime.now(timezone.utc)
            self.execution_store.save(state)

            self._emit(ExecutionEvent(
                execution_id=state.execution_id,
                event_type="node_completed",
                node_id=node_id,
                data={"outputs": outputs},
            ))

        except Exception as exc:
            error_msg = f"{type(exc).__name__}: {exc}"
            ns.error = error_msg
            ns.completed_at = datetime.now(timezone.utc)

            if config.error_policy == ErrorPolicy.SKIP:
                ns.status = "skipped"
                self.execution_store.save(state)
                self._emit(ExecutionEvent(
                    execution_id=state.execution_id,
                    event_type="node_failed",
                    node_id=node_id,
                    data={"error": error_msg, "action": "skipped"},
                ))

            elif config.error_policy == ErrorPolicy.RETRY:
                retry_cfg = config.retry_config or RetryConfig()
                if ns.attempts < retry_cfg.max_attempts:
                    delay = min(
                        retry_cfg.base_delay * (retry_cfg.backoff_multiplier ** (ns.attempts - 1)),
                        retry_cfg.max_delay,
                    )
                    await asyncio.sleep(delay)
                    # Recursive retry
                    await self._execute_node(state, node_id, config, dependencies, global_inputs)
                else:
                    ns.status = "failed"
                    state.status = "failed"
                    state.error = error_msg
                    self.execution_store.save(state)
                    self._emit(ExecutionEvent(
                        execution_id=state.execution_id,
                        event_type="node_failed",
                        node_id=node_id,
                        data={"error": error_msg, "action": "failed"},
                    ))

            elif config.error_policy == ErrorPolicy.FAIL_NODE:
                ns.status = "failed"
                self.execution_store.save(state)
                self._emit(ExecutionEvent(
                    execution_id=state.execution_id,
                    event_type="node_failed",
                    node_id=node_id,
                    data={"error": error_msg, "action": "failed_continue"},
                ))

            else:  # FAIL_WORKFLOW (default)
                ns.status = "failed"
                state.status = "failed"
                state.error = error_msg
                self.execution_store.save(state)
                self._emit(ExecutionEvent(
                    execution_id=state.execution_id,
                    event_type="node_failed",
                    node_id=node_id,
                    data={"error": error_msg, "action": "failed_workflow"},
                ))
