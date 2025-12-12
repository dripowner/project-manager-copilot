"""Prompt templates for PM Copilot Agent."""

from agent.prompts.conversation_classification import CONVERSATION_CLASSIFICATION_PROMPT
from agent.prompts.project_detection import PROJECT_DETECTION_PROMPT
from agent.prompts.task_classification import TASK_CLASSIFICATION_PROMPT
from agent.prompts.tool_prediction import TOOL_PREDICTION_PROMPT

__all__ = [
    "CONVERSATION_CLASSIFICATION_PROMPT",
    "PROJECT_DETECTION_PROMPT",
    "TASK_CLASSIFICATION_PROMPT",
    "TOOL_PREDICTION_PROMPT",
]
