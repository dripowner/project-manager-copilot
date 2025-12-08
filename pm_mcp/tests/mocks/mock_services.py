"""Mock implementations of services for testing."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock


class MockCalendarService:
    """Mock Google Calendar service."""

    def __init__(self) -> None:
        self.list_events = AsyncMock(return_value=self._default_events())

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


class MockDatabasePool:
    """Mock database pool for testing."""

    def __init__(self) -> None:
        self._data: dict[str, dict[str, Any]] = {}
        self._connection = MagicMock()
        self._connection.execute = AsyncMock()
        self._connection.fetchrow = AsyncMock(side_effect=self._fetchrow)
        self._connection.fetch = AsyncMock(return_value=[])

    async def init(self) -> None:
        """Initialize mock pool."""
        pass

    async def close(self) -> None:
        """Close mock pool."""
        pass

    @property
    def pool(self) -> MagicMock:
        """Get mock pool."""
        return MagicMock()

    class _ConnectionContext:
        def __init__(self, conn: MagicMock) -> None:
            self.conn = conn

        async def __aenter__(self) -> MagicMock:
            return self.conn

        async def __aexit__(self, *args: Any) -> None:
            pass

    def connection(self) -> "_ConnectionContext":
        """Get mock connection context."""
        return self._ConnectionContext(self._connection)

    def transaction(self) -> "_ConnectionContext":
        """Get mock transaction context."""
        return self._ConnectionContext(self._connection)

    async def _fetchrow(self, query: str, *args: Any) -> dict[str, Any] | None:
        """Mock fetchrow that returns stored data."""
        if args and args[0] in self._data:
            return self._data[args[0]]
        return None

    def set_meeting_data(self, meeting_id: str, data: dict[str, Any]) -> None:
        """Set mock data for a meeting."""
        self._data[meeting_id] = data
