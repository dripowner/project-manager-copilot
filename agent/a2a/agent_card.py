"""Agent Card definition for PM Copilot Agent."""

from a2a.types import AgentCard, AgentCapabilities, AgentSkill

from agent.core.config import AgentSettings


def get_agent_card(settings: AgentSettings) -> AgentCard:
    """Generate Agent Card for PM Copilot.

    Args:
        settings: Agent settings with agent metadata and server URL

    Returns:
        Agent Card object
    """
    return AgentCard(
        name=settings.agent_name,
        description=settings.agent_description,
        url=settings.a2a_server_base_url,
        version=settings.agent_version,
        protocol_version="0.3.0",
        default_input_modes=["text/plain", "application/json"],
        default_output_modes=["text/plain", "application/json"],
        capabilities=AgentCapabilities(
            streaming=True,
            push_notifications=False,
        ),
        skills=[
            AgentSkill(
                id="sprint-planning",
                name="Sprint Planning & Backlog Management",
                description=(
                    "Analyze backlog, prioritize stories, check team capacity, "
                    "prepare sprint plans"
                ),
                tags=["planning", "backlog", "sprint"],
            ),
            AgentSkill(
                id="status-reporting",
                name="Project Status Reporting",
                description=(
                    "Generate comprehensive status reports with "
                    "completed/in-progress/blocked issues"
                ),
                tags=["reporting", "status", "metrics"],
            ),
            AgentSkill(
                id="meeting-coordination",
                name="Meeting & Action Items Management",
                description=(
                    "Link meetings to Jira issues, track action items, "
                    "review retrospective outcomes"
                ),
                tags=["meeting", "coordination", "action-items"],
            ),
            AgentSkill(
                id="issue-lifecycle",
                name="Issue Lifecycle Management",
                description=(
                    "Create, update, search, and track Jira issues "
                    "throughout their lifecycle"
                ),
                tags=["jira", "issues", "tracking"],
            ),
            AgentSkill(
                id="team-coordination",
                name="Team Workload Coordination",
                description=(
                    "Track team capacity, workload distribution, "
                    "and resource allocation"
                ),
                tags=["team", "workload", "capacity"],
            ),
            AgentSkill(
                id="knowledge-search",
                name="Documentation & Knowledge Search",
                description="Search and retrieve information from Confluence knowledge base",
                tags=["confluence", "documentation", "search"],
            ),
        ],
    )
