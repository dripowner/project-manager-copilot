"""CRUD operations for chat sessions."""

import logging
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from auth_service.models.chat_session import ChatSession

logger = logging.getLogger(__name__)

SOFT_LIMIT_CHATS = 100  # Soft limit чатов на пользователя


async def create_chat_session(
    db: AsyncSession,
    user_id: UUID,
    title: str | None = None,
) -> ChatSession:
    """Create new chat session for user.

    Args:
        db: Database session
        user_id: User ID
        title: Optional chat title

    Returns:
        Created ChatSession instance

    Note:
        If user has >= SOFT_LIMIT_CHATS active chats, oldest chat is auto-archived.
    """
    # Check soft limit
    count_query = (
        select(func.count())
        .select_from(ChatSession)
        .where(
            ChatSession.user_id == user_id,
            ChatSession.is_archived == False,  # noqa: E712
        )
    )
    result = await db.execute(count_query)
    active_count = result.scalar()

    if active_count >= SOFT_LIMIT_CHATS:
        # Auto-archive oldest chat
        oldest_query = (
            select(ChatSession)
            .where(
                ChatSession.user_id == user_id,
                ChatSession.is_archived == False,  # noqa: E712
            )
            .order_by(ChatSession.last_message_at.asc().nulls_first())
            .limit(1)
        )

        oldest_result = await db.execute(oldest_query)
        oldest = oldest_result.scalar_one_or_none()
        if oldest:
            oldest.is_archived = True
            logger.info(f"Auto-archived oldest chat {oldest.id} for user {user_id}")

    thread_id = str(uuid4())

    session = ChatSession(
        user_id=user_id,
        thread_id=thread_id,
        title=title or f"Chat - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
        is_archived=False,
        message_count=0,
    )

    db.add(session)
    await db.commit()
    await db.refresh(session)

    logger.info(f"Created chat session {session.id} for user {user_id}")
    return session


async def list_chat_sessions(
    db: AsyncSession,
    user_id: UUID,
    include_archived: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> list[ChatSession]:
    """List user's chat sessions.

    Args:
        db: Database session
        user_id: User ID
        include_archived: Include archived chats
        limit: Maximum number of results
        offset: Offset for pagination

    Returns:
        List of ChatSession instances ordered by last_message_at (desc)
    """
    query = select(ChatSession).where(ChatSession.user_id == user_id)

    if not include_archived:
        query = query.where(ChatSession.is_archived == False)  # noqa: E712

    # Order by last activity (most recent first)
    query = query.order_by(ChatSession.last_message_at.desc().nulls_last())
    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_chat_session_by_thread_id(
    db: AsyncSession,
    thread_id: str,
) -> ChatSession | None:
    """Get chat session by thread_id.

    Args:
        db: Database session
        thread_id: Thread ID (context_id from A2A)

    Returns:
        ChatSession instance or None if not found
    """
    query = select(ChatSession).where(ChatSession.thread_id == thread_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def update_chat_session(
    db: AsyncSession,
    thread_id: str,
    title: str | None = None,
    is_archived: bool | None = None,
    increment_message_count: bool = False,
) -> ChatSession | None:
    """Update chat session.

    Args:
        db: Database session
        thread_id: Thread ID
        title: New title (optional)
        is_archived: Archive status (optional)
        increment_message_count: Increment message counter

    Returns:
        Updated ChatSession or None if not found
    """
    session = await get_chat_session_by_thread_id(db, thread_id)
    if not session:
        return None

    if title is not None:
        session.title = title
    if is_archived is not None:
        session.is_archived = is_archived
    if increment_message_count:
        session.message_count += 1

    # Always update last_message_at
    session.last_message_at = datetime.utcnow()

    await db.commit()
    await db.refresh(session)

    return session


async def delete_chat_session(
    db: AsyncSession,
    thread_id: str,
    hard_delete: bool = False,
) -> bool:
    """Delete (archive) chat session.

    Args:
        db: Database session
        thread_id: Thread ID
        hard_delete: If True, permanently delete; if False, archive

    Returns:
        True if session was deleted/archived, False if not found
    """
    session = await get_chat_session_by_thread_id(db, thread_id)
    if not session:
        return False

    if hard_delete:
        await db.delete(session)
    else:
        session.is_archived = True

    await db.commit()
    return True
