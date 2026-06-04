"""Inspection helpers for local knowledge graph summaries."""

from collections import Counter

from pydantic import BaseModel, Field

from decision_system.graphing.models import KnowledgeGraph


class ConnectedEntity(BaseModel):
    """Entity degree summary used by graph inspection output."""

    entity_id: str
    name: str
    connection_count: int


class GraphInspection(BaseModel):
    """Structured counts for a local knowledge graph."""

    entity_count: int
    relationship_count: int
    entities_by_type: dict[str, int] = Field(default_factory=dict)
    relationships_by_relation_type: dict[str, int] = Field(default_factory=dict)
    top_connected_entities: list[ConnectedEntity] = Field(default_factory=list)


def inspect_knowledge_graph(graph: KnowledgeGraph, top_n: int = 5) -> GraphInspection:
    """Compute grouped counts and top connected entities."""

    entity_names = {entity.entity_id: entity.name for entity in graph.entities}
    entity_degrees: Counter[str] = Counter()
    for relationship in graph.relationships:
        entity_degrees[relationship.source_entity_id] += 1
        entity_degrees[relationship.target_entity_id] += 1

    top_connected = [
        ConnectedEntity(
            entity_id=entity_id,
            name=entity_names.get(entity_id, entity_id),
            connection_count=count,
        )
        for entity_id, count in sorted(
            entity_degrees.items(),
            key=lambda item: (-item[1], entity_names.get(item[0], item[0])),
        )[:top_n]
    ]

    return GraphInspection(
        entity_count=len(graph.entities),
        relationship_count=len(graph.relationships),
        entities_by_type=dict(Counter(entity.entity_type for entity in graph.entities)),
        relationships_by_relation_type=dict(
            Counter(relationship.relation_type for relationship in graph.relationships)
        ),
        top_connected_entities=top_connected,
    )


def render_graph_inspection(inspection: GraphInspection) -> str:
    """Render graph inspection counts as concise CLI text."""

    lines = [
        f"Total entity count: {inspection.entity_count}",
        f"Total relationship count: {inspection.relationship_count}",
        "Entities grouped by type:",
    ]
    lines.extend(_render_count_lines(inspection.entities_by_type))
    lines.append("Relationships grouped by relation type:")
    lines.extend(_render_count_lines(inspection.relationships_by_relation_type))
    lines.append("Top connected entities:")
    if inspection.top_connected_entities:
        lines.extend(
            f"- {entity.name}: {entity.connection_count}"
            for entity in inspection.top_connected_entities
        )
    else:
        lines.append("- (none)")
    return "\n".join(lines)


def _render_count_lines(counts: dict[str, int]) -> list[str]:
    if not counts:
        return ["- (none)"]
    return [f"- {name}: {count}" for name, count in sorted(counts.items())]
