"""DAG validation and topological sort for workflow execution."""

from __future__ import annotations

from collections import defaultdict

from decision_system.workflow_engine.models import WorkflowDefinition


class DAGError(Exception):
    """Base error for DAG validation failures."""


class CyclicDAGError(DAGError):
    """Raised when the workflow graph contains a cycle."""


class MissingConnectionError(DAGError):
    """Raised when a connection references a non-existent node."""


class DAGValidator:
    """Validates a workflow DAG for structural correctness."""

    @staticmethod
    def validate(wf: WorkflowDefinition) -> list[DAGError]:
        """Validate the workflow DAG. Returns list of errors (empty = valid)."""
        errors: list[DAGError] = []
        node_ids = {n.id for n in wf.nodes}

        # Check for missing nodes in connections
        for conn in wf.connections:
            if conn.source_node not in node_ids:
                errors.append(MissingConnectionError(
                    f"Connection source node '{conn.source_node}' not found in workflow nodes"
                ))
            if conn.target_node not in node_ids:
                errors.append(MissingConnectionError(
                    f"Connection target node '{conn.target_node}' not found in workflow nodes"
                ))

        # Check for cycles (checks exist regardless of missing-node errors)
        cycle = DAGValidator._find_cycle(wf)
        if cycle:
            errors.append(CyclicDAGError(
                f"Workflow contains a cycle: {' -> '.join(cycle)}"
            ))

        return errors

    @staticmethod
    def _find_cycle(wf: WorkflowDefinition) -> list[str] | None:
        """Detect cycles using DFS. Returns the cycle path if found, else None."""
        graph: dict[str, list[str]] = defaultdict(list)
        for conn in wf.connections:
            graph[conn.source_node].append(conn.target_node)

        all_nodes = {n.id for n in wf.nodes}
        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = {n: WHITE for n in all_nodes}
        parent: dict[str, str | None] = {n: None for n in all_nodes}

        def dfs(node: str) -> list[str] | None:
            color[node] = GRAY
            for neighbor in graph.get(node, []):
                if color.get(neighbor) == GRAY:
                    # Found a cycle — reconstruct it
                    path = [neighbor, node]
                    curr = node
                    while curr != neighbor and parent[curr] is not None:
                        curr = parent[curr]  # type: ignore[assignment]
                        if curr is not None:
                            path.append(curr)
                    path.reverse()
                    return path
                if color.get(neighbor) == WHITE:
                    parent[neighbor] = node
                    result = dfs(neighbor)
                    if result:
                        return result
            color[node] = BLACK
            return None

        for node in all_nodes:
            if color[node] == WHITE:
                result = dfs(node)
                if result:
                    return result
        return None


class TopologicalSort:
    """Produces ordered execution layers from a workflow DAG.

    Each layer is a set of independent nodes that can run in parallel.
    """

    @staticmethod
    def sort(wf: WorkflowDefinition) -> list[list[str]]:
        """Return layers of node IDs in execution order.

        Each inner list contains node IDs that can run concurrently.
        """
        # Build in-degree map and adjacency list
        in_degree: dict[str, int] = {n.id: 0 for n in wf.nodes}
        graph: dict[str, list[str]] = defaultdict(list)

        for conn in wf.connections:
            if conn.source_node in in_degree and conn.target_node in in_degree:
                graph[conn.source_node].append(conn.target_node)
                in_degree[conn.target_node] += 1

        # Kahn's algorithm — track layers
        layers: list[list[str]] = []
        # Current frontier: nodes with no remaining dependencies
        frontier = [n for n, deg in in_degree.items() if deg == 0]

        while frontier:
            layers.append(sorted(frontier))  # deterministic order
            next_frontier: list[str] = []
            for node in frontier:
                for neighbor in graph.get(node, []):
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        next_frontier.append(neighbor)
            frontier = next_frontier

        # If there are leftover nodes not in layers, we have a cycle
        sorted_count = sum(len(layer) for layer in layers)
        if sorted_count < len(in_degree):
            raise CyclicDAGError(
                f"Could not sort all nodes: {len(in_degree) - sorted_count} nodes "
                f"are part of a cycle"
            )

        return layers
