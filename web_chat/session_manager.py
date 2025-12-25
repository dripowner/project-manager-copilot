"""Chat session management for Chainlit."""

import logging

import httpx

from web_chat.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


async def create_chat_session(
    token: str,
    title: str | None = None,
) -> dict:
    """Create new chat session via auth_service API.

    Args:
        token: JWT authentication token
        title: Optional chat title

    Returns:
        Created chat session data

    Raises:
        Exception: If API request fails
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.auth_service_url}/users/me/chat_sessions",
            json={"title": title},
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )

        if response.status_code != 200:
            raise Exception(f"Failed to create chat: {response.text}")

        return response.json()


async def list_chat_sessions(token: str) -> list[dict]:
    """List user's chat sessions.

    Args:
        token: JWT authentication token

    Returns:
        List of chat sessions

    Note:
        Returns empty list on error to allow graceful degradation
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{settings.auth_service_url}/users/me/chat_sessions",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )

        if response.status_code != 200:
            logger.error(f"Failed to list chats: {response.status_code}")
            return []

        return response.json()


async def get_chat_session(
    thread_id: str,
    token: str,
) -> dict | None:
    """Get chat session by thread_id.

    Args:
        thread_id: Thread ID
        token: JWT authentication token

    Returns:
        Chat session data or None if not found
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{settings.auth_service_url}/chat_sessions/{thread_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )

        if response.status_code != 200:
            return None

        return response.json()


async def update_chat_session(
    thread_id: str,
    token: str,
    title: str | None = None,
    increment_message: bool = False,
) -> bool:
    """Update chat session.

    Args:
        thread_id: Thread ID
        token: JWT authentication token
        title: New title (optional)
        increment_message: Increment message counter

    Returns:
        True if successful, False otherwise
    """
    async with httpx.AsyncClient() as client:
        data = {}
        if title:
            data["title"] = title

        # Note: increment_message is handled by service layer
        # when we call the endpoint (auto-increments on update)

        response = await client.patch(
            f"{settings.auth_service_url}/chat_sessions/{thread_id}",
            json=data if data else {},
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )

        return response.status_code == 200


async def delete_chat_session(
    thread_id: str,
    token: str,
    hard_delete: bool = False,
) -> bool:
    """Delete (archive) chat session.

    Args:
        thread_id: Thread ID
        token: JWT authentication token
        hard_delete: If True, permanently delete; otherwise archive

    Returns:
        True if successful, False otherwise
    """
    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{settings.auth_service_url}/chat_sessions/{thread_id}",
            params={"hard_delete": hard_delete},
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )

        return response.status_code == 200
