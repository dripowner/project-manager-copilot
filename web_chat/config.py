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

    @computed_field
    @property
    def a2a_agent_url(self) -> str:
        """Construct A2A agent URL from host and port."""
        return f"http://{self.a2a_server_host}:{self.a2a_server_port}"


@lru_cache(maxsize=1)
def get_settings() -> ChainlitSettings:
    """Get cached settings instance."""
    return ChainlitSettings()
