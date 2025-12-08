"""Google Calendar API service."""

import asyncio
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
