"""Confluence MCP tools implementation."""

from typing import Annotated

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.context import Context
from pydantic import Field

from pm_mcp.core.errors import ConfluenceError
from pm_mcp.tools.confluence.models import (
    ConfluenceCreateMeetingPageResponse,
    ConfluencePageContent,
    ConfluencePageSummary,
    ConfluenceSearchPagesResponse,
)


def register_confluence_tools(mcp: FastMCP) -> None:
    """Register Confluence tools with the MCP server.

    Tools access ConfluenceService via ctx.fastmcp.confluence_service.
    """

    @mcp.tool(
        name="confluence_search_pages",
        description="Search for Confluence pages by text query. "
        "Use to find meeting notes, protocols, or documentation by topic/title/date.",
    )
    async def confluence_search_pages(
        query: Annotated[str, Field(description="Text query for CQL search")],
        ctx: Context,
        space_key: Annotated[
            str | None,
            Field(description="Optional Confluence space key to restrict search"),
        ] = None,
        limit: Annotated[
            int,
            Field(
                ge=1, le=100, description="Maximum number of pages to return (1-100)"
            ),
        ] = 10,
    ) -> ConfluenceSearchPagesResponse:
        """Search Confluence pages."""
        await ctx.info(f"Searching Confluence pages: '{query}'")
        try:
            confluence_service = ctx.fastmcp.confluence_service  # type: ignore[attr-defined]
            await ctx.debug(f"Params: space_key={space_key}, limit={limit}")
            pages = await confluence_service.search_pages(
                query=query,
                space_key=space_key,
                limit=limit,
            )

            await ctx.info(f"Found {len(pages)} Confluence pages")
            return ConfluenceSearchPagesResponse(
                pages=[ConfluencePageSummary(**page) for page in pages]
            )

        except ConfluenceError as e:
            raise ToolError(e.message) from e
        except Exception as e:
            raise ToolError(f"Failed to search Confluence pages: {e}") from e

    @mcp.tool(
        name="confluence_get_page_content",
        description="Get the full text content of a Confluence page. "
        "Use to read meeting protocols, extract action items, or analyze documentation.",
    )
    async def confluence_get_page_content(
        page_id: Annotated[str, Field(description="Confluence page ID")],
        ctx: Context,
    ) -> ConfluencePageContent:
        """Get Confluence page content."""
        await ctx.info(f"Fetching Confluence page content: {page_id}")
        try:
            confluence_service = ctx.fastmcp.confluence_service  # type: ignore[attr-defined]
            page = await confluence_service.get_page_content(page_id=page_id)
            await ctx.debug(f"Retrieved page: {page.get('title', 'N/A')}")
            return ConfluencePageContent(**page)

        except ConfluenceError as e:
            raise ToolError(e.message) from e
        except Exception as e:
            raise ToolError(f"Failed to get page content: {e}") from e

    @mcp.tool(
        name="confluence_create_meeting_page",
        description="Create a new Confluence page for meeting notes/protocol. "
        "Use to document meeting outcomes, decisions, and action items.",
    )
    async def confluence_create_meeting_page(
        space_key: Annotated[str, Field(description="Confluence space key")],
        title: Annotated[str, Field(description="Page title")],
        body_markdown: Annotated[
            str, Field(description="Page content in markdown format")
        ],
        ctx: Context,
        parent_page_id: Annotated[
            str | None,
            Field(description="Optional parent page ID for hierarchy"),
        ] = None,
    ) -> ConfluenceCreateMeetingPageResponse:
        """Create Confluence meeting page."""
        await ctx.info(f"Creating Confluence page: '{title}' in space {space_key}")
        try:
            confluence_service = ctx.fastmcp.confluence_service  # type: ignore[attr-defined]
            await ctx.debug(
                f"Params: parent_page_id={parent_page_id}, "
                f"body_length={len(body_markdown)} chars"
            )
            page = await confluence_service.create_page(
                space_key=space_key,
                title=title,
                body_markdown=body_markdown,
                parent_page_id=parent_page_id,
            )

            await ctx.info(f"Created page with ID: {page.get('id', 'N/A')}")
            return ConfluenceCreateMeetingPageResponse(**page)

        except ConfluenceError as e:
            raise ToolError(e.message) from e
        except Exception as e:
            raise ToolError(f"Failed to create meeting page: {e}") from e
