"""Jira Cloud API service."""

import asyncio
from typing import Any

from atlassian import Jira
from requests import HTTPError

from pm_mcp.config import Settings
from pm_mcp.core.errors import JiraError
from pm_mcp.services.base import BaseService, escape_query_value


class JiraService(BaseService):
    """Service for Jira Cloud API operations."""

    def __init__(self, settings: Settings | None = None) -> None:
        super().__init__(settings)
        self._client: Jira | None = None

    def _get_client(self) -> Jira:
        """Get or create Jira client."""
        if self._client is None:
            self._client = Jira(
                url=self.settings.jira_base_url,
                username=self.settings.atlassian_email,
                password=self.settings.atlassian_api_token,
                cloud=True,
            )
        return self._client

    def _build_jql(
        self,
        project_key: str | None = None,
        status_category: str | None = None,
        assignee: str | None = None,
        labels: list[str] | None = None,
        updated_from: str | None = None,
        updated_to: str | None = None,
        text_query: str | None = None,
    ) -> str:
        """Build JQL query from filter parameters.

        All user-provided values are escaped to prevent JQL injection.
        """
        conditions = []

        if project_key:
            conditions.append(f'project = "{escape_query_value(project_key)}"')

        if status_category:
            conditions.append(
                f'statusCategory = "{escape_query_value(status_category)}"'
            )

        if assignee:
            conditions.append(f'assignee = "{escape_query_value(assignee)}"')

        if labels:
            label_conditions = [
                f'labels = "{escape_query_value(label)}"' for label in labels
            ]
            conditions.append(f"({' OR '.join(label_conditions)})")

        if updated_from:
            conditions.append(f'updated >= "{escape_query_value(updated_from)}"')

        if updated_to:
            conditions.append(f'updated <= "{escape_query_value(updated_to)}"')

        if text_query:
            conditions.append(f'text ~ "{escape_query_value(text_query)}"')

        return " AND ".join(conditions) if conditions else ""

    def _list_issues_sync(
        self,
        project_key: str | None = None,
        status_category: str | None = None,
        assignee: str | None = None,
        labels: list[str] | None = None,
        updated_from: str | None = None,
        updated_to: str | None = None,
        text_query: str | None = None,
        max_results: int = 50,
    ) -> list[dict[str, Any]]:
        """Synchronous method to list Jira issues."""
        client = self._get_client()

        jql = self._build_jql(
            project_key=project_key,
            status_category=status_category,
            assignee=assignee,
            labels=labels,
            updated_from=updated_from,
            updated_to=updated_to,
            text_query=text_query,
        )

        try:
            issues = client.jql(
                jql or "ORDER BY updated DESC",
                limit=max_results,
                fields="key,summary,status,assignee,labels,duedate,updated",
            )

            result = []
            for issue in issues.get("issues", []):
                fields = issue.get("fields", {})
                status = fields.get("status", {})
                assignee_data = fields.get("assignee") or {}
                status_category_data = status.get("statusCategory", {})

                result.append(
                    {
                        "key": issue.get("key", ""),
                        "id": issue.get("id", ""),
                        "url": f"{self.settings.jira_base_url}/browse/{issue.get('key', '')}",
                        "summary": fields.get("summary", ""),
                        "status": status.get("name", ""),
                        "status_category": status_category_data.get("name"),
                        "assignee": assignee_data.get("displayName")
                        or assignee_data.get("emailAddress"),
                        "labels": fields.get("labels"),
                        "due_date": fields.get("duedate"),
                        "updated": fields.get("updated"),
                    }
                )

            return result

        except HTTPError as e:
            self._log_error("list_issues", e)
            raise JiraError(
                message="Failed to list issues. Check project key and permissions.",
                details={"operation": "list_issues"},
            ) from e
        except Exception as e:
            self._log_error("list_issues", e)
            raise JiraError(
                message="Failed to list issues due to an unexpected error.",
                details={"operation": "list_issues"},
            ) from e

    async def list_issues(
        self,
        project_key: str | None = None,
        status_category: str | None = None,
        assignee: str | None = None,
        labels: list[str] | None = None,
        updated_from: str | None = None,
        updated_to: str | None = None,
        text_query: str | None = None,
        max_results: int = 50,
    ) -> list[dict[str, Any]]:
        """List Jira issues asynchronously."""
        return await asyncio.to_thread(
            self._list_issues_sync,
            project_key,
            status_category,
            assignee,
            labels,
            updated_from,
            updated_to,
            text_query,
            max_results,
        )

    def _create_issue_sync(
        self,
        project_key: str,
        summary: str,
        description: str | None = None,
        issue_type: str = "Task",
        assignee: str | None = None,
        labels: list[str] | None = None,
        due_date: str | None = None,
    ) -> dict[str, Any]:
        """Synchronous method to create a Jira issue."""
        client = self._get_client()

        fields: dict[str, Any] = {
            "project": {"key": project_key},
            "summary": summary,
            "issuetype": {"name": issue_type},
        }

        if description:
            fields["description"] = description

        if assignee:
            # Try to find user by email or account ID
            fields["assignee"] = {"id": assignee}

        if labels:
            fields["labels"] = labels

        if due_date:
            fields["duedate"] = due_date

        try:
            result = client.create_issue(fields=fields)
            return {
                "key": result.get("key", ""),
                "id": result.get("id", ""),
                "url": f"{self.settings.jira_base_url}/browse/{result.get('key', '')}",
            }
        except HTTPError as e:
            # Log detailed error information from Jira API
            error_details = {
                "operation": "create_issue",
                "project_key": project_key,
                "issue_type": issue_type,
                "fields": fields,
            }

            # Try to extract response body
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_details["response_status"] = e.response.status_code
                    error_details["response_body"] = e.response.text
                except Exception:
                    pass

            self._log_error("create_issue", e, extra_context=error_details)
            raise JiraError(
                message=f"Failed to create issue. Jira API error: {str(e)}",
                details=error_details,
            ) from e
        except Exception as e:
            self._log_error("create_issue", e)
            raise JiraError(
                message="Failed to create issue due to an unexpected error.",
                details={"operation": "create_issue"},
            ) from e

    async def create_issue(
        self,
        project_key: str,
        summary: str,
        description: str | None = None,
        issue_type: str = "Task",
        assignee: str | None = None,
        labels: list[str] | None = None,
        due_date: str | None = None,
    ) -> dict[str, Any]:
        """Create a Jira issue asynchronously."""
        return await asyncio.to_thread(
            self._create_issue_sync,
            project_key,
            summary,
            description,
            issue_type,
            assignee,
            labels,
            due_date,
        )

    async def create_issues_batch(
        self,
        project_key: str,
        issues: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Create multiple Jira issues."""
        results = []
        for issue_data in issues:
            result = await self.create_issue(
                project_key=project_key,
                summary=issue_data.get("summary", ""),
                description=issue_data.get("description"),
                issue_type=issue_data.get("issue_type", "Task"),
                assignee=issue_data.get("assignee"),
                labels=issue_data.get("labels"),
                due_date=issue_data.get("due_date"),
            )
            results.append(result)
        return results

    def _update_issue_sync(
        self,
        issue_key: str,
        summary: str | None = None,
        description: str | None = None,
        status: str | None = None,
        assignee: str | None = None,
        labels: list[str] | None = None,
        due_date: str | None = None,
    ) -> dict[str, Any]:
        """Synchronous method to update a Jira issue."""
        client = self._get_client()

        fields: dict[str, Any] = {}

        if summary:
            fields["summary"] = summary

        if description:
            fields["description"] = description

        if assignee:
            fields["assignee"] = {"id": assignee}

        if labels is not None:
            fields["labels"] = labels

        if due_date:
            fields["duedate"] = due_date

        try:
            if fields:
                client.update_issue_field(issue_key, fields)

            # Handle status transition separately
            if status:
                transitions = client.get_issue_transitions(issue_key)
                for transition in transitions:
                    if transition.get("name", "").lower() == status.lower():
                        client.issue_transition(issue_key, transition["id"])
                        break

            return {
                "key": issue_key,
                "url": f"{self.settings.jira_base_url}/browse/{issue_key}",
            }

        except HTTPError as e:
            self._log_error("update_issue", e)
            raise JiraError(
                message="Failed to update issue. Check issue key and permissions.",
                details={"operation": "update_issue", "issue_key": issue_key},
            ) from e
        except Exception as e:
            self._log_error("update_issue", e)
            raise JiraError(
                message="Failed to update issue due to an unexpected error.",
                details={"operation": "update_issue"},
            ) from e

    async def update_issue(
        self,
        issue_key: str,
        summary: str | None = None,
        description: str | None = None,
        status: str | None = None,
        assignee: str | None = None,
        labels: list[str] | None = None,
        due_date: str | None = None,
    ) -> dict[str, Any]:
        """Update a Jira issue asynchronously."""
        return await asyncio.to_thread(
            self._update_issue_sync,
            issue_key,
            summary,
            description,
            status,
            assignee,
            labels,
            due_date,
        )

    def _add_comment_sync(self, issue_key: str, body: str) -> dict[str, Any]:
        """Synchronous method to add a comment to a Jira issue."""
        client = self._get_client()

        try:
            result = client.issue_add_comment(issue_key, body)
            return {
                "issue_key": issue_key,
                "comment_id": result.get("id", ""),
            }
        except HTTPError as e:
            self._log_error("add_comment", e)
            raise JiraError(
                message="Failed to add comment. Check issue key and permissions.",
                details={"operation": "add_comment", "issue_key": issue_key},
            ) from e
        except Exception as e:
            self._log_error("add_comment", e)
            raise JiraError(
                message="Failed to add comment due to an unexpected error.",
                details={"operation": "add_comment"},
            ) from e

    async def add_comment(self, issue_key: str, body: str) -> dict[str, Any]:
        """Add a comment to a Jira issue asynchronously."""
        return await asyncio.to_thread(self._add_comment_sync, issue_key, body)

    def _get_issue_sync(self, issue_key: str) -> dict[str, Any] | None:
        """Synchronous method to get a single Jira issue by key."""
        client = self._get_client()

        try:
            issue = client.issue(
                issue_key,
                fields="key,summary,status,assignee,labels,duedate,updated",
            )

            if not issue:
                return None

            fields = issue.get("fields", {})
            status = fields.get("status", {})
            assignee_data = fields.get("assignee") or {}
            status_category_data = status.get("statusCategory", {})

            return {
                "key": issue.get("key", ""),
                "id": issue.get("id", ""),
                "url": f"{self.settings.jira_base_url}/browse/{issue.get('key', '')}",
                "summary": fields.get("summary", ""),
                "status": status.get("name", ""),
                "status_category": status_category_data.get("name"),
                "assignee": assignee_data.get("displayName")
                or assignee_data.get("emailAddress"),
                "labels": fields.get("labels"),
                "due_date": fields.get("duedate"),
                "updated": fields.get("updated"),
            }

        except HTTPError:
            # Issue not found or no access
            return None
        except Exception:
            return None

    async def get_issue(self, issue_key: str) -> dict[str, Any] | None:
        """Get a single Jira issue by key asynchronously."""
        return await asyncio.to_thread(self._get_issue_sync, issue_key)

    def _add_meeting_label_sync(
        self,
        issue_key: str,
        meeting_id: str,
    ) -> dict[str, Any]:
        """Sync implementation of add meeting label."""
        label = f"gcal:{meeting_id}"
        client = self._get_client()

        try:
            issue = client.issue(issue_key)
            current_labels = issue["fields"]["labels"] or []

            # Add new label if not exists
            if label not in current_labels:
                current_labels.append(label)
                client.update_issue_field(issue_key, {"labels": current_labels})

            return {"issue_key": issue_key, "label": label, "added": True}

        except HTTPError as e:
            self._log_error("add_meeting_label", e)
            raise JiraError(
                message="Failed to add meeting label. Check issue key and permissions.",
                details={"operation": "add_meeting_label", "issue_key": issue_key},
            ) from e
        except Exception as e:
            self._log_error("add_meeting_label", e)
            raise JiraError(
                message=f"Failed to add meeting label: {e}",
                details={"operation": "add_meeting_label"},
            ) from e

    async def add_meeting_label(
        self,
        issue_key: str,
        meeting_id: str,
    ) -> dict[str, Any]:
        """Add gcal:meeting_id label to Jira issue for reverse lookup."""
        return await asyncio.to_thread(
            self._add_meeting_label_sync,
            issue_key,
            meeting_id,
        )

    def _remove_meeting_label_sync(
        self,
        issue_key: str,
        meeting_id: str,
    ) -> dict[str, Any]:
        """Sync implementation of remove meeting label."""
        label = f"gcal:{meeting_id}"
        client = self._get_client()

        try:
            issue = client.issue(issue_key)
            current_labels = issue["fields"]["labels"] or []

            # Remove label if exists
            if label in current_labels:
                current_labels.remove(label)
                client.update_issue_field(issue_key, {"labels": current_labels})
                return {"issue_key": issue_key, "label": label, "removed": True}

            return {"issue_key": issue_key, "label": label, "removed": False}

        except HTTPError as e:
            self._log_error("remove_meeting_label", e)
            raise JiraError(
                message="Failed to remove meeting label. Check issue key and permissions.",
                details={"operation": "remove_meeting_label", "issue_key": issue_key},
            ) from e
        except Exception as e:
            self._log_error("remove_meeting_label", e)
            raise JiraError(
                message=f"Failed to remove meeting label: {e}",
                details={"operation": "remove_meeting_label"},
            ) from e

    async def remove_meeting_label(
        self,
        issue_key: str,
        meeting_id: str,
    ) -> dict[str, Any]:
        """Remove gcal:meeting_id label from Jira issue."""
        return await asyncio.to_thread(
            self._remove_meeting_label_sync,
            issue_key,
            meeting_id,
        )

    async def find_issues_by_meeting(
        self,
        meeting_id: str,
        project_key: str | None = None,
    ) -> list[dict[str, Any]]:
        """Find all issues linked to a meeting via gcal: labels."""
        # Use label as a filter through list_issues
        return await self.list_issues(
            labels=[f"gcal:{meeting_id}"],
            project_key=project_key,
            max_results=100,
        )
