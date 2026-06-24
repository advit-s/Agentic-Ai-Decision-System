"""Read-only GitHub Issues, Pull Requests, and Releases connector.

Extends the GitHub repository connector to support issues, PRs, and
release notes. All operations are read-only via the GitHub REST API.

v1.30 -- Connector Expansion
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from decision_system.connectors.models import (
    ConnectorConfig,
    ConnectorRuntimeItem,
    ConnectorFetchedContent,
)
from decision_system.connectors.github_connector import (
    _parse_github_url,
    _get_headers,
    _TIMEOUT,
)


# ---------------------------------------------------------------------------
# GitHub Issues (read-only)
# ---------------------------------------------------------------------------


def _issues_api_url(owner: str, repo: str, state: str = "open") -> str:
    return (
        f"https://api.github.com/repos/{owner}/{repo}/issues"
        f"?state={state}&per_page=100&sort=updated&direction=desc"
    )


def _issue_api_url(owner: str, repo: str, issue_number: int) -> str:
    return f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}"


def _pulls_api_url(owner: str, repo: str, state: str = "open") -> str:
    return (
        f"https://api.github.com/repos/{owner}/{repo}/pulls"
        f"?state={state}&per_page=100&sort=updated&direction=desc"
    )


def _releases_api_url(owner: str, repo: str) -> str:
    return (
        f"https://api.github.com/repos/{owner}/{repo}/releases"
        f"?per_page=50"
    )


def _parse_github_repo(repo_url: str) -> dict[str, str] | None:
    parsed = _parse_github_url(repo_url)
    if parsed is None:
        return None
    return {"owner": parsed["owner"], "repo": parsed["repo"]}


def list_issues(
    config: ConnectorConfig, state: str = "open"
) -> list[ConnectorRuntimeItem]:
    """List issues from a GitHub repository (read-only).

    Args:
        config: Connector config with repository_url.
        state: Issue state filter ('open', 'closed', 'all').

    Returns:
        List of ConnectorRuntimeItem for each issue.
    """
    repo_url = config.config.get("repository_url", "")
    repo = _parse_github_repo(repo_url)
    if repo is None:
        return []

    url = _issues_api_url(repo["owner"], repo["repo"], state)
    try:
        resp = httpx.get(url, headers=_get_headers(), timeout=_TIMEOUT)
        if resp.status_code != 200:
            return []

        issues_data = resp.json()
        items: list[ConnectorRuntimeItem] = []

        for issue in issues_data:
            if "pull_request" in issue:
                continue
            items.append(_issue_to_item(issue, repo))

        return items
    except (httpx.TimeoutException, httpx.ConnectError, Exception):
        return []


def _issue_to_item(issue: dict, repo: dict) -> ConnectorRuntimeItem:
    modified = None
    if issue.get("updated_at"):
        try:
            modified = datetime.fromisoformat(
                issue["updated_at"].replace("Z", "+00:00")
            )
        except (ValueError, AttributeError):
            pass

    labels = [l.get("name", "") for l in issue.get("labels", [])]

    return ConnectorRuntimeItem(
        external_id=f"issue-{issue['number']}",
        title=issue.get("title", f"Issue #{issue['number']}"),
        item_type="issue",
        source_url=issue.get("html_url", ""),
        modified_at=modified,
        content_type="text/markdown",
        size_bytes=len(issue.get("body", "") or ""),
        metadata={
            "github_type": "issue",
            "issue_number": issue["number"],
            "state": issue.get("state", "open"),
            "labels": labels,
            "author": issue.get("user", {}).get("login", ""),
            "created_at": issue.get("created_at", ""),
            "updated_at": issue.get("updated_at", ""),
            "comments": issue.get("comments", 0),
            "repo": f"{repo['owner']}/{repo['repo']}",
        },
    )


def fetch_issue(
    config: ConnectorConfig, item: ConnectorRuntimeItem
) -> ConnectorFetchedContent:
    """Fetch the full content of a GitHub issue."""
    repo_url = config.config.get("repository_url", "")
    repo = _parse_github_repo(repo_url)
    if repo is None:
        return ConnectorFetchedContent(
            external_id=item.external_id,
            title=item.title,
            filename=f"{item.external_id}.md",
            content_text="",
            content_type="text/markdown",
        )

    issue_number = item.metadata.get("issue_number", 0)
    url = _issue_api_url(repo["owner"], repo["repo"], issue_number)

    try:
        resp = httpx.get(url, headers=_get_headers(), timeout=_TIMEOUT)
        if resp.status_code != 200:
            return ConnectorFetchedContent(
                external_id=item.external_id,
                title=item.title,
                filename=f"{item.external_id}.md",
                content_text="",
                content_type="text/markdown",
                metadata={"error": f"GitHub API returned {resp.status_code}"},
            )

        issue_data = resp.json()
        body = issue_data.get("body", "") or ""
        content = _format_issue_content(issue_data, body)

        return ConnectorFetchedContent(
            external_id=item.external_id,
            title=item.title,
            filename=f"{item.external_id}.md",
            content_text=content,
            content_type="text/markdown",
            metadata={
                "github_type": "issue",
                "issue_number": issue_number,
                "state": issue_data.get("state", ""),
                "labels": [
                    l.get("name", "") for l in issue_data.get("labels", [])
                ],
                "author": issue_data.get("user", {}).get("login", ""),
                "created_at": issue_data.get("created_at", ""),
                "updated_at": issue_data.get("updated_at", ""),
                "comments": issue_data.get("comments", 0),
                "html_url": issue_data.get("html_url", ""),
            },
        )
    except (httpx.TimeoutException, httpx.ConnectError, Exception) as e:
        return ConnectorFetchedContent(
            external_id=item.external_id,
            title=item.title,
            filename=f"{item.external_id}.md",
            content_text="",
            content_type="text/markdown",
            metadata={"error": str(e)},
        )


def _format_issue_content(issue_data: dict, body: str) -> str:
    lines = [
        f"# {issue_data.get('title', '')}",
        "",
        f"**Issue #{issue_data['number']}** | "
        f"State: {issue_data.get('state', 'unknown')} | "
        f"Author: {issue_data.get('user', {}).get('login', 'unknown')} | "
        f"Created: {issue_data.get('created_at', '')}",
        "",
        "---",
        "",
    ]

    if body:
        lines.append(body)
        lines.append("")

    lines.append("---")
    lines.append(f"*Imported from GitHub issue #{issue_data['number']}*")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# GitHub Pull Requests (read-only)
# ---------------------------------------------------------------------------


def list_pull_requests(
    config: ConnectorConfig, state: str = "open"
) -> list[ConnectorRuntimeItem]:
    """List pull requests from a GitHub repository (read-only)."""
    repo_url = config.config.get("repository_url", "")
    repo = _parse_github_repo(repo_url)
    if repo is None:
        return []

    url = _pulls_api_url(repo["owner"], repo["repo"], state)
    try:
        resp = httpx.get(url, headers=_get_headers(), timeout=_TIMEOUT)
        if resp.status_code != 200:
            return []

        prs_data = resp.json()
        items: list[ConnectorRuntimeItem] = []

        for pr in prs_data:
            items.append(_pr_to_item(pr, repo))

        return items
    except (httpx.TimeoutException, httpx.ConnectError, Exception):
        return []


def _pr_to_item(pr: dict, repo: dict) -> ConnectorRuntimeItem:
    modified = None
    if pr.get("updated_at"):
        try:
            modified = datetime.fromisoformat(
                pr["updated_at"].replace("Z", "+00:00")
            )
        except (ValueError, AttributeError):
            pass

    return ConnectorRuntimeItem(
        external_id=f"pr-{pr['number']}",
        title=pr.get("title", f"PR #{pr['number']}"),
        item_type="pull_request",
        source_url=pr.get("html_url", ""),
        modified_at=modified,
        content_type="text/markdown",
        size_bytes=len(pr.get("body", "") or ""),
        metadata={
            "github_type": "pull_request",
            "pr_number": pr["number"],
            "state": pr.get("state", "open"),
            "author": pr.get("user", {}).get("login", ""),
            "created_at": pr.get("created_at", ""),
            "updated_at": pr.get("updated_at", ""),
            "merged": pr.get("merged", False),
            "draft": pr.get("draft", False),
            "repo": f"{repo['owner']}/{repo['repo']}",
        },
    )


# ---------------------------------------------------------------------------
# GitHub Releases (read-only)
# ---------------------------------------------------------------------------


def list_releases(
    config: ConnectorConfig,
) -> list[ConnectorRuntimeItem]:
    """List releases from a GitHub repository (read-only)."""
    repo_url = config.config.get("repository_url", "")
    repo = _parse_github_repo(repo_url)
    if repo is None:
        return []

    url = _releases_api_url(repo["owner"], repo["repo"])
    try:
        resp = httpx.get(url, headers=_get_headers(), timeout=_TIMEOUT)
        if resp.status_code != 200:
            return []

        releases_data = resp.json()
        items: list[ConnectorRuntimeItem] = []

        for release in releases_data:
            items.append(_release_to_item(release, repo))

        return items
    except (httpx.TimeoutException, httpx.ConnectError, Exception):
        return []


def _release_to_item(release: dict, repo: dict) -> ConnectorRuntimeItem:
    published = None
    if release.get("published_at"):
        try:
            published = datetime.fromisoformat(
                release["published_at"].replace("Z", "+00:00")
            )
        except (ValueError, AttributeError):
            pass

    return ConnectorRuntimeItem(
        external_id=f"release-{release.get('tag_name', release['id'])}",
        title=release.get(
            "name", release.get("tag_name", "Release")
        ),
        item_type="release",
        source_url=release.get("html_url", ""),
        modified_at=published,
        content_type="text/markdown",
        size_bytes=len(release.get("body", "") or ""),
        metadata={
            "github_type": "release",
            "tag_name": release.get("tag_name", ""),
            "author": release.get("author", {}).get("login", ""),
            "published_at": release.get("published_at", ""),
            "prerelease": release.get("prerelease", False),
            "repo": f"{repo['owner']}/{repo['repo']}",
        },
    )


def fetch_release(
    config: ConnectorConfig, item: ConnectorRuntimeItem
) -> ConnectorFetchedContent:
    """Fetch the content of a GitHub release."""
    body = item.metadata.get("body", "")
    tag_name = item.metadata.get("tag_name", "")
    html_url = item.source_url or ""

    content = f"""# {item.title}

**Release:** {tag_name}
**URL:** {html_url}
**Published:** {item.metadata.get('published_at', '')}

---

{body}

---

*Imported from GitHub release {tag_name}*
"""

    return ConnectorFetchedContent(
        external_id=item.external_id,
        title=item.title,
        filename=f"{item.external_id}.md",
        content_text=content,
        content_type="text/markdown",
        metadata=dict(item.metadata),
    )


# ---------------------------------------------------------------------------
# Combined listing helper
# ---------------------------------------------------------------------------


def list_all_github_items(
    config: ConnectorConfig,
    include_issues: bool = True,
    include_prs: bool = True,
    include_releases: bool = True,
) -> list[ConnectorRuntimeItem]:
    """List all available GitHub items (issues, PRs, releases).

    Combines items from across GitHub item types.
    """
    items: list[ConnectorRuntimeItem] = []

    if include_issues:
        try:
            items.extend(list_issues(config, state="all"))
        except Exception:
            pass

    if include_prs:
        try:
            items.extend(list_pull_requests(config, state="all"))
        except Exception:
            pass

    if include_releases:
        try:
            items.extend(list_releases(config))
        except Exception:
            pass

    return items
