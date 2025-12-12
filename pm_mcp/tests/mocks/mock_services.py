"""Mock implementations of services for testing."""

import json
from typing import Any
from unittest.mock import AsyncMock


class MockCalendarService:
    """Mock Google Calendar service with extendedProperties support."""

    def __init__(self) -> None:
        self.list_events = AsyncMock(side_effect=self._list_events)
        self.update_event_metadata = AsyncMock(side_effect=self._update_event_metadata)
        self.get_event_metadata = AsyncMock(side_effect=self._get_event_metadata)
        self.list_calendars = AsyncMock(side_effect=self._list_calendars)
        self.find_or_create_project_calendar = AsyncMock(
            side_effect=self._find_or_create_project_calendar
        )
        self.create_project_calendar = AsyncMock(
            side_effect=self._create_project_calendar
        )

        # In-memory storage: event_id -> extendedProperties.private
        self._events_metadata: dict[str, dict[str, Any]] = {}

        # Mock events data (for get_event_metadata)
        self._events: dict[str, dict[str, Any]] = {
            "event1": {
                "id": "event1",
                "summary": "Sprint Planning",
                "start": {"dateTime": "2024-01-15T10:00:00+00:00"},
            },
            "event2": {
                "id": "event2",
                "summary": "Retrospective",
                "start": {"dateTime": "2024-01-16T14:00:00+00:00"},
            },
        }

        # Mock calendars storage: calendar_id -> calendar data
        self._calendars: dict[str, dict[str, Any]] = {
            "calendar_alpha": {
                "calendar_id": "calendar_alpha",
                "name": "ALPHA",
                "description": "jira_project_key=ALPHA\nconfluence_space_key=ALPHA",
                "primary": False,
                "jira_project_key": "ALPHA",
                "confluence_space_key": "ALPHA",
            },
            "calendar_beta": {
                "calendar_id": "calendar_beta",
                "name": "BETA",
                "description": "jira_project_key=BETA",
                "primary": False,
                "jira_project_key": "BETA",
                "confluence_space_key": None,
            },
        }
        self._calendar_counter = 0

    def _default_events(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "event1",
                "summary": "Sprint Planning",
                "description": "Weekly sprint planning meeting",
                "start": "2024-01-15T10:00:00+00:00",
                "end": "2024-01-15T11:00:00+00:00",
                "location": "Room A",
                "attendees": ["alice@example.com", "bob@example.com"],
            },
            {
                "id": "event2",
                "summary": "Retrospective",
                "description": None,
                "start": "2024-01-16T14:00:00+00:00",
                "end": "2024-01-16T15:00:00+00:00",
                "location": None,
                "attendees": None,
            },
        ]

    def set_event(self, event_id: str, summary: str, start_datetime: str) -> None:
        """Set mock event data."""
        self._events[event_id] = {
            "id": event_id,
            "summary": summary,
            "start": {"dateTime": start_datetime},
        }

    async def _list_events(
        self,
        calendar_id: str,
        time_min: Any = None,
        time_max: Any = None,
        text_query: str | None = None,
        max_results: int = 50,
    ) -> list[dict[str, Any]]:
        """Mock list events with calendar_id parameter."""
        return self._default_events()

    async def _update_event_metadata(
        self,
        calendar_id: str,
        event_id: str,
        jira_issues: list[str],
        confluence_page_id: str | None = None,
        project_key: str | None = None,
    ) -> dict[str, Any]:
        """Mock update event metadata."""
        metadata = {
            "jiraIssues": json.dumps(jira_issues),
        }
        if confluence_page_id:
            metadata["confluencePageId"] = confluence_page_id
        if project_key:
            metadata["projectKey"] = project_key

        self._events_metadata[event_id] = metadata

        return {"id": event_id, "extendedProperties": {"private": metadata}}

    async def _get_event_metadata(
        self, calendar_id: str, event_id: str
    ) -> dict[str, Any]:
        """Mock get event metadata."""
        private_props = self._events_metadata.get(event_id, {})
        event_data = self._events.get(event_id, {})

        return {
            "meeting_id": event_id,
            "issue_keys": json.loads(private_props.get("jiraIssues", "[]")),
            "confluence_page_id": private_props.get("confluencePageId"),
            "project_key": private_props.get("projectKey"),
            "meeting_title": event_data.get("summary"),
            "meeting_date": event_data.get("start", {}).get("dateTime"),
        }

    async def _list_calendars(self) -> list[dict[str, Any]]:
        """Mock list all calendars."""
        return list(self._calendars.values())

    async def _create_project_calendar(
        self,
        project_key: str,
        confluence_space_key: str | None = None,
    ) -> dict[str, Any]:
        """Mock create calendar for project."""
        self._calendar_counter += 1
        calendar_id = f"calendar_{project_key.lower()}_{self._calendar_counter}"

        description_lines = [f"jira_project_key={project_key}"]
        if confluence_space_key:
            description_lines.append(f"confluence_space_key={confluence_space_key}")
        description = "\n".join(description_lines)

        calendar = {
            "calendar_id": calendar_id,
            "name": project_key,
            "description": description,
            "primary": False,
            "jira_project_key": project_key,
            "confluence_space_key": confluence_space_key,
            "created": True,
        }

        self._calendars[calendar_id] = calendar
        return calendar

    async def _find_or_create_project_calendar(
        self,
        project_key: str,
        confluence_space_key: str | None = None,
    ) -> dict[str, Any]:
        """Mock find or create calendar for project."""
        # Search by name
        for calendar in self._calendars.values():
            if calendar["name"] == project_key:
                calendar["created"] = False
                return calendar

        # Not found -> create
        return await self._create_project_calendar(project_key, confluence_space_key)


class MockJiraService:
    """Mock Jira service."""

    def __init__(self) -> None:
        self.list_issues = AsyncMock(return_value=self._default_issues())
        self.create_issue = AsyncMock(side_effect=self._create_issue)
        self.create_issues_batch = AsyncMock(side_effect=self._create_issues_batch)
        self.update_issue = AsyncMock(
            return_value={
                "key": "PROJ-1",
                "url": "https://jira.example.com/browse/PROJ-1",
            }
        )
        self.add_comment = AsyncMock(
            return_value={"issue_key": "PROJ-1", "comment_id": "10001"}
        )
        self.get_issue = AsyncMock(side_effect=self._get_issue)
        self._issue_counter = 0
        self._issues_by_key = {issue["key"]: issue for issue in self._default_issues()}

    def _default_issues(self) -> list[dict[str, Any]]:
        return [
            {
                "key": "PROJ-1",
                "id": "10001",
                "url": "https://jira.example.com/browse/PROJ-1",
                "summary": "Implement feature X",
                "status": "In Progress",
                "status_category": "In Progress",
                "assignee": "Alice",
                "labels": ["backend"],
                "due_date": "2024-01-20",
                "updated": "2024-01-15T10:00:00+00:00",
            },
            {
                "key": "PROJ-2",
                "id": "10002",
                "url": "https://jira.example.com/browse/PROJ-2",
                "summary": "Fix bug Y",
                "status": "To Do",
                "status_category": "To Do",
                "assignee": None,
                "labels": [],
                "due_date": None,
                "updated": "2024-01-14T09:00:00+00:00",
            },
        ]

    def _create_issue(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        self._issue_counter += 1
        key = f"PROJ-{100 + self._issue_counter}"
        return {
            "key": key,
            "id": str(10000 + self._issue_counter),
            "url": f"https://jira.example.com/browse/{key}",
        }

    async def _create_issues_batch(
        self, project_key: str, issues: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        results = []
        for _ in issues:
            results.append(self._create_issue())
        return results

    def _get_issue(self, issue_key: str) -> dict[str, Any] | None:
        """Get issue by key from mock data."""
        return self._issues_by_key.get(issue_key)

    async def add_meeting_label(
        self, issue_key: str, meeting_id: str
    ) -> dict[str, Any]:
        """Mock add meeting label."""
        label = f"gcal:{meeting_id}"
        issue = self._issues_by_key.get(issue_key)
        if issue:
            if label not in issue["labels"]:
                issue["labels"].append(label)
        return {"issue_key": issue_key, "label": label, "added": True}

    async def remove_meeting_label(
        self, issue_key: str, meeting_id: str
    ) -> dict[str, Any]:
        """Mock remove meeting label."""
        label = f"gcal:{meeting_id}"
        issue = self._issues_by_key.get(issue_key)
        if issue and label in issue["labels"]:
            issue["labels"].remove(label)
            return {"issue_key": issue_key, "label": label, "removed": True}
        return {"issue_key": issue_key, "label": label, "removed": False}

    async def find_issues_by_meeting(
        self, meeting_id: str, project_key: str | None = None
    ) -> list[dict[str, Any]]:
        """Mock find issues by meeting."""
        label = f"gcal:{meeting_id}"
        results = []
        for issue in self._issues_by_key.values():
            if label in issue["labels"]:
                if project_key is None or issue["key"].startswith(project_key):
                    results.append(issue)
        return results


class MockConfluenceService:
    """Mock Confluence service."""

    def __init__(self) -> None:
        self.search_pages = AsyncMock(return_value=self._default_pages())
        self.get_page_content = AsyncMock(return_value=self._default_page_content())
        self.create_page = AsyncMock(return_value=self._default_created_page())

    def _default_pages(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "123456",
                "title": "Sprint 10 Planning Notes",
                "url": "https://confluence.example.com/pages/viewpage.action?pageId=123456",
                "space_key": "TEAM",
                "last_modified": "2024-01-15T10:30:00+00:00",
            },
        ]

    def _default_page_content(self) -> dict[str, Any]:
        return {
            "id": "123456",
            "title": "Sprint 10 Planning Notes",
            "url": "https://confluence.example.com/pages/viewpage.action?pageId=123456",
            "body_text": """Sprint 10 Planning Notes

Attendees: Alice, Bob, Charlie

Action Items:
1. Alice: Complete API documentation by Friday
2. Bob: Review pull request #123
3. Charlie: Setup staging environment

Decisions:
- Use PostgreSQL for the new service
- Deploy to production next Monday
""",
        }

    def _default_created_page(self) -> dict[str, Any]:
        return {
            "id": "789012",
            "title": "New Meeting Notes",
            "url": "https://confluence.example.com/pages/viewpage.action?pageId=789012",
        }
