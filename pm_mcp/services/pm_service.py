"""PM layer service using Calendar and Jira APIs."""

from datetime import datetime
from typing import Any

from pm_mcp.config import Settings
from pm_mcp.core.errors import PmError
from pm_mcp.services.base import BaseService


class PmService(BaseService):
    """Service for PM layer using Calendar API + Jira labels (no database)."""

    def __init__(self, settings: Settings | None = None) -> None:
        super().__init__(settings)
        # db_pool больше не нужен!

    async def link_meeting_issues(
        self,
        calendar_service: Any,  # CalendarService
        jira_service: Any,  # JiraService for labels
        meeting_id: str,
        issue_keys: list[str],
        confluence_page_id: str | None = None,
        meeting_title: str | None = None,  # Игнорируется - берется из Calendar
        meeting_date: datetime | None = None,  # Игнорируется - берется из Calendar
        project_key: str | None = None,
    ) -> dict[str, Any]:
        """Link meeting to issues using Calendar + Jira labels for bidirectional lookup."""
        try:
            # Step 1: Update Calendar event with issue keys (meeting → issues)
            await calendar_service.update_event_metadata(
                event_id=meeting_id,
                jira_issues=issue_keys,
                confluence_page_id=confluence_page_id,
                project_key=project_key,
            )

            # Step 2: Add gcal:meeting_id labels to each Jira issue (issue → meetings)
            errors = []
            for issue_key in issue_keys:
                try:
                    await jira_service.add_meeting_label(
                        issue_key=issue_key,
                        meeting_id=meeting_id,
                    )
                except Exception as e:
                    # Log error but continue with other issues
                    self._log_error(f"add_label_{issue_key}", e)
                    errors.append({"issue": issue_key, "error": str(e)})

            # Return result with potential errors
            result = {
                "meeting_id": meeting_id,
                "issue_keys": issue_keys,
                "confluence_page_id": confluence_page_id,
            }
            if errors:
                result["label_errors"] = errors

            return result

        except Exception as e:
            self._log_error("link_meeting_issues", e)
            raise PmError(
                message=f"Failed to link meeting to issues: {e}",
                details={"meeting_id": meeting_id},
            ) from e

    async def get_meeting_issues(
        self,
        calendar_service: Any,  # CalendarService
        meeting_id: str,
    ) -> dict[str, Any]:
        """Get issues linked to meeting from Calendar."""
        try:
            return await calendar_service.get_event_metadata(meeting_id)

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
