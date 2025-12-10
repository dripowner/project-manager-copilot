"""Google Calendar API service."""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from pm_mcp.config import Settings
from pm_mcp.core.errors import CalendarError
from pm_mcp.services.base import BaseService


class CalendarService(BaseService):
    """Service for Google Calendar API operations."""

    def __init__(self, settings: Settings | None = None) -> None:
        super().__init__(settings)
        self._service = None

    def _get_service(self) -> Any:
        """Get or create Google Calendar service."""
        if self._service is None:
            self._service = build(
                "calendar",
                "v3",
                developerKey=self.settings.google_api_key,
            )
        return self._service

    def _list_events_sync(
        self,
        time_min: datetime | None = None,
        time_max: datetime | None = None,
        text_query: str | None = None,
        max_results: int = 50,
    ) -> list[dict[str, Any]]:
        """Synchronous method to list calendar events."""
        service = self._get_service()

        now = datetime.now(timezone.utc)
        if time_min is None:
            time_min = now - timedelta(days=7)
        if time_max is None:
            time_max = now + timedelta(days=7)

        try:
            request_params: dict[str, Any] = {
                "calendarId": self.settings.google_calendar_id,
                "timeMin": time_min.isoformat(),
                "timeMax": time_max.isoformat(),
                "maxResults": max_results,
                "singleEvents": True,
                "orderBy": "startTime",
            }

            if text_query:
                request_params["q"] = text_query

            events_result = service.events().list(**request_params).execute()
            events = events_result.get("items", [])

            result = []
            for event in events:
                start = event.get("start", {})
                end = event.get("end", {})

                # Handle all-day events (date) vs timed events (dateTime)
                start_time = start.get("dateTime") or start.get("date")
                end_time = end.get("dateTime") or end.get("date")

                attendees = []
                for attendee in event.get("attendees", []):
                    attendees.append(
                        attendee.get("displayName") or attendee.get("email", "")
                    )

                result.append(
                    {
                        "id": event.get("id", ""),
                        "summary": event.get("summary", ""),
                        "description": event.get("description"),
                        "start": start_time,
                        "end": end_time,
                        "location": event.get("location"),
                        "attendees": attendees if attendees else None,
                    }
                )

            return result

        except HttpError as e:
            self._log_error("list_events", e)
            raise CalendarError(
                message=f"Failed to list calendar events: {e.reason}",
                details={"status_code": e.resp.status},
            ) from e
        except Exception as e:
            self._log_error("list_events", e)
            raise CalendarError(
                message=f"Failed to list calendar events: {e}",
            ) from e

    async def list_events(
        self,
        time_min: datetime | None = None,
        time_max: datetime | None = None,
        text_query: str | None = None,
        max_results: int = 50,
    ) -> list[dict[str, Any]]:
        """List calendar events asynchronously."""
        return await asyncio.to_thread(
            self._list_events_sync,
            time_min,
            time_max,
            text_query,
            max_results,
        )

    def _update_event_metadata_sync(
        self,
        event_id: str,
        jira_issues: list[str],
        confluence_page_id: str | None = None,
        project_key: str | None = None,
    ) -> dict[str, Any]:
        """Sync implementation of update event metadata."""
        service = self._get_service()

        # Валидация размера (превентивная проверка)
        metadata = {
            "jiraIssues": json.dumps(jira_issues),
        }
        if confluence_page_id:
            metadata["confluencePageId"] = confluence_page_id
        if project_key:
            metadata["projectKey"] = project_key

        # Проверка размера (Google API лимит ~8KB для extendedProperties)
        metadata_size = len(json.dumps(metadata))
        if metadata_size > 7000:  # Safety margin
            raise ValueError(
                f"Metadata size ({metadata_size} bytes) exceeds safe limit. "
                f"Consider reducing number of linked issues (current: {len(jira_issues)})"
            )

        try:
            event = (
                service.events()
                .patch(
                    calendarId="primary",  # Публичный календарь команды
                    eventId=event_id,
                    body={"extendedProperties": {"private": metadata}},
                )
                .execute()
            )
            return event

        except HttpError as e:
            self._log_error("update_event_metadata", e)
            raise CalendarError(
                message=f"Failed to update event metadata: {e.reason}",
                details={"status_code": e.resp.status, "event_id": event_id},
            ) from e
        except Exception as e:
            self._log_error("update_event_metadata", e)
            raise CalendarError(
                message=f"Failed to update event metadata: {e}",
                details={"event_id": event_id},
            ) from e

    async def update_event_metadata(
        self,
        event_id: str,
        jira_issues: list[str],
        confluence_page_id: str | None = None,
        project_key: str | None = None,
    ) -> dict[str, Any]:
        """Update event with PM metadata using extendedProperties.private."""
        return await asyncio.to_thread(
            self._update_event_metadata_sync,
            event_id,
            jira_issues,
            confluence_page_id,
            project_key,
        )

    def _get_event_metadata_sync(self, event_id: str) -> dict[str, Any]:
        """Sync implementation of get event metadata."""
        service = self._get_service()

        try:
            event = (
                service.events().get(calendarId="primary", eventId=event_id).execute()
            )

            private_props = event.get("extendedProperties", {}).get("private", {})

            return {
                "meeting_id": event_id,
                "issue_keys": json.loads(private_props.get("jiraIssues", "[]")),
                "confluence_page_id": private_props.get("confluencePageId"),
                "project_key": private_props.get("projectKey"),
                "meeting_title": event.get("summary"),
                "meeting_date": event.get("start", {}).get("dateTime"),
            }

        except HttpError as e:
            # Handle 404 - event not found
            if e.resp.status == 404:
                return {
                    "meeting_id": event_id,
                    "issue_keys": [],
                    "confluence_page_id": None,
                    "project_key": None,
                    "meeting_title": None,
                    "meeting_date": None,
                }
            self._log_error("get_event_metadata", e)
            raise CalendarError(
                message=f"Failed to get event metadata: {e.reason}",
                details={"status_code": e.resp.status, "event_id": event_id},
            ) from e
        except Exception as e:
            self._log_error("get_event_metadata", e)
            raise CalendarError(
                message=f"Failed to get event metadata: {e}",
                details={"event_id": event_id},
            ) from e

    async def get_event_metadata(self, event_id: str) -> dict[str, Any]:
        """Get PM metadata from event extendedProperties.private."""
        return await asyncio.to_thread(self._get_event_metadata_sync, event_id)
