import json

from decision_system.graphing.extractor import extract_knowledge_graph
from decision_system.graphing.models import Entity, Relationship
from decision_system.graphing.store import load_knowledge_graph, save_knowledge_graph
from decision_system.models import EvidenceChunk


def _chunk(text: str, filename: str = "systems.md") -> EvidenceChunk:
    return EvidenceChunk(
        evidence_id="doc-test:chunk-0001",
        document_id="doc-test",
        source_path=f"company_docs/{filename}",
        source_filename=filename,
        chunk_id="chunk-0001",
        text=text,
    )


def _entity_names_by_id(graph):
    return {entity.entity_id: entity.name for entity in graph.entities}


def test_entity_model_serialization():
    entity = Entity(
        entity_id="entity-billing",
        name="Billing",
        entity_type="system",
        source_evidence_ids=["doc-test:chunk-0001"],
        source_filenames=["billing.md"],
        confidence="medium",
    )

    payload = entity.model_dump(mode="json")

    assert payload == {
        "entity_id": "entity-billing",
        "name": "Billing",
        "entity_type": "system",
        "source_evidence_ids": ["doc-test:chunk-0001"],
        "source_filenames": ["billing.md"],
        "confidence": "medium",
    }


def test_relationship_model_serialization():
    relationship = Relationship(
        relationship_id="relationship-1",
        source_entity_id="entity-billing",
        relation_type="depends_on",
        target_entity_id="entity-legacyauth",
        source_evidence_ids=["doc-test:chunk-0001"],
        source_filenames=["billing.md"],
        confidence="medium",
    )

    payload = relationship.model_dump(mode="json")

    assert payload == {
        "relationship_id": "relationship-1",
        "source_entity_id": "entity-billing",
        "relation_type": "depends_on",
        "target_entity_id": "entity-legacyauth",
        "source_evidence_ids": ["doc-test:chunk-0001"],
        "source_filenames": ["billing.md"],
        "confidence": "medium",
    }


def test_deterministic_extraction_from_depends_on_sentence():
    graph = extract_knowledge_graph([_chunk("Billing depends on LegacyAuth.")])
    names_by_id = _entity_names_by_id(graph)
    relationship = graph.relationships[0]

    assert {entity.name for entity in graph.entities} == {"Billing", "LegacyAuth"}
    assert relationship.relation_type == "depends_on"
    assert names_by_id[relationship.source_entity_id] == "Billing"
    assert names_by_id[relationship.target_entity_id] == "LegacyAuth"
    assert relationship.source_evidence_ids == ["doc-test:chunk-0001"]
    assert relationship.source_filenames == ["systems.md"]


def test_deterministic_extraction_from_owned_by_sentence():
    graph = extract_knowledge_graph([_chunk("LegacyAuth owned by Platform Team.")])
    names_by_id = _entity_names_by_id(graph)
    relationship = graph.relationships[0]

    assert {entity.name for entity in graph.entities} == {"LegacyAuth", "Platform Team"}
    assert relationship.relation_type == "owned_by"
    assert names_by_id[relationship.source_entity_id] == "LegacyAuth"
    assert names_by_id[relationship.target_entity_id] == "Platform Team"


def test_contradiction_relationship_from_marker():
    graph = extract_knowledge_graph(
        [
            _chunk(
                "Billing migration requires rollback planning. "
                "CONTRADICTS: Billing migration can proceed without rollback planning."
            )
        ]
    )

    assert any(relationship.relation_type == "contradicts" for relationship in graph.relationships)
    relationship = next(
        relationship
        for relationship in graph.relationships
        if relationship.relation_type == "contradicts"
    )
    assert relationship.source_evidence_ids == ["doc-test:chunk-0001"]
    assert relationship.source_filenames == ["systems.md"]


def test_graph_store_writes_and_loads_json(tmp_path):
    graph = extract_knowledge_graph([_chunk("Billing depends on LegacyAuth.")])
    graph_path = tmp_path / "graph" / "knowledge_graph.json"

    saved_path = save_knowledge_graph(graph, graph_path)
    loaded_graph = load_knowledge_graph(graph_path)

    assert saved_path == graph_path
    assert json.loads(graph_path.read_text(encoding="utf-8"))["entities"]
    assert loaded_graph == graph
