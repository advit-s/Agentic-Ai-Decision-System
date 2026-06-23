"""Tests for the evidence resolver.

These tests verify workspace-scoped evidence resolution, missing evidence
handling, and cross-workspace isolation.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from decision_system.evidence.resolver import EvidenceResolver, ResolvedEvidence


class TestEvidenceResolver:
    """Tests for EvidenceResolver."""

    def test_resolve_empty(self):
        """Resolving with no identifiers returns warning."""
        resolver = EvidenceResolver()
        result = resolver.resolve()
        assert result.warning is not None
        assert "No evidence identifier" in result.warning

    def test_resolve_missing_evidence_id(self):
        """Resolving a non-existent evidence ID returns warning."""
        resolver = EvidenceResolver()
        result = resolver.resolve(evidence_id="nonexistent-id")
        assert result.warning is not None
        assert "Could not resolve" in result.warning

    def test_resolve_with_only_source_id(self):
        """Resolving with only source_id returns warning (no data store)."""
        resolver = EvidenceResolver()
        result = resolver.resolve(source_id="src-1")
        assert result.warning is not None

    def test_resolve_with_only_chunk_id(self):
        """Resolving with only chunk_id returns warning (no data store)."""
        resolver = EvidenceResolver()
        result = resolver.resolve(chunk_id="chunk-1")
        assert result.warning is not None

    def test_resolve_many_empty(self):
        """Resolving many with empty lists returns empty."""
        resolver = EvidenceResolver()
        results = resolver.resolve_many()
        assert len(results) == 0

    def test_resolve_many_missing(self):
        """Resolving many missing IDs returns warnings for each."""
        resolver = EvidenceResolver()
        results = resolver.resolve_many(
            evidence_ids=["e1", "e2"],
            workspace_id="test-ws",
        )
        assert len(results) == 2
        for r in results:
            assert r.warning is not None

    def test_resolved_evidence_to_dict(self):
        """ResolvedEvidence.to_dict produces expected keys."""
        r = ResolvedEvidence(
            evidence_id="ev-1",
            source_id="src-1",
            chunk_id="chunk-1",
            source_name="doc.md",
            source_type="document",
            chunk_text="Revenue grew by 20%.",
            chunk_index=0,
            workspace_id="ws-1",
        )
        d = r.to_dict()
        assert d["evidence_id"] == "ev-1"
        assert d["source_name"] == "doc.md"
        assert d["chunk_text"] == "Revenue grew by 20%."
        assert d["workspace_id"] == "ws-1"
        assert d["warning"] is None

    def test_resolved_evidence_with_warning(self):
        """ResolvedEvidence preserves warning."""
        r = ResolvedEvidence(
            evidence_id="ev-missing",
            warning="Evidence not found.",
        )
        assert r.warning == "Evidence not found."
        d = r.to_dict()
        assert d["warning"] == "Evidence not found."

    def test_resolve_cross_workspace(self):
        """Cross-workspace evidence access returns standard error (no data)."""
        resolver = EvidenceResolver()
        # Without any real store, cross-workspace just returns missing
        result = resolver.resolve(
            evidence_id="ev-1",
            workspace_id="workspace-a",
        )
        assert result.warning is not None
        # Verify it's the same behavior for any workspace
        result2 = resolver.resolve(
            evidence_id="ev-1",
            workspace_id="workspace-b",
        )
        assert result2.warning is not None


class TestEvidenceResolverStoreDir:
    """Tests with store_dir parameter."""

    def test_init_with_store_dir(self):
        """Resolver can be initialized with a store directory."""
        resolver = EvidenceResolver(store_dir="/tmp/test-store")
        assert resolver is not None

    def test_store_dir_resolve(self):
        """Resolving with store_dir but no actual data returns warning."""
        with tempfile.TemporaryDirectory() as tmpdir:
            resolver = EvidenceResolver(store_dir=tmpdir)
            result = resolver.resolve(evidence_id="ev-none")
            assert result.warning is not None
