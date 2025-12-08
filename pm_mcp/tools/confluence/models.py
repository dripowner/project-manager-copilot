"""Pydantic models for Confluence tools."""

from pydantic import Field

from pm_mcp.core.models import BaseMcpModel


# Search pages models
class ConfluenceSearchPagesRequest(BaseMcpModel):
    """Request model for confluence_search_pages tool."""

    query: str = Field(description="Text query for CQL search")
    space_key: str | None = Field(
        default=None,
        description="Optional Confluence space key to restrict search",
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of pages to return",
    )


class ConfluencePageSummary(BaseMcpModel):
    """Summary of a Confluence page."""

    id: str = Field(description="Page ID")
    title: str = Field(description="Page title")
    url: str = Field(description="Direct URL to page in Confluence")
    space_key: str = Field(description="Space key")
    last_modified: str | None = Field(
        default=None, description="Last modification timestamp"
    )


class ConfluenceSearchPagesResponse(BaseMcpModel):
    """Response model for confluence_search_pages tool."""

    pages: list[ConfluencePageSummary] = Field(description="List of matching pages")


# Get page content models
class ConfluenceGetPageContentRequest(BaseMcpModel):
    """Request model for confluence_get_page_content tool."""

    page_id: str = Field(description="Confluence page ID")


class ConfluencePageContent(BaseMcpModel):
    """Full content of a Confluence page."""

    id: str = Field(description="Page ID")
    title: str = Field(description="Page title")
    url: str = Field(description="Direct URL to page")
    body_text: str = Field(description="Page content as plain text (HTML parsed)")


# Create page models
class ConfluenceCreateMeetingPageRequest(BaseMcpModel):
    """Request model for confluence_create_meeting_page tool."""

    space_key: str = Field(description="Confluence space key")
    title: str = Field(description="Page title")
    body_markdown: str = Field(description="Page content in markdown format")
    parent_page_id: str | None = Field(
        default=None,
        description="Optional parent page ID for hierarchy",
    )


class ConfluenceCreateMeetingPageResponse(BaseMcpModel):
    """Response model for confluence_create_meeting_page tool."""

    id: str = Field(description="Created page ID")
    title: str = Field(description="Page title")
    url: str = Field(description="Direct URL to the new page")
