"""Configuration for Auth Service."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthSettings(BaseSettings):
    """Auth service configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server settings
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8003, description="Server port")
    reload: bool = Field(default=False, description="Enable auto-reload in development")

    # Database
    database_url: str = Field(
        description="PostgreSQL connection string (asyncpg format)"
    )

    # Security
    secret_key: str = Field(
        description="Secret key for JWT signing and encryption"
    )

    # OAuth (optional)
    google_oauth_client_id: str = Field(default="", description="Google OAuth Client ID")
    google_oauth_client_secret: str = Field(
        default="", description="Google OAuth Client Secret"
    )
    github_oauth_client_id: str = Field(default="", description="GitHub OAuth Client ID")
    github_oauth_client_secret: str = Field(
        default="", description="GitHub OAuth Client Secret"
    )


@lru_cache(maxsize=1)
def get_settings() -> AuthSettings:
    """Get cached settings instance."""
    return AuthSettings()
