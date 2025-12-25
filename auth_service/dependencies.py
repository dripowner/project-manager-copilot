"""FastAPI dependencies for auth service."""

from collections.abc import AsyncGenerator

from fastapi import Depends
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from auth_service.database import get_async_session
from auth_service.models.user import User


async def get_user_db(
    session: AsyncSession = Depends(get_async_session),
) -> AsyncGenerator[SQLAlchemyUserDatabase, None]:
    """Get FastAPI Users database adapter.

    Args:
        session: Database session

    Yields:
        SQLAlchemyUserDatabase: User database adapter
    """
    yield SQLAlchemyUserDatabase(session, User)
