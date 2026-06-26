"""Generic URL / Web Page Import connector (read-only).

Fetches a URL, extracts title and text from HTML, stores original URL
metadata. Blocks private/internal network addresses by default to prevent
SSRF attacks.
"""

from __future__ import annotations

import ipaddress
import re
import socket
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx

from decision_system.connectors.models import (
    ConnectorConfig,
    ConnectorFetchedContent,
    ConnectorRuntimeItem,
)
from decision_system.connectors.runtime import ConnectorRuntime

_TIMEOUT = httpx.Timeout(30.0, connect=10.0, read=30.0)
_MAX_RESPONSE_SIZE = 10 * 1024 * 1024  # 10 MB

# Private/reserved network prefixes to block by default
_PRIVATE_PREFIXES: list[tuple[str, int | None]] = [
    ("127.0.0.0/8", None),
    ("10.0.0.0/8", None),
    ("172.16.0.0/12", None),
    ("192.168.0.0/16", None),
    ("169.254.0.0/16", None),
    ("::1/128", None),
    ("fc00::/7", None),
    ("localhost", None),
]

# Known text/* content types we accept
_ACCEPTABLE_CONTENT_TYPES = [
    "text/html",
    "text/plain",
    "text/markdown",
    "application/json",
    "application/xml",
    "text/xml",
    "application/javascript",
    "text/javascript",
    "text/css",
    "text/csv",
]


def _is_private_ip(ip_str: str) -> bool:
    """Check if a dotted-quad IP string is a private/reserved address using ipaddress module."""
    if not ip_str:
        return False
    try:
        addr = ipaddress.ip_address(ip_str)
        return addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_unspecified
    except ValueError:
        return False


def _resolve_and_check(hostname: str) -> bool:
    """Resolve a hostname via DNS and check if any resolved address is private.

    Returns True if the hostname resolves to a private/reserved IP.
    Returns False if the hostname resolves to a public IP only.
    On DNS failure, returns True (fail closed) to block potentially unsafe hosts.
    """
    try:
        for addr_info in socket.getaddrinfo(hostname, 80, family=socket.AF_INET):
            ip = addr_info[4][0]
            if _is_private_ip(ip):
                return True
        # All resolved addresses are public
        return False
    except (socket.gaierror, OSError):
        # DNS resolution failure - fail closed to avoid SSRF on transient DNS issues
        return True


def _is_private_host(hostname: str) -> bool:
    """Check if a hostname resolves to a private/internal address.

    First checks known private hostnames and IP patterns (fast path),
    then performs DNS resolution to catch hostnames that resolve
    to internal IPs (e.g., "internal.company.com" -> 10.x.x.x).
    """
    if not hostname:
        return True

    hostname_lower = hostname.lower()

    # Check localhost-like hostnames
    if hostname_lower in ("localhost", "localhost.localdomain", "127.0.0.1", "::1"):
        return True

    # Fast-path check for dotted-quad private IP patterns
    if _is_private_ip(hostname_lower):
        return True

    # DNS resolution check for hostnames that resolve to private IPs
    # (catches cases like "internal.company.com" -> 10.0.0.1)
    if _resolve_and_check(hostname_lower):
        return True

    return False


def _extract_html_title(html: str) -> str:
    """Extract the <title> from an HTML document."""
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if match:
        title = match.group(1).strip()
        return " ".join(title.split())  # Collapse whitespace
    return ""


def _extract_html_text(html: str) -> str:
    """Extract readable text from HTML by stripping tags."""
    # Remove script and style elements
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.IGNORECASE | re.DOTALL)

    # Replace common block tags with newlines
    for tag in (
        "</p>",
        "</div>",
        "</h[1-6]>",
        "</li>",
        "</tr>",
        "</blockquote>",
        "</pre>",
    ):
        text = re.sub(tag, "\n", text, flags=re.IGNORECASE)

    # Strip remaining HTML tags
    text = re.sub(r"<[^>]+>", " ", text)

    # Decode common HTML entities
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " ")

    # Collapse whitespace
    text = re.sub(r"\n\s*\n", "\n\n", text)
    text = re.sub(r" +", " ", text)

    return text.strip()


class UrlConnectorRuntime(ConnectorRuntime):
    """Read-only URL/web page import connector.

    Fetches a URL, extracts content, and returns it as a local data source.
    Blocks private/internal network addresses by default to prevent SSRF.
    """

    def __init__(
        self,
        allow_private: bool = False,
    ) -> None:
        self._allow_private = allow_private

    def test_connection(self, config: ConnectorConfig) -> dict[str, Any]:
        """Test that a URL is reachable and returns acceptable content."""
        url = config.config.get("url", "")
        if not url:
            return {"success": False, "message": "No URL configured"}

        # Validate URL format
        parsed = urlparse(url)
        if not parsed.netloc:
            return {"success": False, "message": f"Invalid URL format: {url}"}

        # Check private address
        if not self._allow_private and _is_private_host(parsed.hostname or ""):
            return {
                "success": False,
                "message": (
                    f"URL '{url}' points to a private/internal network address. "
                    "These are blocked by default for security."
                ),
            }

        try:
            async_resp = httpx.head(
                url,
                headers=self._headers(),
                timeout=_TIMEOUT,
                follow_redirects=True,
            )
            resp = async_resp
            if resp.status_code < 500:
                content_type = resp.headers.get("content-type", "").lower()
                return {
                    "success": True,
                    "message": f"URL is reachable (HTTP {resp.status_code})",
                    "content_type": content_type,
                    "status_code": resp.status_code,
                }
            else:
                return {
                    "success": False,
                    "message": f"URL returned HTTP {resp.status_code}",
                    "status_code": resp.status_code,
                }
        except httpx.TimeoutException:
            return {"success": False, "message": "Connection timed out"}
        except httpx.ConnectError:
            return {"success": False, "message": "Could not connect to host"}
        except Exception as e:
            return {"success": False, "message": f"Connection failed: {str(e)}"}

    def list_items(self, config: ConnectorConfig, path: str = "") -> list[ConnectorRuntimeItem]:
        """URL connector returns a single item (the page itself)."""
        url = config.config.get("url", "")
        if not url:
            return []
        return [
            ConnectorRuntimeItem(
                external_id=url,
                title=url,
                item_type="url",
                source_url=url,
                content_type="text/html",
            )
        ]

    def fetch_item(
        self, config: ConnectorConfig, item: ConnectorRuntimeItem
    ) -> ConnectorFetchedContent:
        """Fetch URL content, extract title and text."""
        url = item.source_url or config.config.get("url", "")
        if not url:
            return ConnectorFetchedContent(
                external_id=item.external_id,
                title=item.title,
                filename="page.txt",
                content_text="",
                content_type="text/plain",
                metadata={"error": "No URL provided"},
            )

        # Validate URL
        parsed = urlparse(url)
        if not parsed.netloc:
            return ConnectorFetchedContent(
                external_id=item.external_id,
                title=item.title,
                filename="page.txt",
                content_text="",
                content_type="text/plain",
                metadata={"error": f"Invalid URL: {url}"},
            )

        # Private address check
        if not self._allow_private and _is_private_host(parsed.hostname or ""):
            return ConnectorFetchedContent(
                external_id=item.external_id,
                title=item.title,
                filename="page.txt",
                content_text="[Blocked: URL points to a private/internal network address]",
                content_type="text/plain",
                metadata={
                    "error": "blocked_private_address",
                    "url": url,
                },
            )

        try:
            resp = httpx.get(
                url,
                headers=self._headers(),
                timeout=_TIMEOUT,
                follow_redirects=True,
            )
            if resp.status_code >= 400:
                return ConnectorFetchedContent(
                    external_id=item.external_id,
                    title=item.title,
                    filename="page.txt",
                    content_text="",
                    content_type="text/plain",
                    metadata={"error": f"HTTP {resp.status_code}"},
                )

            # Check size
            content = resp.content
            if len(content) > _MAX_RESPONSE_SIZE:
                content = content[:_MAX_RESPONSE_SIZE]
                truncated = True
            else:
                truncated = False

            content_type = resp.headers.get("content-type", "text/html").lower()
            text = content.decode("utf-8", errors="replace")

            # Extract title from HTML
            title = item.title
            if "html" in content_type:
                extracted_title = _extract_html_title(text)
                if extracted_title:
                    title = extracted_title
                text = _extract_html_text(text)

            return ConnectorFetchedContent(
                external_id=item.external_id,
                title=title,
                filename=f"{title[:50]}.txt" if title else "page.txt",
                content_text=text,
                content_type=content_type,
                metadata={
                    "url": url,
                    "status_code": resp.status_code,
                    "content_type": content_type,
                    "truncated": truncated,
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                },
            )

        except httpx.TimeoutException:
            return ConnectorFetchedContent(
                external_id=item.external_id,
                title=item.title,
                filename="page.txt",
                content_text="",
                content_type="text/plain",
                metadata={"error": "timeout", "url": url},
            )
        except httpx.ConnectError:
            return ConnectorFetchedContent(
                external_id=item.external_id,
                title=item.title,
                filename="page.txt",
                content_text="",
                content_type="text/plain",
                metadata={"error": "connection_error", "url": url},
            )
        except Exception as e:
            return ConnectorFetchedContent(
                external_id=item.external_id,
                title=item.title,
                filename="page.txt",
                content_text="",
                content_type="text/plain",
                metadata={"error": str(e), "url": url},
            )

    def sync(
        self,
        config: ConnectorConfig,
        path: str = "",
        item_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Fetch the URL and return its content."""
        items = self.list_items(config, path)
        if item_ids is not None:
            items = [i for i in items if i.external_id in item_ids]

        content_list = []
        for item in items:
            content = self.fetch_item(config, item)
            content_list.append(content)

        return {
            "items_found": len(items),
            "items_imported": len(content_list),
            "items_skipped": 0,
            "items_failed": 0,
            "content_list": content_list,
        }

    def _headers(self) -> dict[str, str]:
        return {
            "User-Agent": "AgenticDecisionSystem-Connector/1.28",
            "Accept": "text/html,text/plain,application/json,*/*",
        }


# Factory
def get_url_connector(allow_private: bool = False) -> UrlConnectorRuntime:
    return UrlConnectorRuntime(allow_private=allow_private)
