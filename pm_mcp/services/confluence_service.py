"""Confluence Cloud API service."""

import asyncio
from typing import Any

from atlassian import Confluence
from bs4 import BeautifulSoup
from requests import HTTPError

from pm_mcp.config import Settings
from pm_mcp.core.errors import ConfluenceError
from pm_mcp.services.base import BaseService, escape_query_value


class ConfluenceService(BaseService):
    """Service for Confluence Cloud API operations."""

    def __init__(self, settings: Settings | None = None) -> None:
        super().__init__(settings)
        self._client: Confluence | None = None

    def _get_client(self) -> Confluence:
        """Get or create Confluence client."""
        if self._client is None:
            self._client = Confluence(
                url=self.settings.confluence_base_url,
                username=self.settings.atlassian_email,
                password=self.settings.atlassian_api_token,
                cloud=True,
            )
        return self._client

    def _parse_html_to_text(self, html_content: str) -> str:
        """Parse HTML content to plain text."""
        if not html_content:
            return ""

        soup = BeautifulSoup(html_content, "lxml")

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        # Get text and normalize whitespace
        text = soup.get_text(separator="\n")
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = "\n".join(chunk for chunk in chunks if chunk)

        return text

    def _search_pages_sync(
        self,
        query: str,
        space_key: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Synchronous method to search Confluence pages.

        All user-provided values are escaped to prevent CQL injection.
        """
        client = self._get_client()

        # Build CQL query with escaped values
        cql_parts = [f'text ~ "{escape_query_value(query)}"']
        if space_key:
            cql_parts.append(f'space = "{escape_query_value(space_key)}"')
        cql_parts.append("type = page")

        cql = " AND ".join(cql_parts)

        try:
            results = client.cql(cql, limit=limit)

            pages = []
            for result in results.get("results", []):
                content = result.get("content", {})
                pages.append(
                    {
                        "id": content.get("id", ""),
                        "title": content.get("title", ""),
                        "url": f"{self.settings.confluence_base_url}{content.get('_links', {}).get('webui', '')}",
                        "space_key": content.get("space", {}).get("key", ""),
                        "last_modified": result.get("lastModified"),
                    }
                )

            return pages

        except HTTPError as e:
            self._log_error("search_pages", e)
            raise ConfluenceError(
                message="Failed to search pages. Check space key and permissions.",
                details={"operation": "search_pages"},
            ) from e
        except Exception as e:
            self._log_error("search_pages", e)
            raise ConfluenceError(
                message="Failed to search pages due to an unexpected error.",
                details={"operation": "search_pages"},
            ) from e

    async def search_pages(
        self,
        query: str,
        space_key: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search Confluence pages asynchronously."""
        return await asyncio.to_thread(
            self._search_pages_sync,
            query,
            space_key,
            limit,
        )

    def _get_page_content_sync(self, page_id: str) -> dict[str, Any]:
        """Synchronous method to get Confluence page content."""
        client = self._get_client()

        try:
            page = client.get_page_by_id(
                page_id,
                expand="body.storage,space",
            )

            html_content = page.get("body", {}).get("storage", {}).get("value", "")
            text_content = self._parse_html_to_text(html_content)

            return {
                "id": page.get("id", ""),
                "title": page.get("title", ""),
                "url": f"{self.settings.confluence_base_url}{page.get('_links', {}).get('webui', '')}",
                "body_text": text_content,
            }

        except HTTPError as e:
            self._log_error("get_page_content", e)
            raise ConfluenceError(
                message="Failed to get page content. Check page ID and permissions.",
                details={"operation": "get_page_content", "page_id": page_id},
            ) from e
        except Exception as e:
            self._log_error("get_page_content", e)
            raise ConfluenceError(
                message="Failed to get page content due to an unexpected error.",
                details={"operation": "get_page_content"},
            ) from e

    async def get_page_content(self, page_id: str) -> dict[str, Any]:
        """Get Confluence page content asynchronously."""
        return await asyncio.to_thread(self._get_page_content_sync, page_id)

    def _create_page_sync(
        self,
        space_key: str,
        title: str,
        body_markdown: str,
        parent_page_id: str | None = None,
    ) -> dict[str, Any]:
        """Synchronous method to create a Confluence page.

        Note: The body_markdown parameter undergoes basic conversion where only
        newlines are converted to <br/>. This is NOT full markdown support.
        For full markdown rendering, consider using a library like 'markdown'
        or 'mistune' to convert markdown to proper HTML/Confluence storage format.
        """
        client = self._get_client()

        # Basic conversion: newlines to <br/> only (not full markdown support)
        html_body = body_markdown.replace("\n", "<br/>")

        try:
            result = client.create_page(
                space=space_key,
                title=title,
                body=html_body,
                parent_id=parent_page_id,
            )

            return {
                "id": result.get("id", ""),
                "title": result.get("title", ""),
                "url": f"{self.settings.confluence_base_url}{result.get('_links', {}).get('webui', '')}",
            }

        except HTTPError as e:
            self._log_error("create_page", e)
            raise ConfluenceError(
                message="Failed to create page. Check space key and permissions.",
                details={"operation": "create_page", "space_key": space_key},
            ) from e
        except Exception as e:
            self._log_error("create_page", e)
            raise ConfluenceError(
                message="Failed to create page due to an unexpected error.",
                details={"operation": "create_page"},
            ) from e

    async def create_page(
        self,
        space_key: str,
        title: str,
        body_markdown: str,
        parent_page_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a Confluence page asynchronously."""
        return await asyncio.to_thread(
            self._create_page_sync,
            space_key,
            title,
            body_markdown,
            parent_page_id,
        )
