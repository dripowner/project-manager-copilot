"""PM Copilot Chainlit Web Interface.

Provides a web-based chat interface for PM Copilot Agent using Chainlit.
Uses A2A protocol (a2a-sdk Python client) for communication with agent-a2a.
"""

from .config import get_settings

__all__ = ["get_settings"]
