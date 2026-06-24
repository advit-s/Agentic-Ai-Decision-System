"""Abstract runtime interface and base class for all connector implementations.

Each connector type implements the ConnectorRuntime ABC to provide:
- test_connection: verify the connector can reach its source
- list_items: enumerate available items from the source
- fetch_item: retrieve content for a specific item
- sync: batch list+fetch loop for import
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from decision_system.connectors.models import (
    ConnectorConfig,
    ConnectorRuntimeItem,
    ConnectorFetchedContent,
)


class ConnectorRuntime(ABC):
    """Abstract base for read-only connector runtimes.

    All methods are read-only — they never create, update, or delete
    resources in the external system.
    """

    @abstractmethod
    def test_connection(self, config: ConnectorConfig) -> dict[str, Any]:
        """Test connectivity to the external source.

        Returns a dict with at least 'success' (bool) and 'message' (str).
        Must not modify any external state.
        """
        ...

    @abstractmethod
    def list_items(
        self, config: ConnectorConfig, path: str = ""
    ) -> list[ConnectorRuntimeItem]:
        """Enumerate available items from the external source.

        For folder-based connectors, 'path' can narrow the listing scope.
        Must not import or copy any data — only enumerate.
        """
        ...

    @abstractmethod
    def fetch_item(
        self, config: ConnectorConfig, item: ConnectorRuntimeItem
    ) -> ConnectorFetchedContent:
        """Retrieve the full content for a single item.

        Returns binary or text content that will be stored locally.
        Must not modify the external resource.
        """
        ...

    @abstractmethod
    def sync(
        self,
        config: ConnectorConfig,
        path: str = "",
        item_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Batch list + fetch items for import.

        Args:
            config: The connector configuration.
            path: Optional path/filter for the listing.
            item_ids: If provided, only sync these specific items.

        Returns:
            Dict with keys: items_found, items_imported, items_skipped,
            items_failed, content_list (list of ConnectorFetchedContent).
        """
        ...


class FakeConnectorRuntime(ConnectorRuntime):
    """Fake runtime for testing. Returns canned data."""

    def __init__(self) -> None:
        self._items: list[ConnectorRuntimeItem] = []
        self._content: dict[str, ConnectorFetchedContent] = {}

    def set_items(self, items: list[ConnectorRuntimeItem]) -> None:
        self._items = items

    def set_content(self, content: list[ConnectorFetchedContent]) -> None:
        for c in content:
            self._content[c.external_id] = c

    def test_connection(self, config: ConnectorConfig) -> dict[str, Any]:
        return {"success": True, "message": "Fake connector OK"}

    def list_items(
        self, config: ConnectorConfig, path: str = ""
    ) -> list[ConnectorRuntimeItem]:
        return self._items

    def fetch_item(
        self, config: ConnectorConfig, item: ConnectorRuntimeItem
    ) -> ConnectorFetchedContent:
        if item.external_id in self._content:
            return self._content[item.external_id]
        return ConnectorFetchedContent(
            external_id=item.external_id,
            title=item.title,
            filename=f"{item.external_id}.txt",
            content_text="Fake content",
            content_type="text/plain",
        )

    def sync(
        self,
        config: ConnectorConfig,
        path: str = "",
        item_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        items = self.list_items(config, path)
        if item_ids is not None:
            items = [i for i in items if i.external_id in item_ids]
        content_list = [self.fetch_item(config, i) for i in items]
        return {
            "items_found": len(items),
            "items_imported": len(content_list),
            "items_skipped": 0,
            "items_failed": 0,
            "content_list": content_list,
        }
