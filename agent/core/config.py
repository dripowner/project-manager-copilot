"""Configuration settings for PM Copilot Agent."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    """Settings for PM Copilot Agent.

    Configuration is loaded from environment variables and .env file.
    """

    # LLM Settings (uses same vars as MCP server)
    openai_base_url: str | None = Field(
        default=None,
        description="OpenAI API base URL (optional, for custom endpoints)",
    )
    openai_api_key: str = Field(
        description="OpenAI API key for LLM access",
    )
    openai_base_model: str = Field(
        default="gpt-4o-mini",
        description="OpenAI model to use for agent reasoning",
    )
    max_iterations: int = Field(
        default=10,
        description="Maximum number of agent iterations",
        ge=1,
        le=50,
    )

    # MCP Server Configuration
    mcp_server_transport: str = Field(
        default="http",
        description="MCP server transport type (stdio or http). Default 'http' for production.",
    )
    mcp_server_command: str = Field(
        default="python",
        description="Command to start MCP server (for stdio transport only - ignored with http)",
    )
    mcp_server_args: list[str] = Field(
        default_factory=lambda: ["-m", "pm_mcp"],
        description="Arguments for MCP server command (for stdio transport only - ignored with http)",
    )
    mcp_server_url: str = Field(
        default="http://mcp-server:8000/mcp",
        description="MCP server URL (for http transport). Default uses Docker service name 'mcp-server'.",
    )

    # PostgreSQL Configuration (shared with MCP server)
    postgres_host: str = Field(default="localhost", description="PostgreSQL host")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_db: str = Field(default="pm_mcp", description="PostgreSQL database name")
    postgres_user: str = Field(default="pm_mcp", description="PostgreSQL user")
    postgres_password: str = Field(default="", description="PostgreSQL password")

    # Project Context (optional defaults)
    default_project_key: str | None = Field(
        default=None,
        description="Default Jira project key",
    )
    default_sprint_name: str | None = Field(
        default=None,
        description="Default sprint name",
    )

    @property
    def postgres_url(self) -> str:
        """Build PostgreSQL connection URL from components.

        Returns:
            PostgreSQL connection URL

        Raises:
            ValueError: If critical credentials (user or password) are missing
        """
        if not self.postgres_user:
            raise ValueError(
                "postgres_user is required for PostgreSQL connection. "
                "Set POSTGRES_USER environment variable."
            )
        if not self.postgres_password:
            raise ValueError(
                "postgres_password is required for PostgreSQL connection. "
                "Set POSTGRES_PASSWORD environment variable."
            )

        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
