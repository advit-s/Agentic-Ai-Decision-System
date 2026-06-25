"""Read-only GitHub Repository connector.

Lists files from a public GitHub repository and imports selected files
as local data sources. Optional GITHUB_TOKEN env var for rate-limit increases.

No write actions. No commit/push/PR creation.
"""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlparse

import httpx

from decision_system.connectors.models import (
    ConnectorConfig,
    ConnectorFetchedContent,
    ConnectorRuntimeItem,
)
from decision_system.connectors.runtime import ConnectorRuntime

# Timeouts for all GitHub API calls
_TIMEOUT = httpx.Timeout(30.0, connect=10.0)

# Supported file extensions for content import
_SUPPORTED_EXTENSIONS: set[str] = {
    ".md",
    ".txt",
    ".json",
    ".csv",
    ".yml",
    ".yaml",
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".go",
    ".rs",
    ".java",
    ".rb",
    ".sh",
    ".toml",
    ".cfg",
    ".ini",
    ".xml",
    ".html",
    ".css",
    ".scss",
    ".sql",
}

_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

_REPO_URL_PATTERN = "https://api.github.com/repos/{owner}/{repo}/contents/{path}"


def _parse_github_url(url: str) -> dict[str, str] | None:
    """Parse a GitHub URL into owner/repo/path components.

    Supports:
    - https://github.com/owner/repo
    - https://github.com/owner/repo/tree/main/path
    - https://github.com/owner/repo/blob/main/path
    """
    parsed = urlparse(url)
    if parsed.netloc not in ("github.com", "www.github.com"):
        return None

    path_parts = [p for p in parsed.path.strip("/").split("/") if p]
    if len(path_parts) < 2:
        return None

    owner = path_parts[0]
    repo = path_parts[1]
    branch = "main"

    # Check for tree/blob URLs
    if len(path_parts) >= 4 and path_parts[2] in ("tree", "blob"):
        branch = path_parts[3]
        remaining = path_parts[4:]
    elif len(path_parts) >= 3:
        # Could be owner/repo/path without branch specifier
        remaining = path_parts[2:]
    else:
        remaining = []

    path = "/".join(remaining) if remaining else ""
    return {"owner": owner, "repo": repo, "branch": branch, "path": path}


def _github_api_url(owner: str, repo: str, path: str = "") -> str:
    return _REPO_URL_PATTERN.format(owner=owner, repo=repo, path=path)


def _get_headers() -> dict[str, str]:
    headers = {"Accept": "application/vnd.github.v3+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _is_supported_file(filename: str) -> bool:
    ext = os.path.splitext(filename)[1].lower()
    return ext in _SUPPORTED_EXTENSIONS


class GitHubConnectorRuntime(ConnectorRuntime):
    """Read-only GitHub repository connector runtime.

    Lists repository files and fetches content via the GitHub API.
    Requires no token for public repos. Optional GITHUB_TOKEN for
    higher rate limits.
    """

    def test_connection(self, config: ConnectorConfig) -> dict[str, Any]:
        """Test the connection by verifying the repo URL is accessible."""
        repo_url = config.config.get("repository_url", "")
        if not repo_url:
            return {"success": False, "message": "No repository URL configured"}

        parsed = _parse_github_url(repo_url)
        if not parsed:
            return {
                "success": False,
                "message": f"Invalid GitHub URL: {repo_url}",
            }

        api_url = _github_api_url(parsed["owner"], parsed["repo"])
        try:
            resp = httpx.get(api_url, headers=_get_headers(), timeout=_TIMEOUT)
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "success": True,
                    "message": f"Repository '{parsed['owner']}/{parsed['repo']}' is accessible",
                    "repo": f"{parsed['owner']}/{parsed['repo']}",
                    "description": data.get("description", ""),
                    "private": data.get("private", False),
                    "default_branch": data.get("default_branch", "main"),
                }
            elif resp.status_code == 404:
                return {
                    "success": False,
                    "message": f"Repository '{parsed['owner']}/{parsed['repo']}' not found",
                }
            elif resp.status_code == 403:
                return {
                    "success": False,
                    "message": "Rate limited. Set GITHUB_TOKEN env var for higher limits.",
                }
            else:
                return {
                    "success": False,
                    "message": f"GitHub API returned {resp.status_code}",
                }
        except httpx.TimeoutException:
            return {"success": False, "message": "Connection timed out"}
        except httpx.ConnectError:
            return {"success": False, "message": "Could not connect to github.com"}
        except Exception as e:
            return {"success": False, "message": f"Connection failed: {str(e)}"}

    def list_items(self, config: ConnectorConfig, path: str = "") -> list[ConnectorRuntimeItem]:
        """List files in the repository at the specified path."""
        repo_url = config.config.get("repository_url", "")
        parsed = _parse_github_url(repo_url)
        if not parsed:
            return []

        # Use config path or parsed path or the explicit path arg
        search_path = path or parsed["path"]
        api_url = _github_api_url(parsed["owner"], parsed["repo"], search_path)

        try:
            resp = httpx.get(api_url, headers=_get_headers(), timeout=_TIMEOUT)
            if resp.status_code != 200:
                return []

            data = resp.json()
            items: list[ConnectorRuntimeItem] = []

            # Single file response
            if isinstance(data, dict):
                name = data.get("name", "")
                if _is_supported_file(name):
                    items.append(self._item_from_api(data, parsed))
                return items

            # Directory listing
            for entry in data:
                name = entry.get("name", "")
                entry_type = entry.get("type", "file")

                if entry_type == "dir":
                    items.append(
                        ConnectorRuntimeItem(
                            external_id=entry.get("path", name),
                            title=name,
                            item_type="folder",
                            source_url=entry.get("html_url", ""),
                            metadata={"sha": entry.get("sha", "")},
                        )
                    )
                elif entry_type == "file" and _is_supported_file(name):
                    items.append(self._item_from_api(entry, parsed))

            return items

        except (httpx.TimeoutException, httpx.ConnectError, Exception):
            return []

    def _item_from_api(self, entry: dict, parsed: dict) -> ConnectorRuntimeItem:
        return ConnectorRuntimeItem(
            external_id=entry.get("path", entry.get("name", "")),
            title=entry.get("name", ""),
            item_type="file",
            source_url=entry.get("html_url", ""),
            content_type=f"text/{os.path.splitext(entry.get('name', ''))[1].lstrip('.')}"
            if entry.get("name")
            else "text/plain",
            size_bytes=entry.get("size", 0),
            metadata={
                "sha": entry.get("sha", ""),
                "repo": f"{parsed['owner']}/{parsed['repo']}",
                "branch": parsed.get("branch", "main"),
            },
        )

    def fetch_item(
        self, config: ConnectorConfig, item: ConnectorRuntimeItem
    ) -> ConnectorFetchedContent:
        """Fetch the content of a single file from GitHub."""
        repo_url = config.config.get("repository_url", "")
        parsed = _parse_github_url(repo_url)
        if not parsed:
            return ConnectorFetchedContent(
                external_id=item.external_id,
                title=item.title,
                filename=item.external_id,
                content_text="",
                content_type="text/plain",
            )

        # Use the git trees API for raw content
        tree_url = (
            f"https://api.github.com/repos/{parsed['owner']}/{parsed['repo']}"
            f"/contents/{item.external_id}"
        )
        try:
            resp = httpx.get(tree_url, headers=_get_headers(), timeout=_TIMEOUT)
            if resp.status_code != 200:
                return ConnectorFetchedContent(
                    external_id=item.external_id,
                    title=item.title,
                    filename=os.path.basename(item.external_id),
                    content_text="",
                    content_type="text/plain",
                    metadata={"error": f"GitHub API returned {resp.status_code}"},
                )

            data = resp.json()
            import base64

            content_b64 = data.get("content", "")
            encoding = data.get("encoding", "")

            if encoding == "base64":
                try:
                    content_bytes = base64.b64decode(content_b64)
                    # Check file size limit
                    if len(content_bytes) > _MAX_FILE_SIZE:
                        return ConnectorFetchedContent(
                            external_id=item.external_id,
                            title=item.title,
                            filename=os.path.basename(item.external_id),
                            content_text="",
                            content_type=item.content_type or "text/plain",
                            metadata={
                                "error": f"File exceeds {_MAX_FILE_SIZE // 1024 // 1024}MB limit"
                            },
                        )
                    content_text = content_bytes.decode("utf-8", errors="replace")
                except Exception:
                    content_text = ""
            else:
                content_text = ""

            return ConnectorFetchedContent(
                external_id=item.external_id,
                title=item.title,
                filename=os.path.basename(item.external_id),
                content_text=content_text,
                content_type=item.content_type or "text/plain",
                metadata={
                    "sha": data.get("sha", ""),
                    "size": data.get("size", 0),
                    "repo": f"{parsed['owner']}/{parsed['repo']}",
                    "source_url": item.source_url or data.get("html_url", ""),
                },
            )

        except (httpx.TimeoutException, httpx.ConnectError, Exception) as e:
            return ConnectorFetchedContent(
                external_id=item.external_id,
                title=item.title,
                filename=os.path.basename(item.external_id),
                content_text="",
                content_type="text/plain",
                metadata={"error": str(e)},
            )

    def sync(
        self,
        config: ConnectorConfig,
        path: str = "",
        item_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """List all items, optionally filter by item_ids, fetch content."""
        items = self.list_items(config, path)

        # Filter to only files (not folders) for content fetching
        files = [i for i in items if i.item_type == "file"]
        if item_ids is not None:
            files = [i for i in files if i.external_id in item_ids]

        content_list: list[ConnectorFetchedContent] = []
        errors = 0
        for item in files:
            try:
                content = self.fetch_item(config, item)
                content_list.append(content)
            except Exception:
                errors += 1

        return {
            "items_found": len(items),
            "items_imported": len(content_list),
            "items_skipped": len(items) - len(files),
            "items_failed": errors,
            "content_list": content_list,
        }


# Factory
def get_github_connector() -> GitHubConnectorRuntime:
    return GitHubConnectorRuntime()
