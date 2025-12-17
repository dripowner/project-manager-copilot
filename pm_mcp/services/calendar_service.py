"""Google Calendar API service."""

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError

from pm_mcp.config import Settings
from pm_mcp.core.errors import CalendarError
from pm_mcp.core.validation import validate_issue_keys, validate_metadata_dict
from pm_mcp.services.base import BaseService

logger = logging.getLogger(__name__)

# Valid ACL roles as per Google Calendar API
VALID_ACL_ROLES = {"owner", "writer", "reader", "freeBusyReader"}


class CalendarService(BaseService):
    """Service for Google Calendar API operations."""

    def __init__(self, settings: Settings | None = None) -> None:
        super().__init__(settings)
        self._service = None

    def _get_service(self) -> Resource:
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

        Supports two formats:
        1. JSON (new): {"jira_project_key": "ALPHA", "version": "v1"}
        2. Legacy (key=value): jira_project_key=ALPHA\\nconfluence_space_key=ALPHA

        Args:
            description: Calendar description string

        Returns:
            Dictionary with parsed metadata (validated against whitelist)
        """
        metadata = {"jira_project_key": None, "confluence_space_key": None}

        if not description:
            return metadata

        description = description.strip()

        # Try JSON format first (new format)
        if description.startswith("{"):
            try:
                parsed = json.loads(description)
                if isinstance(parsed, dict):
                    # Validate and filter metadata using whitelist
                    validated = validate_metadata_dict(parsed)
                    metadata.update(validated)
                    return metadata
            except json.JSONDecodeError:
                logger.warning("Failed to parse calendar metadata as JSON, falling back to legacy format")

        # Fallback to legacy key=value format
        for line in description.split("\n"):
            line = line.strip()
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                if key in metadata:
                    metadata[key] = value

        return metadata

    @staticmethod
    def _normalize_date_format(event_time: dict[str, Any]) -> dict[str, Any]:
        """Normalize event time format.

        Args:
            event_time: Event start/end time dict from Google Calendar API

        Returns:
            Dictionary with keys:
                - time: ISO 8601 string (dateTime or date)
                - is_all_day: bool indicating if event is all-day
        """
        if "dateTime" in event_time:
            return {"time": event_time["dateTime"], "is_all_day": False}
        elif "date" in event_time:
            return {"time": event_time["date"], "is_all_day": True}
        return {"time": None, "is_all_day": False}

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

        # Build metadata in JSON format (new format)
        metadata = {"jira_project_key": project_key, "version": "v1"}
        if confluence_space_key:
            metadata["confluence_space_key"] = confluence_space_key

        # Validate metadata against whitelist
        validated_metadata = validate_metadata_dict(metadata)
        description = json.dumps(validated_metadata)

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
        """Find calendar by project_key or create if not found.

        Handles race condition where multiple concurrent requests attempt
        to create the same calendar.
        """
        # Try to find existing calendar
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

        # Not found → try to create
        try:
            return self._create_project_calendar_sync(project_key, confluence_space_key)
        except HttpError as e:
            # Handle race condition: another process created the calendar
            if e.resp.status == 409:
                logger.info(f"Calendar '{project_key}' was created by another process, retrying find")
                # Retry find operation
                calendars = self._list_calendars_sync()
                for cal in calendars:
                    if cal["name"] == project_key and cal["jira_project_key"] == project_key:
                        cal["created"] = False
                        return cal
                # Still not found - let original error propagate
            raise

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

    def _verify_project_access_sync(
        self,
        project_key: str,
        user_email: str | None = None,
    ) -> dict[str, Any]:
        """Verify user access to project calendar via ACL (synchronous).

        Args:
            project_key: Jira project key
            user_email: User email to check. If None, uses calendar_owner_email from settings.

        Returns:
            dict with keys:
                - calendar: Calendar info dict
                - has_access: bool
                - role: str | None (owner/writer/reader/freeBusyReader)
                - user_email: str (checked email)
                - acl_entries_count: int
                - service_account_email: str | None

        Raises:
            CalendarError: If access verification fails or email not provided
        """
        # Resolve user_email
        if not user_email:
            user_email = self.settings.calendar_owner_email
            if not user_email:
                raise CalendarError(
                    message="user_email not provided and calendar_owner_email not configured",
                    details={
                        "config_keys": ["calendar_owner_email"],
                        "hint": "Provide user_email parameter or configure CALENDAR_OWNER_EMAIL env var",
                    },
                )

        # Find or create calendar
        calendar = self._find_or_create_project_calendar_sync(project_key)
        calendar_id = calendar["calendar_id"]

        # Get ACL from Google Calendar API
        service = self._get_service()

        try:
            acl_response = service.acl().list(calendarId=calendar_id).execute()
            acl_items = acl_response.get("items", [])

            # Find user in ACL entries
            user_acl = None
            for acl_entry in acl_items:
                scope = acl_entry.get("scope", {})
                if scope.get("type") == "user" and scope.get("value") == user_email:
                    user_acl = acl_entry
                    break

            # Issue #12: Only expose service account email in DEBUG mode
            service_account_email = (
                self.settings.google_service_account_email
                if self.settings.log_level == "DEBUG"
                else None
            )

            return {
                "calendar": calendar,
                "has_access": user_acl is not None,
                "role": user_acl.get("role") if user_acl else None,
                "user_email": user_email,
                "acl_entries_count": len(acl_items),
                "service_account_email": service_account_email,
            }

        except HttpError as e:
            self._log_error("verify_project_access", e)
            raise CalendarError(
                message=f"Failed to verify access for calendar {calendar_id}: {e.reason}",
                details={
                    "status_code": e.resp.status,
                    "calendar_id": calendar_id,
                    "project_key": project_key,
                    "user_email": user_email,
                },
            ) from e

    async def verify_project_access(
        self,
        project_key: str,
        user_email: str | None = None,
    ) -> dict[str, Any]:
        """Verify user access to project calendar asynchronously.

        Args:
            project_key: Jira project key
            user_email: User email to check (optional, uses calendar_owner_email if not provided)

        Returns:
            Dictionary with calendar info and access details
        """
        return await asyncio.to_thread(
            self._verify_project_access_sync,
            project_key,
            user_email,
        )

    def _grant_project_access_sync(
        self,
        project_key: str,
        user_email: str,
        role: str = "writer",
    ) -> dict[str, Any]:
        """Grant calendar access to user via ACL (synchronous).

        Args:
            project_key: Jira project key
            user_email: Email address to grant access to
            role: ACL role to grant (owner/writer/reader/freeBusyReader)

        Returns:
            dict with keys:
                - calendar: Calendar info dict
                - user_email: str (granted email)
                - role: str (granted role)
                - action_taken: str (granted/updated/already_exists)
                - previous_role: str | None

        Raises:
            CalendarError: If role is invalid or grant operation fails
        """
        # Validate role
        if role not in VALID_ACL_ROLES:
            raise CalendarError(
                message=f"Invalid role '{role}'. Must be one of: {', '.join(sorted(VALID_ACL_ROLES))}",
                details={
                    "provided_role": role,
                    "valid_roles": sorted(VALID_ACL_ROLES),
                },
            )

        # Validate user_email
        if not user_email:
            raise CalendarError(
                message="user_email is required and cannot be empty",
                details={"hint": "Provide a valid user email address"},
            )

        # Find or create calendar
        calendar = self._find_or_create_project_calendar_sync(project_key)
        calendar_id = calendar["calendar_id"]

        service = self._get_service()

        try:
            # Get current ACL to check if user already has access
            acl_response = service.acl().list(calendarId=calendar_id).execute()
            acl_items = acl_response.get("items", [])

            # Find existing user ACL entry
            existing_acl = None
            acl_rule_id = None
            for acl_entry in acl_items:
                scope = acl_entry.get("scope", {})
                if scope.get("type") == "user" and scope.get("value") == user_email:
                    existing_acl = acl_entry
                    acl_rule_id = acl_entry.get("id")
                    break

            action_taken = "granted"
            previous_role = None

            if existing_acl:
                current_role = existing_acl.get("role")
                if current_role == role:
                    # Already has the exact role - no action needed
                    action_taken = "already_exists"
                else:
                    # Role differs - update ACL entry
                    service.acl().update(
                        calendarId=calendar_id,
                        ruleId=acl_rule_id,
                        body={
                            "role": role,
                            "scope": {"type": "user", "value": user_email},
                        },
                    ).execute()
                    action_taken = "updated"
                    previous_role = current_role
            else:
                # No existing access - create new ACL entry
                service.acl().insert(
                    calendarId=calendar_id,
                    body={
                        "role": role,
                        "scope": {"type": "user", "value": user_email},
                    },
                ).execute()
                action_taken = "granted"

            return {
                "calendar": calendar,
                "user_email": user_email,
                "role": role,
                "action_taken": action_taken,
                "previous_role": previous_role,
            }

        except HttpError as e:
            self._log_error("grant_project_access", e)
            raise CalendarError(
                message=f"Failed to grant access for calendar {calendar_id}: {e.reason}",
                details={
                    "status_code": e.resp.status,
                    "calendar_id": calendar_id,
                    "project_key": project_key,
                    "user_email": user_email,
                    "role": role,
                },
            ) from e

    async def grant_project_access(
        self,
        project_key: str,
        user_email: str,
        role: str = "writer",
    ) -> dict[str, Any]:
        """Grant calendar access to user asynchronously.

        Args:
            project_key: Jira project key
            user_email: Email address to grant access to
            role: ACL role to grant (default: 'writer')

        Returns:
            Dictionary with calendar info and granted access details
        """
        return await asyncio.to_thread(
            self._grant_project_access_sync,
            project_key,
            user_email,
            role,
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

                # Normalize date format (handles all-day vs timed events)
                start_normalized = self._normalize_date_format(start)
                end_normalized = self._normalize_date_format(end)

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
                        "start": start_normalized["time"],
                        "end": end_normalized["time"],
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
            # Issue #13: Mask exception details in production
            raise CalendarError(
                message="Failed to list calendar events",
                details={"error_type": type(e).__name__},
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

        # Validate issue keys before storage (XSS prevention)
        validated_issues = validate_issue_keys(jira_issues) if jira_issues else []

        # Size validation (preventive check)
        metadata = {
            "jiraIssues": json.dumps(validated_issues),
        }
        if confluence_page_id:
            metadata["confluencePageId"] = confluence_page_id
        if project_key:
            metadata["projectKey"] = project_key

        # Size check (Google API limit ~8KB for extendedProperties)
        metadata_size = len(json.dumps(metadata))
        if metadata_size > 7000:  # Safety margin
            raise ValueError(
                f"Metadata size ({metadata_size} bytes) exceeds safe limit. "
                f"Consider reducing number of linked issues (current: {len(validated_issues)})"
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
            # Issue #13: Mask exception details in production
            raise CalendarError(
                message="Failed to update event metadata",
                details={"error_type": type(e).__name__, "event_id": event_id},
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

            # Parse jiraIssues with error handling for corrupted JSON
            jira_issues_str = private_props.get("jiraIssues", "[]")
            try:
                issue_keys = json.loads(jira_issues_str)
                if not isinstance(issue_keys, list):
                    logger.warning(f"Event {event_id}: jiraIssues is not a list, using empty list")
                    issue_keys = []
            except json.JSONDecodeError:
                logger.warning(f"Event {event_id}: corrupted JSON in jiraIssues, using empty list")
                issue_keys = []

            # Normalize meeting date
            start_time = event.get("start", {})
            meeting_date_normalized = self._normalize_date_format(start_time)

            return {
                "meeting_id": event_id,
                "issue_keys": issue_keys,
                "confluence_page_id": private_props.get("confluencePageId"),
                "project_key": private_props.get("projectKey"),
                "meeting_title": event.get("summary"),
                "meeting_date": meeting_date_normalized["time"],
            }

        except HttpError as e:
            # Consistent 404 handling - raise error instead of returning empty dict
            if e.resp.status == 404:
                raise CalendarError(
                    message=f"Event not found: {event_id}",
                    details={"status_code": 404, "event_id": event_id, "calendar_id": calendar_id},
                ) from e
            self._log_error("get_event_metadata", e)
            raise CalendarError(
                message=f"Failed to get event metadata: {e.reason}",
                details={"status_code": e.resp.status, "event_id": event_id},
            ) from e
        except Exception as e:
            self._log_error("get_event_metadata", e)
            # Issue #13: Mask exception details in production
            raise CalendarError(
                message="Failed to get event metadata",
                details={"error_type": type(e).__name__, "event_id": event_id},
            ) from e

    async def get_event_metadata(
        self, calendar_id: str, event_id: str
    ) -> dict[str, Any]:
        """Get PM metadata from event extendedProperties.private."""
        return await asyncio.to_thread(
            self._get_event_metadata_sync, calendar_id, event_id
        )
