"""Prompt for project key detection from conversation history."""

PROJECT_DETECTION_PROMPT = """Analyze the conversation history and extract the Jira project key if mentioned.

Look for project keys in these patterns:
1. Explicit mentions: "работаем с проектом ALPHA", "project BETA", "в проекте GAMMA"
2. Implicit context: "issue ALPHA-123" → project_key=ALPHA, "задача BETA-456" → project_key=BETA
3. Context from previous messages: if user mentioned project earlier, use that

Project key format:
- Usually 3-6 uppercase letters
- Examples: ALPHA, BETA, GAMMA, PROJ, DEV, TEST

Priority rules:
- Recent mentions have higher priority than old ones
- Explicit mentions override implicit ones
- If multiple projects mentioned, use the most recent

Conversation history:
{conversation_history}

Return ONLY the project key (e.g., "ALPHA") or "UNKNOWN" if you cannot determine it with confidence.
"""
