"""Prompt for conversation classification (chat vs PM work)."""

CONVERSATION_CLASSIFICATION_PROMPT = """Classify the user's request based on conversation history.

CATEGORIES:

1. "chat" - Simple conversational queries that DON'T require PM tools:
   - Greetings: "привет", "hello", "как дела", "hi", "hey"
   - General questions: "что ты умеешь", "кто ты", "help", "расскажи о себе"
   - Small talk: "спасибо", "thanks", "ok", "понятно", "хорошо"
   - Standalone acknowledgments with NO previous context: "ок", "нет", "согласен"

2. "pm_work" - Requests requiring PM tools (Jira, Confluence, Calendar):
   - Jira operations: "создай issue", "покажи backlog", "обнови задачу"
   - Confluence: "найди в Confluence", "покажи документацию"
   - Calendar: "какие встречи сегодня", "создай событие", "проверь календарь"
   - Reports: "сгенерируй отчет", "статус проекта"
   - PM operations: "свяжи встречу с задачей", "action items"
   - Confirmations of PM tasks: "да проверь", "да создай", "да покажи"

IMPORTANT: Consider the conversation history! If the assistant asked to confirm a PM task,
and the user says "да", "yes", "проверь", etc., classify it as "pm_work".

CONVERSATION HISTORY:
{history}

CURRENT USER MESSAGE: {message}

Return ONLY ONE WORD: "chat" OR "pm_work"
"""
