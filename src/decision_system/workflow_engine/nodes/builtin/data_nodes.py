"""Built-in data analysis node types.

Each node wraps an existing data/analysis capability.
"""

from __future__ import annotations

from pathlib import Path

from decision_system.workflow_engine.models import (
    ExecutionContext,
    WorkflowNode,
)


class ExtractGraphNode(WorkflowNode):
    """Extracts entities and relationships from documents into a knowledge graph."""

    type: str = "decision_system.extract_graph"
    label: str = "Extract Graph"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        from decision_system.graphing.extractor import extract_knowledge_graph

        chunks = inputs.get("chunks") or []
        graph = extract_knowledge_graph(chunks)

        kg_dict = graph.model_dump() if hasattr(graph, "model_dump") else {}
        return {
            "graph": kg_dict,
            "entity_count": len(kg_dict.get("entities", [])),
            "relationship_count": len(kg_dict.get("relationships", [])),
        }

    @classmethod
    def get_config_schema(cls) -> dict:
        return {"type": "object", "properties": {}}

    @classmethod
    def get_input_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {"chunks": {"type": "array"}},
        }

    @classmethod
    def get_output_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "graph": {"type": "object"},
                "entity_count": {"type": "integer"},
                "relationship_count": {"type": "integer"},
            },
        }


class ProfileDataNode(WorkflowNode):
    """Profiles local CSV data files."""

    type: str = "decision_system.profile_data"
    label: str = "Profile Data"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        from decision_system.data_catalog.loader import load_csv
        from decision_system.data_catalog.models import DataCategory
        from decision_system.data_catalog.profiler import profile_dataset

        catalog_path_str = self.config.get("catalog_path", "company_data")
        catalog_path = Path(catalog_path_str)

        profiles = []
        if catalog_path.exists():
            # Load each CSV from category subdirectories
            for cat_dir in catalog_path.iterdir():
                if not cat_dir.is_dir():
                    continue
                try:
                    category = DataCategory(cat_dir.name)
                except ValueError:
                    continue
                for csv_file in sorted(cat_dir.glob("*.csv")):
                    try:
                        ds = load_csv(csv_file, category)
                        profiles.append(profile_dataset(ds))
                    except Exception:
                        continue

        return {
            "profiles": [p.model_dump() if hasattr(p, "model_dump") else p for p in profiles],
            "count": len(profiles),
        }

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "catalog_path": {
                    "type": "string",
                    "default": "company_data",
                    "title": "Catalog Path",
                },
            },
        }

    @classmethod
    def get_input_schema(cls) -> dict:
        return {"type": "object", "properties": {}}

    @classmethod
    def get_output_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "profiles": {"type": "array"},
                "count": {"type": "integer"},
            },
        }


class MapOntologyNode(WorkflowNode):
    """Maps data profiles to ontology concepts."""

    type: str = "decision_system.map_ontology"
    label: str = "Map Ontology"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        from decision_system.ontology.mapper import map_profiles_to_ontology

        profiles = inputs.get("profiles") or []
        ontology = map_profiles_to_ontology(profiles)
        onto_dict = ontology.model_dump() if hasattr(ontology, "model_dump") else {}
        return {
            "ontology": onto_dict,
            "concept_count": len(onto_dict.get("mappings", [])),
        }

    @classmethod
    def get_config_schema(cls) -> dict:
        return {"type": "object", "properties": {}}

    @classmethod
    def get_input_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {"profiles": {"type": "array"}},
        }

    @classmethod
    def get_output_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "ontology": {"type": "object"},
                "concept_count": {"type": "integer"},
            },
        }


class DetectPatternsNode(WorkflowNode):
    """Runs deterministic pattern and vulnerability detection."""

    type: str = "decision_system.detect_patterns"
    label: str = "Detect Patterns"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        from decision_system.insights.detectors import run_detectors
        from decision_system.insights.store import InsightStore

        store = InsightStore()
        profiles = inputs.get("profiles") or []
        inputs.get("graph")

        csv_root = Path(self.config.get("catalog_path", "company_data"))
        run_detectors(store, profiles, csv_root)

        insights = store.get_all_insights()
        return {
            "insights": [i.model_dump() if hasattr(i, "model_dump") else i for i in insights],
            "count": len(insights),
        }

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "severity_threshold": {
                    "type": "string",
                    "default": "low",
                    "enum": ["low", "medium", "high", "critical"],
                },
                "catalog_path": {
                    "type": "string",
                    "default": "company_data",
                },
            },
        }

    @classmethod
    def get_input_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "profiles": {"type": "array"},
                "graph": {"type": "object"},
            },
        }

    @classmethod
    def get_output_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "insights": {"type": "array"},
                "count": {"type": "integer"},
            },
        }


class WarRoomNode(WorkflowNode):
    """Runs the war-cabinet multi-role analysis protocol."""

    type: str = "decision_system.war_room"
    label: str = "Run War Room"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        from decision_system.war_room.runner import run_war_room

        question = inputs.get("question") or inputs.get("text") or ""
        if not question:
            question = self.config.get("question", "")

        result = run_war_room(question=question)
        result_dict = result.model_dump() if hasattr(result, "model_dump") else {}
        return {
            "war_room_run": result_dict,
            "artifact_count": len(result_dict.get("artifacts", [])),
            "judge_interventions": len(result_dict.get("judge_findings", [])),
        }

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "title": "Question",
                    "description": "Business question for the war room",
                },
            },
        }

    @classmethod
    def get_input_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "text": {"type": "string"},
            },
        }

    @classmethod
    def get_output_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "war_room_run": {"type": "object"},
                "artifact_count": {"type": "integer"},
                "judge_interventions": {"type": "integer"},
            },
        }
