"""Main FastAPI application for auth service."""

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_users import FastAPIUsers
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)

from auth_service.config import get_settings
from auth_service.database import create_db_and_tables, get_async_session
from auth_service.dependencies import get_user_db
from auth_service.models.user import User
from auth_service.schemas.user import UserCreate, UserRead, UserUpdate
from auth_service.services import chat_session_service
from auth_service.services.user_manager import get_user_manager

settings = get_settings()
logger = logging.getLogger(__name__)


def get_jwt_strategy() -> JWTStrategy:
    """Get JWT authentication strategy."""
    return JWTStrategy(secret=settings.secret_key, lifetime_seconds=3600)


# Configure authentication backend
bearer_transport = BearerTransport(tokenUrl="auth/login")
auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

# Create FastAPIUsers instance
fastapi_users = FastAPIUsers[User, UUID](
    get_user_manager,
    [auth_backend],
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Creating database tables...")
    await create_db_and_tables()
    logger.info("Auth service started")
    yield
    # Shutdown
    logger.info("Auth service stopped")


# Create FastAPI app
app = FastAPI(
    title="PM Copilot Auth Service",
    description="Authentication and user management for PM Copilot",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on your needs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# Include FastAPI Users routes
app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)


# Custom login endpoint for Chainlit integration
@app.post("/auth/login", tags=["auth"])
async def login(email: str, password: str):
    """Custom login endpoint for Chainlit password_auth_callback.

    Args:
        email: User email
        password: User password

    Returns:
        User data with JWT access token

    Raises:
        HTTPException: If authentication fails
    """
    from auth_service.services.user_manager import get_user_manager

    # Get user by email
    async for user_db in get_user_db():
        async for user_manager in get_user_manager(user_db):
            try:
                # Get user by email
                user = await user_manager.get_by_email(email)

                if user is None:
                    raise HTTPException(status_code=400, detail="Invalid credentials")

                # Verify password
                valid, updated_password_hash = await user_manager.password_helper.verify_and_update(
                    password, user.hashed_password
                )

                if not valid:
                    raise HTTPException(status_code=400, detail="Invalid credentials")

                # Check if user is active
                if not user.is_active:
                    raise HTTPException(status_code=400, detail="User is not active")

                # Generate JWT access token
                strategy = get_jwt_strategy()
                access_token = await strategy.write_token(user)

                # Return user data with access token
                return {
                    "id": str(user.id),
                    "email": user.email,
                    "full_name": user.full_name,
                    "avatar_url": user.avatar_url,
                    "default_project_key": user.default_project_key,
                    "is_active": user.is_active,
                    "is_verified": user.is_verified,
                    "access_token": access_token,  # JWT token for API calls
                }
            except Exception as e:
                logger.error(f"Login error: {e}")
                raise HTTPException(status_code=400, detail="Authentication failed")


# Get current user dependency
current_user = fastapi_users.current_user(active=True)


# ============================================================================
# Chat Session Management
# ============================================================================


class ChatSessionResponse(BaseModel):
    """Response schema for chat session."""

    id: UUID
    user_id: UUID
    thread_id: str
    title: str | None
    is_archived: bool
    message_count: int
    last_message_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class ChatSessionCreate(BaseModel):
    """Schema for creating chat session."""

    title: str | None = None


class ChatSessionUpdate(BaseModel):
    """Schema for updating chat session."""

    title: str | None = None
    is_archived: bool | None = None


@app.get(
    "/users/me/chat_sessions",
    response_model=list[ChatSessionResponse],
    tags=["chat_sessions"],
)
async def list_user_chat_sessions(
    include_archived: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """List current user's chat sessions.

    Args:
        include_archived: Include archived sessions
        limit: Maximum number of results
        offset: Offset for pagination
        user: Current authenticated user
        db: Database session

    Returns:
        List of chat sessions ordered by last activity
    """
    sessions = await chat_session_service.list_chat_sessions(
        db, user.id, include_archived, limit, offset
    )
    return sessions


@app.post(
    "/users/me/chat_sessions",
    response_model=ChatSessionResponse,
    tags=["chat_sessions"],
)
async def create_user_chat_session(
    data: ChatSessionCreate,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Create new chat session.

    Args:
        data: Chat session creation data
        user: Current authenticated user
        db: Database session

    Returns:
        Created chat session
    """
    session = await chat_session_service.create_chat_session(db, user.id, data.title)
    return session


@app.get(
    "/chat_sessions/{thread_id}",
    response_model=ChatSessionResponse,
    tags=["chat_sessions"],
)
async def get_chat_session(
    thread_id: str,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Get chat session by thread_id (with ownership check).

    Args:
        thread_id: Thread ID
        user: Current authenticated user
        db: Database session

    Returns:
        Chat session data

    Raises:
        HTTPException: If session not found or access denied
    """
    session = await chat_session_service.get_chat_session_by_thread_id(db, thread_id)

    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    if session.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return session


@app.patch(
    "/chat_sessions/{thread_id}",
    response_model=ChatSessionResponse,
    tags=["chat_sessions"],
)
async def update_chat_session(
    thread_id: str,
    data: ChatSessionUpdate,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Update chat session (with ownership check).

    Args:
        thread_id: Thread ID
        data: Update data
        user: Current authenticated user
        db: Database session

    Returns:
        Updated chat session

    Raises:
        HTTPException: If session not found or access denied
    """
    session = await chat_session_service.get_chat_session_by_thread_id(db, thread_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Chat session not found")

    updated = await chat_session_service.update_chat_session(
        db, thread_id, data.title, data.is_archived
    )
    return updated


@app.delete("/chat_sessions/{thread_id}", tags=["chat_sessions"])
async def delete_chat_session(
    thread_id: str,
    hard_delete: bool = Query(default=False),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Delete (archive) chat session.

    Args:
        thread_id: Thread ID
        hard_delete: If True, permanently delete; otherwise archive
        user: Current authenticated user
        db: Database session

    Returns:
        Success status

    Raises:
        HTTPException: If session not found or access denied
    """
    session = await chat_session_service.get_chat_session_by_thread_id(db, thread_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Chat session not found")

    success = await chat_session_service.delete_chat_session(db, thread_id, hard_delete)
    return {"success": success}
