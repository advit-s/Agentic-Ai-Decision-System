"""Tests for document parsing and CSV/JSON profiling."""

from decision_system.data_sources.parser import (
    parse_document,
    profile_csv,
    profile_json_content,
    get_supported_extensions,
    is_parsable,
)


def test_get_supported_extensions():
    exts = get_supported_extensions()
    assert ".txt" in exts
    assert ".md" in exts
    assert ".json" in exts


def test_is_parsable():
    assert is_parsable(".txt") is True
    assert is_parsable(".md") is True
    assert is_parsable(".json") is True
    assert is_parsable(".pdf") is False
    assert is_parsable(".csv") is False  # CSV is profiled, not parsed as text


def test_parse_text():
    content = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph with more content."
    chunks, warnings = parse_document(content, ".txt", "src1", "ws1")
    assert len(chunks) >= 1
    assert len(warnings) == 0
    assert all(c.source_id == "src1" for c in chunks)
    assert all(c.workspace_id == "ws1" for c in chunks)


def test_parse_markdown():
    content = "# Title\n\nSome content here.\n\n## Section 2\n\nMore details."
    chunks, warnings = parse_document(content, ".md", "src1", "ws1")
    assert len(chunks) >= 1
    assert any("Title" in c.text for c in chunks)


def test_parse_json_object():
    content = '{"name": "Alice", "role": "engineer", "department": "IT"}'
    chunks, warnings = parse_document(content, ".json", "src1", "ws1")
    assert len(chunks) >= 1
    assert any("Alice" in c.text for c in chunks)


def test_parse_json_array():
    content = '[{"id": 1, "value": "a"}, {"id": 2, "value": "b"}]'
    chunks, warnings = parse_document(content, ".json", "src1", "ws1")
    assert len(chunks) >= 2


def test_parse_empty():
    chunks, warnings = parse_document("", ".txt", "src1", "ws1")
    assert len(chunks) == 0
    assert any("empty" in w.lower() for w in warnings)


def test_parse_unsupported():
    chunks, warnings = parse_document("content", ".pdf", "src1", "ws1")
    assert len(chunks) == 0
    assert any("unsupported" in w.lower() for w in warnings)


def test_profile_csv_basic():
    csv_content = "name,age,role\nAlice,30,engineer\nBob,25,designer\nCharlie,35,manager"
    profile = profile_csv(csv_content, "src1", "ws1")
    assert profile["row_count"] == 3
    assert profile["column_count"] == 3
    assert profile["source_id"] == "src1"


def test_profile_csv_numeric():
    csv_content = "product,revenue,cost\nA,100,50\nB,200,80\nC,150,60"
    profile = profile_csv(csv_content, "src1", "ws1")
    assert profile["row_count"] == 3
    assert profile["column_count"] == 3
    assert "revenue" in profile["numeric_summary"]
    assert profile["numeric_summary"]["revenue"]["mean"] == 150.0


def test_profile_csv_missing_values():
    csv_content = "name,email\nAlice,alice@test.com\nBob,\nCharlie,charlie@test.com\nDiana,"
    profile = profile_csv(csv_content, "src1", "ws1")
    assert profile["row_count"] == 4
    assert profile["missing_values"]["email"] == 2  # Two missing emails


def test_profile_json_list():
    json_content = '[{"name": "A", "score": 10}, {"name": "B", "score": 20}]'
    profile = profile_json_content(json_content, "src1", "ws1")
    assert profile["top_level_type"] == "list"
    assert profile["record_count"] == 2
    assert "name" in profile.get("field_paths", [])


def test_profile_json_object():
    json_content = '{"company": "Acme", "revenue": 1000000, "employees": 50}'
    profile = profile_json_content(json_content, "src1", "ws1")
    assert profile["top_level_type"] == "dict"
    assert "company" in profile.get("field_paths", [])
