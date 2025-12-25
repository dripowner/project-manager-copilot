"""OAuth account model for third-party authentication."""

from datetime import datetime
from uuid import UUID

from fastapi_users.db import SQLAlchemyBaseOAuthAccountTableUUID
from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from auth_service.database import Base


class OAuthAccount(SQLAlchemyBaseOAuthAccountTableUUID, Base):
    """OAuth account model for storing OAuth provider data.

    Inherits from SQLAlchemyBaseOAuthAccountTableUUID which provides:
    - id: UUID (primary key)
    - user_id: UUID (foreign key to users.id)
    - oauth_name: str (provider name: 'google', 'github')
    - access_token: str
    - expires_at: int | None
    - refresh_token: str | None
    - account_id: str (provider's user ID)
    - account_email: str
    """

    __tablename__ = "oauth_accounts"

    # Timestamp for tracking when account was linked
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
