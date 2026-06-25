"""Tests for data source models."""

from decision_system.data_sources.models import (
    DatasetProfile,
    DataSource,
    DataSourceChunk,
    EvidenceSearchResponse,
    EvidenceSearchResult,
)


def test_data_source_defaults():
    ds = DataSource(source_id="s1", workspace_id="ws1", name="test.txt")
    assert ds.source_id == "s1"
    assert ds.workspace_id == "ws1"
    assert ds.name == "test.txt"
    assert ds.source_type == "unknown"
    assert ds.file_type == "unknown"
    assert ds.status == "uploaded"
    assert ds.size_bytes == 0
    assert ds.error_message is None


def test_data_source_chunk_defaults():
    chunk = DataSourceChunk(chunk_id="c1", source_id="s1", workspace_id="ws1")
    assert chunk.chunk_index == 0
    assert chunk.text == ""
    assert chunk.char_start is None


def test_dataset_profile_defaults():
    profile = DatasetProfile(profile_id="p1", source_id="s1", workspace_id="ws1")
    assert profile.row_count == 0
    assert profile.column_count == 0
    assert profile.columns == []
    assert profile.warnings == []


def test_evidence_search_result():
    result = EvidenceSearchResult(
        evidence_id="ev1",
        workspace_id="ws1",
        source_id="s1",
        text="test evidence",
        score=0.95,
    )
    assert result.evidence_id == "ev1"
    assert result.score == 0.95


def test_evidence_search_response():
    results = [
        EvidenceSearchResult(evidence_id="ev1", workspace_id="ws1", source_id="s1", text="test")
    ]
    resp = EvidenceSearchResponse(
        results=results,
        query="test query",
        retrieval_mode="keyword",
        total_results=1,
    )
    assert resp.retrieval_mode == "keyword"
    assert resp.total_results == 1
    assert len(resp.results) == 1
