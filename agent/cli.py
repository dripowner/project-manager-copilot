"""CLI interface for PM Copilot Agent."""

import asyncio
import logging
from typing import Optional

import typer
from langchain_core.messages import HumanMessage
from rich.console import Console
from rich.logging import RichHandler
from rich.markdown import Markdown

from agent.core.checkpointer import create_checkpointer, close_checkpointer
from agent.core.config import AgentSettings
from agent.core.mcp_client import MCPClientWrapper
from agent.core.state import ProjectContext
from agent.graphs.main_graph import create_main_graph
from langgraph.checkpoint.base import BaseCheckpointSaver

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True, show_time=False)],
)
logger = logging.getLogger(__name__)

# Create Typer app
app = typer.Typer(
    name="pm-copilot",
    help="PM Copilot Agent - AI-powered project management assistant",
)
console = Console()


async def run_agent(
    query: str,
    settings: AgentSettings,
    project_key: Optional[str] = None,
    sprint_name: Optional[str] = None,
    checkpointer: Optional[BaseCheckpointSaver] = None,
    thread_id: str = "cli-session",
) -> str:
    """Run the agent with a query.

    Args:
        query: User query to process
        settings: Agent settings
        project_key: Optional Jira project key
        sprint_name: Optional sprint name
        checkpointer: Optional checkpointer for persistent state
        thread_id: Thread ID for conversation persistence

    Returns:
        Agent response text
    """
    # Configure MCP server connection based on transport type
    if settings.mcp_server_transport == "http":
        # HTTP mode: connect to external MCP server (production deployment)
        mcp_server_config = {
            "pm-mcp-server": {
                "url": settings.mcp_server_url,
                "transport": "http",
            }
        }
    else:
        # STDIO mode: launch MCP server as subprocess (local development)
        mcp_server_config = {
            "pm-mcp-server": {
                "command": settings.mcp_server_command,
                "args": settings.mcp_server_args,
                "transport": "stdio",
            }
        }

    # Initialize MCP client and agent
    async with MCPClientWrapper(mcp_server_config) as mcp_client:
        graph = await create_main_graph(mcp_client, settings, checkpointer)

        # Prepare project context
        project_context = ProjectContext(
            project_key=project_key or settings.default_project_key or "UNKNOWN",
            sprint_name=sprint_name or settings.default_sprint_name,
            team_members=[],
        )

        # Prepare initial state
        initial_state = {
            "messages": [HumanMessage(content=query)],
            "project_context": project_context,
            "plan": None,
            "mode": "simple",
            "tool_results": [],
            "remaining_steps": settings.max_iterations,
        }

        # Run agent
        logger.info(f"Executing agent (thread: {thread_id})...")
        result = await graph.ainvoke(
            initial_state, config={"configurable": {"thread_id": thread_id}}
        )

        # Extract final message
        final_message = result["messages"][-1]
        return final_message.content


@app.command()
def chat(
    query: str = typer.Argument(..., help="Query to send to the agent"),
    project_key: Optional[str] = typer.Option(
        None, "--project", "-p", help="Jira project key"
    ),
    sprint: Optional[str] = typer.Option(None, "--sprint", "-s", help="Sprint name"),
) -> None:
    """Execute a single agent query.

    Example:
        pm-copilot chat "List all issues in sprint" --project PROJ --sprint Sprint-1
    """

    async def _chat():
        settings = AgentSettings()
        checkpointer = None
        try:
            # Initialize checkpointer
            checkpointer = await create_checkpointer(settings)

            # Run agent
            result = await run_agent(query, settings, project_key, sprint, checkpointer)
            console.print(Markdown(result))
        finally:
            # Cleanup checkpointer
            await close_checkpointer(checkpointer)

    try:
        asyncio.run(_chat())
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}", style="bold red")
        raise typer.Exit(code=1)


@app.command()
def interactive(
    project_key: Optional[str] = typer.Option(
        None, "--project", "-p", help="Jira project key"
    ),
    sprint: Optional[str] = typer.Option(None, "--sprint", "-s", help="Sprint name"),
) -> None:
    """Start interactive chat session with PM Copilot.

    Example:
        pm-copilot interactive --project PROJ --sprint Sprint-1
    """

    async def _interactive():
        console.print("\n[bold blue]PM Copilot Agent[/bold blue] - Interactive Mode")
        console.print("Type your queries or 'exit'/'quit' to stop.\n")

        settings = AgentSettings()
        checkpointer = None

        try:
            # Initialize checkpointer once for the session
            checkpointer = await create_checkpointer(settings)

            # Display project context
            if project_key or settings.default_project_key:
                console.print(
                    f"[dim]Project: {project_key or settings.default_project_key}[/dim]"
                )
            if sprint or settings.default_sprint_name:
                console.print(
                    f"[dim]Sprint: {sprint or settings.default_sprint_name}[/dim]"
                )
            console.print()

            # Interactive loop
            while True:
                try:
                    query = console.input("[bold blue]You>[/bold blue] ")

                    if query.strip().lower() in ["exit", "quit", "q"]:
                        console.print("[dim]Goodbye![/dim]")
                        break

                    if not query.strip():
                        continue

                    # Run agent (reuses same checkpointer for conversation persistence)
                    result = await run_agent(
                        query, settings, project_key, sprint, checkpointer
                    )

                    # Display response
                    console.print("\n[bold green]Agent>[/bold green]")
                    console.print(Markdown(result))
                    console.print()

                except KeyboardInterrupt:
                    console.print("\n[dim]Interrupted. Type 'exit' to quit.[/dim]")
                    continue
                except Exception as e:
                    console.print(f"\n[red]Error:[/red] {e}\n", style="bold red")
                    logger.exception("Error processing query")
                    continue

        finally:
            # Cleanup checkpointer
            await close_checkpointer(checkpointer)

    try:
        asyncio.run(_interactive())
    except Exception as e:
        console.print(f"[red]Failed to initialize agent:[/red] {e}", style="bold red")
        raise typer.Exit(code=1)


@app.command()
def version() -> None:
    """Show PM Copilot version."""
    from agent import __version__

    console.print(f"PM Copilot Agent v{__version__}")


if __name__ == "__main__":
    app()
