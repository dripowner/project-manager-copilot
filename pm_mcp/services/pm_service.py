"""PM layer service for PostgreSQL operations."""

import json
from datetime import datetime
from typing import Any

from pm_mcp.config import Settings
from pm_mcp.core.database import DatabasePool
from pm_mcp.core.errors import PmError
from pm_mcp.services.base import BaseService


class PmService(BaseService):
    """Service for PM layer database operations."""

    def __init__(
        self,
        db_pool: DatabasePool,
        settings: Settings | None = None,
    ) -> None:
        super().__init__(settings)
        self.db_pool = db_pool

    async def link_meeting_issues(
        self,
        meeting_id: str,
        issue_keys: list[str],
        confluence_page_id: str | None = None,
        meeting_title: str | None = None,
        meeting_date: datetime | None = None,
        project_key: str | None = None,
    ) -> dict[str, Any]:
        """Link meeting to Jira issues."""
        try:
            async with self.db_pool.connection() as conn:
                # Upsert meeting link
                await conn.execute(
                    """
                    INSERT INTO meeting_links (
                        meeting_id, confluence_page_id, meeting_title,
                        meeting_date, issue_keys, project_key, updated_at
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, NOW())
                    ON CONFLICT (meeting_id) DO UPDATE SET
                        confluence_page_id = COALESCE($2, meeting_links.confluence_page_id),
                        meeting_title = COALESCE($3, meeting_links.meeting_title),
                        meeting_date = COALESCE($4, meeting_links.meeting_date),
                        issue_keys = $5,
                        project_key = COALESCE($6, meeting_links.project_key),
                        updated_at = NOW()
                    """,
                    meeting_id,
                    confluence_page_id,
                    meeting_title,
                    meeting_date,
                    json.dumps(issue_keys),
                    project_key,
                )

            return {
                "meeting_id": meeting_id,
                "issue_keys": issue_keys,
                "confluence_page_id": confluence_page_id,
            }

        except Exception as e:
            self._log_error("link_meeting_issues", e)
            raise PmError(
                message=f"Failed to link meeting to issues: {e}",
                details={"meeting_id": meeting_id},
            ) from e

    async def get_meeting_issues(
        self,
        meeting_id: str,
    ) -> dict[str, Any]:
        """Get issues linked to a meeting."""
        try:
            async with self.db_pool.connection() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT meeting_id, confluence_page_id, meeting_title,
                           meeting_date, issue_keys, project_key
                    FROM meeting_links
                    WHERE meeting_id = $1
                    """,
                    meeting_id,
                )

                if row is None:
                    return {
                        "meeting_id": meeting_id,
                        "issue_keys": [],
                        "confluence_page_id": None,
                    }

                issue_keys = json.loads(row["issue_keys"]) if row["issue_keys"] else []

                return {
                    "meeting_id": row["meeting_id"],
                    "confluence_page_id": row["confluence_page_id"],
                    "meeting_title": row["meeting_title"],
                    "meeting_date": row["meeting_date"].isoformat()
                    if row["meeting_date"]
                    else None,
                    "issue_keys": issue_keys,
                    "project_key": row["project_key"],
                }

        except Exception as e:
            self._log_error("get_meeting_issues", e)
            raise PmError(
                message=f"Failed to get meeting issues: {e}",
                details={"meeting_id": meeting_id},
            ) from e

    async def get_project_snapshot(
        self,
        project_key: str,
        jira_service: Any,  # JiraService, avoiding circular import
        since: str | None = None,
    ) -> dict[str, Any]:
        """Get aggregated project statistics."""
        try:
            # Get issues from Jira
            all_issues = await jira_service.list_issues(
                project_key=project_key,
                max_results=500,
            )

            # Calculate statistics
            total_open = 0
            total_in_progress = 0
            total_done = 0
            total_overdue = 0
            by_assignee: dict[str, int] = {}

            today = datetime.now().date()

            for issue in all_issues:
                status_category = issue.get("status_category", "")

                if status_category == "To Do":
                    total_open += 1
                elif status_category == "In Progress":
                    total_in_progress += 1
                elif status_category == "Done":
                    total_done += 1

                # Check overdue
                due_date = issue.get("due_date")
                if due_date and status_category != "Done":
                    try:
                        due = datetime.fromisoformat(due_date).date()
                        if due < today:
                            total_overdue += 1
                    except (ValueError, TypeError):
                        pass

                # Count by assignee
                assignee = issue.get("assignee") or "Unassigned"
                by_assignee[assignee] = by_assignee.get(assignee, 0) + 1

            return {
                "project_key": project_key,
                "total_open": total_open,
                "total_in_progress": total_in_progress,
                "total_done": total_done,
                "total_overdue": total_overdue,
                "by_assignee": by_assignee,
            }

        except Exception as e:
            self._log_error("get_project_snapshot", e)
            raise PmError(
                message=f"Failed to get project snapshot: {e}",
                details={"project_key": project_key},
            ) from e
