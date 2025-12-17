"""User-facing messages for MCP server.

All messages in Russian as per project requirements.
"""


class ErrorMessages:
    """Error messages for MCP tools."""

    # Calendar errors
    CALENDAR_NOT_FOUND = "Календарь не найден для проекта: {project_key}"
    CALENDAR_CREATE_FAILED = "Не удалось создать календарь: {error}"
    CALENDAR_METADATA_INVALID = "Неверный формат метаданных календаря"

    # Event errors
    EVENT_NOT_FOUND = "Событие не найдено: {event_id}"
    EVENT_METADATA_TOO_LARGE = (
        "Размер метаданных ({size} байт) превышает безопасный лимит. "
        "Рассмотрите уменьшение количества связанных задач (текущее: {count})"
    )

    # Validation errors
    INVALID_ISSUE_KEY = "Неверный формат ключа задачи: {key}"
    INVALID_DATE_FORMAT = "Неверный формат даты: {date_str}"
    MESSAGE_TOO_LONG = "Сообщение слишком длинное: {size} байт > {max_size} байт"
    MESSAGE_EMPTY = "Сообщение не может быть пустым"

    # Generic
    MISSING_CREDENTIALS = "Учетные данные не настроены: {config_keys}"
    OPERATION_FAILED = "Операция не выполнена"


class SuccessMessages:
    """Success messages for MCP operations."""

    CALENDAR_CREATED = "Календарь создан для проекта: {project_key}"
    CALENDAR_FOUND = "Найден календарь для проекта: {project_key}"
    EVENT_LINKED = "Событие связано с {count} задачами"
    EVENT_CREATED = "Событие создано: {summary}"
    ACCESS_GRANTED = "Доступ предоставлен пользователю {user_email}"


class InfoMessages:
    """Informational messages."""

    CALENDAR_USING_EXISTING = "Используется существующий календарь для проекта: {project_key}"
    METADATA_MIGRATED = "Метаданные календаря обновлены до нового формата"
    PROCESSING_REQUEST = "Обработка запроса..."
