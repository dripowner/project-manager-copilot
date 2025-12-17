"""Agent-facing messages for A2A server.

All messages in Russian as per project requirements.
"""


class AgentMessages:
    """Messages for agent execution flow."""

    # Routing
    ROUTING_CONVERSATION = "Маршрутизация разговора..."
    DETECTING_PROJECT = "Определение контекста проекта..."
    ANALYZING_TASK = "Анализ типа задачи..."
    VALIDATING_TOOLS = "Валидация необходимых инструментов..."

    # Execution
    EXECUTING_TOOLS = "Выполнение инструментов..."
    PLANNING_EXECUTION = "Планирование и выполнение..."
    GENERATING_RESPONSE = "Генерация ответа..."

    # Project
    REQUESTING_PROJECT_INFO = "Запрос информации о проекте..."

    # Status
    TASK_COMPLETE = "Задача успешно выполнена"
    TASK_FAILED = "Ошибка выполнения задачи: {error}"
    PROCESSING_REQUEST = "Обработка запроса..."


class ToolDisplayNames:
    """User-friendly tool names with emoji for status updates."""

    # Jira
    JIRA_LIST_ISSUES = "📋 Получение задач Jira"
    JIRA_CREATE_ISSUES = "✨ Создание задач Jira"
    JIRA_GET_ISSUE = "🔍 Получение информации о задаче Jira"
    JIRA_UPDATE_ISSUE = "✏️ Обновление задачи Jira"
    JIRA_ADD_COMMENT = "💬 Добавление комментария в Jira"

    # Calendar
    CALENDAR_LIST_MEETINGS = "📅 Получение встреч из календаря"
    CALENDAR_CREATE_MEETING = "📅 Создание встречи в календаре"
    CALENDAR_LIST_EVENTS = "📅 Получение событий календаря"
    CALENDAR_FIND_CALENDAR = "📅 Поиск календаря проекта"

    # PM Layer
    PM_LINK_MEETING_ISSUES = "🔗 Связывание встречи с задачами"
    PM_GET_MEETING_ISSUES = "🔗 Получение задач встречи"
    PM_GET_PROJECT_SNAPSHOT = "📊 Получение снимка проекта"

    # Confluence
    CONFLUENCE_SEARCH = "🔎 Поиск в Confluence"
    CONFLUENCE_READ = "📖 Чтение страницы Confluence"


class NodeMessages:
    """Messages for LangGraph nodes."""

    CONVERSATION_ROUTER = "🔍 Маршрутизация разговора..."
    PROJECT_DETECTOR = "📋 Определение контекста проекта..."
    TASK_ROUTER = "🎯 Анализ типа задачи..."
    TOOL_VALIDATOR = "✅ Валидация необходимых инструментов..."
    SIMPLE_EXECUTOR = "⚡ Выполнение инструментов..."
    PLAN_EXECUTOR = "📝 Планирование и выполнение..."
    ASK_PROJECT_KEY = "❓ Запрос информации о проекте..."
    SIMPLE_CHAT_RESPONSE = "💬 Генерация ответа..."
