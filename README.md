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
- PostgreSQL 16+ (для PM Layer)

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

# PostgreSQL (для PM Layer)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=pm_mcp
POSTGRES_USER=pm_mcp
POSTGRES_PASSWORD=your-password

# Google Calendar
GOOGLE_CALENDAR_ID=your-calendar-id
GOOGLE_API_KEY=your-api-key
```

### Получение токенов

- **Atlassian API Token**: [Создать токен](https://id.atlassian.com/manage-profile/security/api-tokens)
- **Google API Key**: [Google Cloud Console](https://console.cloud.google.com/apis/credentials) — включите Calendar API

## Запуск

### Локально

```bash
# Запуск миграций БД
uv run alembic upgrade head

# Запуск сервера
uv run python -m pm_mcp
```

Сервер запустится на `http://localhost:8000/mcp`

### Docker

```bash
# Запуск всего стека (PostgreSQL + миграции + сервер)
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
| `calendar_list_events` | Список событий за период |

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
