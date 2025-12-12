"""Google Calendar API service."""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from google.oauth2 import service_account
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
        """Get or create Google Calendar service with Service Account."""
        if self._service is None:
            credentials_dict = self.settings.google_service_account_credentials
            if not credentials_dict:
                raise CalendarError(
                    message="Service account credentials not configured",
                    details={"config_keys": ["GOOGLE_SERVICE_ACCOUNT_KEY_JSON"]},
                )

            credentials = service_account.Credentials.from_service_account_info(
                credentials_dict,
                scopes=["https://www.googleapis.com/auth/calendar"],
            )

            self._service = build("calendar", "v3", credentials=credentials)
        return self._service

    def _parse_calendar_metadata(
        self, description: str | None
    ) -> dict[str, str | None]:
        """Parse calendar metadata from description.

        Expected format:
            jira_project_key=ALPHA
            confluence_space_key=ALPHA
        """
        metadata = {"jira_project_key": None, "confluence_space_key": None}

        if not description:
            return metadata

        for line in description.strip().split("\n"):
            line = line.strip()
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                if key in metadata:
                    metadata[key] = value

        return metadata

    def _list_calendars_sync(self) -> list[dict[str, Any]]:
        """List all calendars accessible to service account."""
        service = self._get_service()

        try:
            calendar_list = service.calendarList().list().execute()
            calendars = []

            for cal in calendar_list.get("items", []):
                metadata = self._parse_calendar_metadata(cal.get("description"))
                calendars.append(
                    {
                        "calendar_id": cal.get("id"),
                        "name": cal.get("summary"),
                        "description": cal.get("description"),
                        "primary": cal.get("primary", False),
                        "jira_project_key": metadata.get("jira_project_key"),
                        "confluence_space_key": metadata.get("confluence_space_key"),
                    }
                )

            return calendars

        except HttpError as e:
            self._log_error("list_calendars", e)
            raise CalendarError(
                message=f"Failed to list calendars: {e.reason}",
                details={"status_code": e.resp.status},
            ) from e

    async def list_calendars(self) -> list[dict[str, Any]]:
        """List all calendars asynchronously."""
        return await asyncio.to_thread(self._list_calendars_sync)

    def _create_project_calendar_sync(
        self,
        project_key: str,
        confluence_space_key: str | None = None,
    ) -> dict[str, Any]:
        """Create new calendar for project with metadata in description."""
        service = self._get_service()

        # Build description
        description_lines = [f"jira_project_key={project_key}"]
        if confluence_space_key:
            description_lines.append(f"confluence_space_key={confluence_space_key}")
        description = "\n".join(description_lines)

        calendar_body = {
            "summary": project_key,  # Calendar name = project_key
            "description": description,
            "timeZone": "UTC",
        }

        try:
            created_calendar = service.calendars().insert(body=calendar_body).execute()
            calendar_id = created_calendar.get("id")

            # Add calendar to calendarList so it becomes visible in list_calendars()
            # Without this, created calendars won't appear in calendarList().list()
            service.calendarList().insert(body={"id": calendar_id}).execute()

            # Share calendar with owner email if configured
            if self.settings.calendar_owner_email:
                service.acl().insert(
                    calendarId=calendar_id,
                    body={
                        "role": "owner",
                        "scope": {
                            "type": "user",
                            "value": self.settings.calendar_owner_email,
                        },
                    },
                ).execute()

            metadata = self._parse_calendar_metadata(
                created_calendar.get("description")
            )
            return {
                "calendar_id": calendar_id,
                "name": created_calendar.get("summary"),
                "description": created_calendar.get("description"),
                "primary": False,
                "jira_project_key": metadata.get("jira_project_key"),
                "confluence_space_key": metadata.get("confluence_space_key"),
                "created": True,
            }

        except HttpError as e:
            self._log_error("create_project_calendar", e)
            raise CalendarError(
                message=f"Failed to create calendar for project {project_key}: {e.reason}",
                details={"status_code": e.resp.status, "project_key": project_key},
            ) from e

    async def create_project_calendar(
        self,
        project_key: str,
        confluence_space_key: str | None = None,
    ) -> dict[str, Any]:
        """Create calendar for project asynchronously."""
        return await asyncio.to_thread(
            self._create_project_calendar_sync,
            project_key,
            confluence_space_key,
        )

    def _find_or_create_project_calendar_sync(
        self,
        project_key: str,
        confluence_space_key: str | None = None,
    ) -> dict[str, Any]:
        """Find calendar by project_key or create if not found."""
        calendars = self._list_calendars_sync()

        # Search by name
        for cal in calendars:
            if cal["name"] == project_key:
                # Validate metadata
                if cal["jira_project_key"] == project_key:
                    cal["created"] = False
                    return cal
                else:
                    # Name collision
                    raise CalendarError(
                        message=f"Calendar '{project_key}' exists but has different metadata",
                        details={
                            "expected_project_key": project_key,
                            "actual_project_key": cal["jira_project_key"],
                        },
                    )

        # Not found → create
        return self._create_project_calendar_sync(project_key, confluence_space_key)

    async def find_or_create_project_calendar(
        self,
        project_key: str,
        confluence_space_key: str | None = None,
    ) -> dict[str, Any]:
        """Find or create project calendar asynchronously."""
        return await asyncio.to_thread(
            self._find_or_create_project_calendar_sync,
            project_key,
            confluence_space_key,
        )

    def _list_events_sync(
        self,
        calendar_id: str,
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
                "calendarId": calendar_id,
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
        calendar_id: str,
        time_min: datetime | None = None,
        time_max: datetime | None = None,
        text_query: str | None = None,
        max_results: int = 50,
    ) -> list[dict[str, Any]]:
        """List calendar events asynchronously."""
        return await asyncio.to_thread(
            self._list_events_sync,
            calendar_id,
            time_min,
            time_max,
            text_query,
            max_results,
        )

    def _update_event_metadata_sync(
        self,
        calendar_id: str,
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
                    calendarId=calendar_id,
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
        calendar_id: str,
        event_id: str,
        jira_issues: list[str],
        confluence_page_id: str | None = None,
        project_key: str | None = None,
    ) -> dict[str, Any]:
        """Update event with PM metadata using extendedProperties.private."""
        return await asyncio.to_thread(
            self._update_event_metadata_sync,
            calendar_id,
            event_id,
            jira_issues,
            confluence_page_id,
            project_key,
        )

    def _get_event_metadata_sync(
        self, calendar_id: str, event_id: str
    ) -> dict[str, Any]:
        """Sync implementation of get event metadata."""
        service = self._get_service()

        try:
            event = (
                service.events().get(calendarId=calendar_id, eventId=event_id).execute()
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

    async def get_event_metadata(
        self, calendar_id: str, event_id: str
    ) -> dict[str, Any]:
        """Get PM metadata from event extendedProperties.private."""
        return await asyncio.to_thread(
            self._get_event_metadata_sync, calendar_id, event_id
        )
