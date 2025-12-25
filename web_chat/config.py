from functools import lru_cache

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ChainlitSettings(BaseSettings):
    """Configuration for Chainlit web chat service."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Chainlit specific
    chainlit_host: str = Field(default="0.0.0.0")
    chainlit_port: int = Field(default=8002)

    # A2A Agent server connection (reuses existing variables from agent config)
    a2a_server_host: str = Field(
        default="agent-a2a", description="A2A Agent server host"
    )
    a2a_server_port: int = Field(default=8001, description="A2A Agent server port")

    # Authentication
    auth_service_url: str = Field(
        default="http://auth-service:8003",
        description="Auth service URL for user authentication",
    )
    chainlit_auth_secret: str = Field(
        ...,  # Required, no default
        description="Secret key for Chainlit session management (REQUIRED - min 32 characters)",
        min_length=32,
    )

    # OAuth credentials (optional - leave empty to disable OAuth)
    google_oauth_client_id: str = Field(default="", description="Google OAuth client ID")
    google_oauth_client_secret: str = Field(
        default="", description="Google OAuth client secret"
    )
    github_oauth_client_id: str = Field(default="", description="GitHub OAuth client ID")
    github_oauth_client_secret: str = Field(
        default="", description="GitHub OAuth client secret"
    )

    @computed_field
    @property
    def a2a_agent_url(self) -> str:
        """Construct A2A agent URL from host and port."""
        return f"http://{self.a2a_server_host}:{self.a2a_server_port}"


@lru_cache(maxsize=1)
def get_settings() -> ChainlitSettings:
    """Get cached settings instance."""
    return ChainlitSettings()
