"""Configuration management using pydantic-settings."""

from functools import lru_cache
from typing import Any

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

    # Google Calendar - Service Account
    google_service_account_email: str = Field(
        default="", description="Service account email for Calendar API"
    )
    google_service_account_key_json: str = Field(
        default="",
        description="Service account JSON key (full JSON structure as string)",
    )
    calendar_owner_email: str = Field(
        default="",
        description="User email to share created calendars with (optional)",
    )

    # Server settings
    server_host: str = Field(default="0.0.0.0", description="Server host")
    server_port: int = Field(default=8000, description="Server port")

    # Logging and Observability

    # Production (container deployment) variables
    phoenix_project_name: str = Field(
        default="",
        description="Phoenix project identifier (used as service.name in telemetry)",
    )
    otel_endpoint: str = Field(
        default="", description="OTEL Telemetry collector endpoint (production)"
    )
    enable_phoenix: bool = Field(
        default=False, description="Enable Phoenix telemetry (default: False)"
    )
    enable_monitoring: bool = Field(
        default=False,
        description="Enable Prometheus metrics collection (default: False)",
    )

    # Local development fallback variables
    log_level: str = Field(
        default="INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )
    otel_exporter_otlp_endpoint: str = Field(
        default="",
        description="OpenTelemetry OTLP exporter endpoint (local dev fallback)",
    )
    otel_service_name: str = Field(
        default="pm-mcp-server",
        description="Service name for telemetry (local dev fallback)",
    )

    @property
    def google_service_account_credentials(self) -> dict[str, Any]:
        """Parse service account JSON credentials."""
        import json

        if not self.google_service_account_key_json:
            return {}
        return json.loads(self.google_service_account_key_json)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
