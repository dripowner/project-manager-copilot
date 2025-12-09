"""Configuration management using pydantic-settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Atlassian (Jira & Confluence)
    atlassian_api_token: str = Field(default="", description="Atlassian API token")
    atlassian_email: str = Field(default="", description="Atlassian account email")
    jira_base_url: str = Field(
        default="https://your-domain.atlassian.net",
        description="Jira Cloud base URL",
    )
    confluence_base_url: str = Field(
        default="https://your-domain.atlassian.net/wiki",
        description="Confluence Cloud base URL",
    )

    # PostgreSQL
    postgres_host: str = Field(default="localhost", description="PostgreSQL host")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_db: str = Field(default="pm_mcp", description="PostgreSQL database name")
    postgres_user: str = Field(default="pm_mcp", description="PostgreSQL user")
    postgres_password: str = Field(default="", description="PostgreSQL password")

    # Google Calendar
    google_calendar_id: str = Field(default="", description="Google Calendar ID")
    google_api_key: str = Field(default="", description="Google API key")

    # Server settings
    server_host: str = Field(default="0.0.0.0", description="Server host")
    server_port: int = Field(default=8000, description="Server port")

    # MCP Transport
    mcp_transport: Literal["stdio", "http"] = Field(
        default="http",
        description="MCP transport mode: 'stdio' for CLI/desktop apps, 'http' for network deployment",
    )

    @property
    def database_url(self) -> str:
        """Construct PostgreSQL connection URL."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_async(self) -> str:
        """Construct asyncpg connection URL."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
