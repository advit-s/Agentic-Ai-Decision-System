"""Inspection helpers for the v0.4 ontology map."""

from __future__ import annotations

from decision_system.ontology.models import OntologyMap


def inspect_ontology(omap: OntologyMap) -> dict[str, object]:
    """Compute summary statistics from an ontology map."""

    concept_count = len(omap.concepts)
    mapping_count = len(omap.column_mappings)

    concept_type_counts: dict[str, int] = {}
    for concept in omap.concepts:
        ct = concept.concept_type
        concept_type_counts[ct] = concept_type_counts.get(ct, 0) + 1

    # Build dataset column coverage
    dataset_columns: dict[str, list[str]] = {}
    for mapping in omap.column_mappings:
        ds = mapping.dataset_id
        dataset_columns.setdefault(ds, []).append(mapping.column_name)

    # Find unmapped columns per dataset by comparing with all known column names
    # (We don't have a full column list here, so we just note what is mapped.)

    return {
        "concept_count": concept_count,
        "mapping_count": mapping_count,
        "concept_type_counts": concept_type_counts,
        "dataset_columns": dataset_columns,
        "concept_ids": sorted(c.concept_id for c in omap.concepts),
        "mapped_columns": [
            {
                "dataset_id": m.dataset_id,
                "column_name": m.column_name,
                "concept_id": m.mapped_concept_id,
                "concept_name": m.mapped_concept_name,
            }
            for m in omap.column_mappings
        ],
    }


def render_ontology_inspection(summary: dict[str, object]) -> str:
    """Render the ontology inspection as a human-readable string."""

    lines: list[str] = ["# Ontology Inspection", ""]

    lines.append(f"Concepts: {summary['concept_count']}")
    lines.append(f"Mapped columns: {summary['mapping_count']}")
    lines.append("")

    concept_type_counts: dict[str, int] = summary.get("concept_type_counts", {})
    if concept_type_counts:
        lines.append("## Concept Types")
        lines.append("")
        for ctype, count in sorted(concept_type_counts.items()):
            lines.append(f"- **{ctype}**: {count}")
        lines.append("")

    dataset_columns: dict[str, list[str]] = summary.get("dataset_columns", {})
    if dataset_columns:
        lines.append("## Mapped Columns by Dataset")
        lines.append("")
        for ds_id in sorted(dataset_columns.keys()):
            cols = dataset_columns[ds_id]
            lines.append(f"- **{ds_id}**: {', '.join(cols[:20])}")
            if len(cols) > 20:
                lines.append(f"  - ... and {len(cols) - 20} more")
        lines.append("")

    mapped_columns: list[dict] = summary.get("mapped_columns", [])
    if mapped_columns:
        lines.append("## Column Mappings (first 30)")
        lines.append("")
        for m in mapped_columns[:30]:
            lines.append(
                f"- `{m['dataset_id']}`.`{m['column_name']}` "
                f"-> **{m['concept_id']}** ({m['concept_name']})"
            )
        if len(mapped_columns) > 30:
            lines.append(f"- ... and {len(mapped_columns) - 30} more")
        lines.append("")

    if summary["concept_count"] == 0 and summary["mapping_count"] == 0:
        return "# Ontology Inspection\n\nNo ontology map found. Run `decision-system map-ontology` first."

    return "\n".join(lines)
