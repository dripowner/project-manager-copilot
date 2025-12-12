# PM MCP Server

MCP-сервер для интеграции инструментов проектного управления. Предоставляет единый интерфейс для работы с Jira, Confluence, Google Calendar и собственным PM-слоем для связывания встреч с задачами.

## Возможности

- **Jira**: создание, просмотр, обновление задач, добавление комментариев
- **Confluence**: поиск страниц, чтение содержимого
- **Google Calendar**: просмотр событий и встреч
- **PM Layer**: связывание встреч с задачами Jira, отслеживание action items

## Требования

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) — менеджер пакетов

## Установка

```bash
# Клонирование репозитория
git clone <repository-url>
cd cloudru-mcp

# Установка зависимостей
uv sync --all-groups

# Копирование конфигурации
cp .env.example .env
```

## Конфигурация

Заполните `.env` файл:

```env
# Atlassian (Jira & Confluence)
ATLASSIAN_API_TOKEN=your-api-token
ATLASSIAN_EMAIL=your-email@example.com
JIRA_BASE_URL=https://your-domain.atlassian.net
CONFLUENCE_BASE_URL=https://your-domain.atlassian.net/wiki

# Google Calendar (Service Account)
GOOGLE_SERVICE_ACCOUNT_EMAIL=your-sa@project.iam.gserviceaccount.com
GOOGLE_SERVICE_ACCOUNT_KEY_JSON='{"type":"service_account","project_id":"...","private_key":"...","client_email":"..."}'
```

### Получение токенов

- **Atlassian API Token**: [Создать токен](https://id.atlassian.com/manage-profile/security/api-tokens)
- **Google Service Account**:
  1. Перейдите в [Google Cloud Console](https://console.cloud.google.com)
  2. Создайте проект или выберите существующий
  3. Включите Google Calendar API
  4. Создайте Service Account с доступом к Calendar
  5. Сгенерируйте и скачайте JSON ключ
  6. Скопируйте содержимое JSON файла в переменную `GOOGLE_SERVICE_ACCOUNT_KEY_JSON`

### Мультикалендарная архитектура

Система автоматически создает отдельный календарь для каждого проекта Jira:

- **Именование календарей**: имя календаря = project_key (например, "ALPHA", "BETA")
- **Автосоздание**: календари создаются при первом обращении
- **Изоляция данных**: события разных проектов хранятся в отдельных календарях
- **Метаданные**: связка с проектом сохраняется в описании календаря

## Запуск

### Локально

```bash
# Запуск сервера
uv run python -m pm_mcp
```

Сервер запустится на `http://localhost:8000/mcp`

### Docker

```bash
# Запуск всего стека (mcp-server + agent-a2a)
docker compose up -d

# Просмотр логов
docker compose logs -f mcp-server
```

## PM Copilot A2A Agent

PM Copilot доступен через [A2A (Agent-to-Agent)](https://github.com/a2aproject/a2a-python) протокол для интеграции с другими AI агентами.

### Запуск A2A сервера

```bash
# Локально (требуется запущенный MCP сервер)
uv run python -m agent

# Или через Docker (запускает весь стек)
docker compose up -d agent-a2a
```

Сервер запустится на `http://localhost:8001`

### A2A Endpoints

- `POST /rpc` — JSON-RPC endpoint для A2A протокола
- `GET /.well-known/agent-card.json` — Agent Card для discovery
- `GET /health` — Health check

### Agent Capabilities

PM Copilot предоставляет следующие capabilities:

1. **Sprint Planning** — планирование спринтов и управление бэклогом
2. **Status Reporting** — генерация статус-репортов по проекту
3. **Meeting Coordination** — управление встречами и action items
4. **Issue Lifecycle** — полный lifecycle управления задачами Jira
5. **Team Coordination** — координация команды и workload
6. **Knowledge Search** — поиск информации в Confluence

### Пример использования Agent Card

```bash
# Получить Agent Card
curl http://localhost:8001/.well-known/agent-card.json

# Ожидаемый ответ:
{
  "name": "PM Copilot Agent",
  "description": "AI-powered assistant for project managers...",
  "url": "http://localhost:8001",
  "capabilities": {
    "streaming": true,
    "pushNotifications": false
  },
  "skills": [...]
}
```

## Подключение к Claude Desktop

Добавьте в `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "pm-mcp": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

## Доступные инструменты

### Jira

| Инструмент | Описание |
|------------|----------|
| `jira_list_issues` | Поиск задач по проекту с фильтрами (статус, исполнитель, метки) |
| `jira_create_issues_batch` | Создание нескольких задач из action items |
| `jira_update_issue` | Обновление задачи (статус, исполнитель, срок) |
| `jira_add_comment` | Добавление комментария к задаче |

### Confluence

| Инструмент | Описание |
|------------|----------|
| `confluence_search_pages` | Поиск страниц по тексту или CQL |
| `confluence_get_page_content` | Получение содержимого страницы |

### Google Calendar

| Инструмент | Описание |
|------------|----------|
| `calendar_list_events` | Список событий за период (по project_key или calendar_id) |
| `calendar_list_calendars` | Список всех доступных календарей с метаданными |
| `calendar_find_project_calendar` | Найти или создать календарь для проекта |

### PM Layer

| Инструмент | Описание |
|------------|----------|
| `pm_link_meeting_issues` | Связывание встречи с задачами Jira |
| `pm_get_meeting_issues` | Получение задач, связанных со встречей |
| `pm_get_project_snapshot` | Обзор состояния проекта |

## Разработка

```bash
# Запуск тестов
uv run pytest

# Линтинг
uv run ruff check pm_mcp/
uv run ruff format pm_mcp/
```
