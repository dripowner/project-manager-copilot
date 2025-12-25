"""Pydantic schemas for user data."""

from uuid import UUID

from fastapi_users import schemas


class UserRead(schemas.BaseUser[UUID]):
    """Schema for reading user data (public-facing).

    Inherits from BaseUser which provides:
    - id: UUID
    - email: str
    - is_active: bool
    - is_superuser: bool
    - is_verified: bool
    """

    full_name: str | None = None
    avatar_url: str | None = None
    default_project_key: str | None = None


class UserCreate(schemas.BaseUserCreate):
    """Schema for creating a new user.

    Inherits from BaseUserCreate which provides:
    - email: EmailStr
    - password: str
    - is_active: bool (optional, default True)
    - is_superuser: bool (optional, default False)
    - is_verified: bool (optional, default False)
    """

    full_name: str | None = None
    avatar_url: str | None = None
    default_project_key: str | None = None


class UserUpdate(schemas.BaseUserUpdate):
    """Schema for updating user data.

    Inherits from BaseUserUpdate which provides:
    - email: EmailStr | None
    - password: str | None
    - is_active: bool | None
    - is_superuser: bool | None
    - is_verified: bool | None
    """

    full_name: str | None = None
    avatar_url: str | None = None
    default_project_key: str | None = None
