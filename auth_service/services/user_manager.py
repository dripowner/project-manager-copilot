"""User manager for FastAPI Users."""

import logging
from uuid import UUID

from fastapi import Request
from fastapi_users import BaseUserManager, UUIDIDMixin

from auth_service.config import get_settings
from auth_service.models.user import User

settings = get_settings()
logger = logging.getLogger(__name__)


class UserManager(UUIDIDMixin, BaseUserManager[User, UUID]):
    """User manager for handling user operations."""

    reset_password_token_secret = settings.secret_key
    verification_token_secret = settings.secret_key

    async def on_after_register(self, user: User, request: Request | None = None):
        """Called after user registration."""
        logger.info(f"User {user.id} has registered (email: {user.email})")

    async def on_after_forgot_password(
        self, user: User, token: str, request: Request | None = None
    ):
        """Called after forgot password request."""
        logger.info(f"User {user.id} has forgotten their password. Reset token: {token}")

    async def on_after_request_verify(
        self, user: User, token: str, request: Request | None = None
    ):
        """Called after verification request."""
        logger.info(f"Verification requested for user {user.id}. Token: {token}")


async def get_user_manager(user_db=None):
    """Dependency to get user manager instance.

    Args:
        user_db: User database (injected by FastAPI Users)

    Yields:
        UserManager: User manager instance
    """
    yield UserManager(user_db)
