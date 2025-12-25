# PM MCP Server

MCP-сервер для интеграции инструментов проектного управления. Предоставляет единый интерфейс для работы с Jira, Confluence, Google Calendar и собственным PM-слоем для связывания встреч с задачами.

## Возможности

- **Jira**: создание, просмотр, обновление задач, добавление комментариев
- **Confluence**: поиск страниц, чтение содержимого
- **Google Calendar**: просмотр событий и встреч (multi-calendar архитектура)
- **PM Layer**: связывание встреч с задачами Jira, отслеживание action items
- **A2A Agent**: PM Copilot агент с поддержкой Agent-to-Agent протокола
- **Web Chat**: Веб-интерфейс с многопользовательской авторизацией (Chainlit)
- **Multi-User Auth**: Email/пароль + OAuth (Google, GitHub) через FastAPI Users
- **Observability**: OpenTelemetry трассировка и Prometheus метрики

## Требования

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) — менеджер пакетов
- Docker и Docker Compose (опционально, для контейнерного запуска)

## Быстрый старт

### Локальная разработка

```bash
# 1. Клонирование репозитория
git clone <repository-url>
cd cloudru-mcp

# 2. Установка зависимостей
uv sync --all-groups

# 3. Копирование конфигурации
cp .env.example.local .env

# 4. ⚠️ ВАЖНО: Установите обязательные секреты!
# Сгенерируйте пароли и секреты (см. раздел "4. Авторизация"):
openssl rand -base64 32  # POSTGRES_PASSWORD
openssl rand -base64 48  # AUTH_SECRET_KEY
openssl rand -base64 48  # CHAINLIT_AUTH_SECRET

# 5. Заполните .env файл (см. раздел "Конфигурация")

# 6. Запуск MCP сервера
uv run python -m pm_mcp

# 7. (Опционально) Запуск A2A агента в другом терминале
uv run python -m agent
```

### Docker Compose (рекомендуется)

```bash
# 1. Клонирование репозитория
git clone <repository-url>
cd cloudru-mcp

# 2. Копирование конфигурации
cp .env.example.local .env

# 3. ⚠️ ВАЖНО: Установите обязательные секреты!
# Сгенерируйте пароли и секреты (см. раздел "4. Авторизация"):
openssl rand -base64 32  # POSTGRES_PASSWORD
openssl rand -base64 48  # AUTH_SECRET_KEY
openssl rand -base64 48  # CHAINLIT_AUTH_SECRET

# 4. Заполните .env файл (см. раздел "Конфигурация")

# 5. Запуск PostgreSQL и auth-service
docker compose up -d postgres auth-service

# 6. Применение миграций базы данных
docker compose exec auth-service uv run alembic upgrade head

# 7. Запуск всего стека
docker compose up -d

# 8. Просмотр логов
docker compose logs -f

# 9. Откройте web chat в браузере
# http://localhost:8002
```

## Конфигурация

### Структура конфигурации

Проект использует единый `.env` файл в корне с переменными для всех компонентов:

- **MCP Server** — переменные с префиксами `ATLASSIAN_`, `GOOGLE_`, `SERVER_`
- **A2A Agent** — переменные с префиксами `OPENAI_`, `A2A_`, `MCP_SERVER_`
- **Observability** — переменные с префиксами `LOG_`, `OTEL_`, `PHOENIX_`

Альтернативно можно использовать отдельные `.env` файлы:

- `pm_mcp/.env` — только для MCP сервера
- `agent/.env` — только для A2A агента

### 1. Atlassian (Jira & Confluence) — Обязательно

**Шаг 1:** Создайте API токен Atlassian

1. Перейдите на страницу [API Tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Войдите в свой аккаунт Atlassian
3. Нажмите **Create API token**
4. Укажите название токена (например, "PM MCP Server")
5. Скопируйте созданный токен (будет показан только один раз)

**Шаг 2:** Заполните переменные в `.env`:

```env
# Email вашего Atlassian аккаунта
ATLASSIAN_EMAIL=your-email@company.com

# API токен из шага 1
ATLASSIAN_API_TOKEN=ATATT3xFfGF0abc123def456...

# URL вашего Jira workspace
JIRA_BASE_URL=https://yourcompany.atlassian.net

# URL вашего Confluence workspace
CONFLUENCE_BASE_URL=https://yourcompany.atlassian.net/wiki
```

### 2. Google Calendar (Service Account) — Обязательно

**Шаг 1:** Создайте проект в Google Cloud Console

1. Откройте [Google Cloud Console](https://console.cloud.google.com)
2. Нажмите на выпадающий список проектов и выберите **New Project**
3. Введите название проекта (например, "PM MCP Calendar")
4. Нажмите **Create**

**Шаг 2:** Включите Google Calendar API

1. В меню навигации выберите **APIs & Services** → **Library**
2. Найдите **Google Calendar API**
3. Нажмите **Enable**

**Шаг 3:** Создайте Service Account

1. В меню навигации выберите **APIs & Services** → **Credentials**
2. Нажмите **Create Credentials** → **Service account**
3. Заполните форму:
   - **Service account name**: `pm-mcp-calendar-bot`
   - **Service account ID**: автоматически заполнится
   - **Description**: "Service account for PM MCP calendar access"
4. Нажмите **Create and Continue**
5. Пропустите роли (нажмите **Continue**, затем **Done**)

**Шаг 4:** Создайте и скачайте ключ

1. Найдите созданный Service Account в списке
2. Нажмите на него, перейдите на вкладку **Keys**
3. Нажмите **Add Key** → **Create new key**
4. Выберите формат **JSON**
5. Нажмите **Create** — файл ключа автоматически скачается

**Шаг 5:** Заполните переменные в `.env`:

Откройте скачанный JSON файл и скопируйте его содержимое:

```env
# Email Service Account (из JSON: client_email)
GOOGLE_SERVICE_ACCOUNT_EMAIL=pm-mcp-calendar-bot@your-project.iam.gserviceaccount.com

# Полное содержимое JSON файла ключа (сохраните как одну строку или многострочный JSON)
GOOGLE_SERVICE_ACCOUNT_KEY_JSON='{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "abc123...",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBA...\n-----END PRIVATE KEY-----\n",
  "client_email": "pm-mcp-calendar-bot@your-project.iam.gserviceaccount.com",
  "client_id": "123456789...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/...",
  "universe_domain": "googleapis.com"
}'

# (Опционально) Email для шаринга созданных календарей
CALENDAR_OWNER_EMAIL=your-email@gmail.com
```

**Примечание:** Service Account автоматически создает календари для каждого Jira проекта. Чтобы видеть эти календари в своем Google Calendar, укажите `CALENDAR_OWNER_EMAIL`.

### 3. OpenAI API (для A2A агента) — Обязательно для агента

#### Вариант A: OpenAI Official API

1. Перейдите на [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Войдите в аккаунт OpenAI
3. Нажмите **Create new secret key**
4. Скопируйте ключ (показывается один раз)

```env
OPENAI_API_KEY=sk-proj-abc123...
OPENAI_BASE_MODEL=gpt-4o-mini
# OPENAI_BASE_URL не нужен для официального API
```

#### Вариант B: Cloud.ru Foundation Models

Используйте API ключ из платформы Cloud.ru:

```env
OPENAI_API_KEY=your-cloud-ru-api-key
OPENAI_BASE_URL=https://foundation-models.api.cloud.ru/v1
OPENAI_BASE_MODEL=openai/gpt-oss-120b
```

#### Вариант C: Другие OpenAI-совместимые API

```env
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://your-llm-provider.com/v1
OPENAI_BASE_MODEL=model-name
```

### 4. Авторизация (для веб-интерфейса)

⚠️ **ВАЖНО: Требования безопасности**

Следующие переменные являются **ОБЯЗАТЕЛЬНЫМИ** и должны быть установлены перед запуском:

- `POSTGRES_PASSWORD` — минимум 16 символов
- `AUTH_SECRET_KEY` — минимум 32 символа
- `CHAINLIT_AUTH_SECRET` — минимум 32 символа

Docker Compose **не запустится** без этих переменных (выдаст ошибку).

**Генерация безопасных секретов:**

```bash
# PostgreSQL пароль (минимум 16 символов)
openssl rand -base64 32

# AUTH_SECRET_KEY и CHAINLIT_AUTH_SECRET (минимум 32 символа)
openssl rand -base64 48
```

**Настройка в `.env`:**

```env
# PostgreSQL (для хранения пользователей)
POSTGRES_USER=pm_user
# ОБЯЗАТЕЛЬНО: Замените на сгенерированный пароль!
POSTGRES_PASSWORD=YOUR_GENERATED_PASSWORD_HERE

# Auth Service
# Автоматически использует POSTGRES_PASSWORD из выше
DATABASE_URL=postgresql+asyncpg://pm_user:${POSTGRES_PASSWORD}@postgres:5432/pm_copilot

# ОБЯЗАТЕЛЬНО: Замените на сгенерированный секрет (мин. 32 символа)!
AUTH_SECRET_KEY=YOUR_GENERATED_SECRET_KEY_HERE

# ОБЯЗАТЕЛЬНО: Замените на сгенерированный секрет (мин. 32 символа)!
CHAINLIT_AUTH_SECRET=YOUR_GENERATED_CHAINLIT_SECRET_HERE

# OAuth (опционально - оставьте пустыми для использования только email/пароль)
# Google: https://console.cloud.google.com/apis/credentials
# GitHub: https://github.com/settings/developers
GOOGLE_OAUTH_CLIENT_ID=
GOOGLE_OAUTH_CLIENT_SECRET=
GITHUB_OAUTH_CLIENT_ID=
GITHUB_OAUTH_CLIENT_SECRET=
```

**Примечание:** Авторизация требуется только для доступа к веб-интерфейсу (web_chat). A2A агент остается открытым для интеграций.

### 5. MCP Server и A2A Agent

```env
# MCP Server настройки
SERVER_HOST=0.0.0.0
SERVER_PORT=8000

# A2A Agent настройки
MCP_SERVER_URL=http://localhost:8000/mcp
A2A_SERVER_HOST=0.0.0.0
A2A_SERVER_PORT=8001
A2A_SERVER_BASE_URL=http://localhost:8001

# Параметры агента
MAX_ITERATIONS=10
DEFAULT_PROJECT_KEY=PROJ
DEFAULT_SPRINT_NAME=Sprint 1
```

### 6. Observability (опционально)

```env
# Логирование
LOG_LEVEL=INFO

# OpenTelemetry (оставьте пустым для консольного вывода)
OTEL_EXPORTER_OTLP_ENDPOINT=
OTEL_SERVICE_NAME=pm-mcp-server

# Отключить телеметрию и метрики (по умолчанию отключены)
# ENABLE_PHOENIX=false
# ENABLE_MONITORING=false
```

### Мультикалендарная архитектура

Система автоматически создает отдельный календарь для каждого проекта Jira:

- **Именование календарей**: имя календаря = project_key (например, "ALPHA", "BETA")
- **Автосоздание**: календари создаются при первом обращении
- **Изоляция данных**: события разных проектов хранятся в отдельных календарях
- **Метаданные**: связка с проектом сохраняется в описании календаря

### Первичная настройка базы данных

При первом запуске необходимо применить миграции:

```bash
# Локально
uv run alembic upgrade head

# Или через Docker
docker compose exec auth-service uv run alembic upgrade head
```

Для создания первого пользователя используйте web_chat интерфейс (регистрация доступна без авторизации).

## Запуск

### Вариант 1: Локальный запуск (для разработки)

**Только MCP Server:**

```bash
# Запуск MCP сервера
uv run python -m pm_mcp
```

Сервер запустится на `http://localhost:8000/mcp`

**MCP Server + A2A Agent (два терминала):**

```bash
# Терминал 1: MCP Server
uv run python -m pm_mcp

# Терминал 2: A2A Agent
uv run python -m agent
```

- MCP Server: `http://localhost:8000/mcp`
- A2A Agent: `http://localhost:8001`
- Agent Card: `http://localhost:8001/.well-known/agent-card.json`

### Вариант 2: Docker Compose (для production)

**Запуск всего стека:**

```bash
# Сборка и запуск контейнеров
docker compose up -d

# Просмотр логов всех сервисов
docker compose logs -f

# Просмотр логов конкретного сервиса
docker compose logs -f mcp-server
docker compose logs -f agent-a2a
```

**Перезапуск после изменений в коде:**

```bash
# Пересборка и перезапуск MCP сервера
docker compose up -d --build mcp-server

# Пересборка и перезапуск A2A агента
docker compose up -d --build agent-a2a
```

**Остановка:**

```bash
# Остановить все сервисы
docker compose down

# Остановить с удалением volumes
docker compose down -v
```

### Вариант 3: Отдельные Docker контейнеры

**MCP Server:**

```bash
# Сборка
docker build -t pm-mcp-server -f Dockerfile .

# Запуск
docker run -d \
  --name pm-mcp-server \
  -p 8000:8000 \
  --env-file .env \
  pm-mcp-server
```

**A2A Agent:**

```bash
# Сборка
docker build -t pm-copilot-agent -f agent/Dockerfile .

# Запуск
docker run -d \
  --name pm-copilot-agent \
  -p 8001:8001 \
  --env-file .env \
  --link pm-mcp-server \
  pm-copilot-agent
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

## PM Copilot Web Chat

Веб-интерфейс для взаимодействия с PM Copilot агентом через браузер с поддержкой многопользовательской авторизации.

### Запуск Web Chat

```bash
# Локально (требуется запущенный A2A агент и auth-service)
uv run chainlit run web_chat/app.py --host 0.0.0.0 --port 8002

# Или через Docker (запускает весь стек)
docker compose up -d web-chat
```

Интерфейс будет доступен по адресу `http://localhost:8002`

### Функции авторизации

**Dual Authentication:**

- **Email/Пароль**: Регистрация и вход через форму
- **OAuth**: Вход через Google или GitHub (требуется настройка OAuth credentials)

**Первый запуск:**

1. Откройте `http://localhost:8002`
2. Нажмите "Sign Up" для создания учетной записи
3. Заполните email и пароль
4. После регистрации войдите в систему

**User Profile:**

- `full_name` - отображается в интерфейсе
- `avatar_url` - аватар пользователя
- `default_project_key` - проект по умолчанию для быстрого доступа

### Настройка OAuth (опционально)

Для включения входа через Google/GitHub:

1. **Google OAuth:**
   - Создайте OAuth App в [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
   - Добавьте Authorized redirect URI: `http://localhost:8002/auth/oauth/google/callback`
   - Скопируйте Client ID и Client Secret в `.env`

2. **GitHub OAuth:**
   - Создайте OAuth App в [GitHub Settings](https://github.com/settings/developers)
   - Добавьте Authorization callback URL: `http://localhost:8002/auth/oauth/github/callback`
   - Скопируйте Client ID и Client Secret в `.env`

3. **Создайте `.chainlit/config.toml`** (опционально, для кастомизации):

```toml
[auth]
enable_password_auth = true

[auth.oauth_google]
client_id = "${GOOGLE_OAUTH_CLIENT_ID}"
client_secret = "${GOOGLE_OAUTH_CLIENT_SECRET}"

[auth.oauth_github]
client_id = "${GITHUB_OAUTH_CLIENT_ID}"
client_secret = "${GITHUB_OAUTH_CLIENT_SECRET}"
```

### Важно: Безопасность

- **Агент остается открытым**: A2A agent (`http://localhost:8001`) доступен без авторизации для интеграций
- **Web chat защищен**: Доступ к веб-интерфейсу только для авторизованных пользователей
- **User context**: Информация о пользователе передается в агент для аудита (но НЕ для проверки доступа)

## Подключение клиентов

### Claude Desktop (MCP Client)

Добавьте в `claude_desktop_config.json` (обычно находится в `%APPDATA%\Claude\` на Windows или `~/Library/Application Support/Claude/` на macOS):

```json
{
  "mcpServers": {
    "pm-mcp": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

После изменения конфигурации перезапустите Claude Desktop.

### A2A Agent Integration

Для интеграции с другими AI агентами используйте Agent Card:

```bash
# Получить Agent Card
curl http://localhost:8001/.well-known/agent-card.json

# Использовать A2A RPC endpoint
curl -X POST http://localhost:8001/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "task.create",
    "params": {
      "skill": "sprint_planning",
      "input": "Спланируй спринт для проекта ALPHA"
    },
    "id": 1
  }'
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

### Установка dev зависимостей

```bash
# Установить все зависимости включая dev группу
uv sync --all-groups
```

### Тестирование

```bash
# Запуск всех тестов
uv run pytest

# Запуск тестов с coverage
uv run pytest --cov=pm_mcp --cov-report=html

# Запуск конкретного теста
uv run pytest pm_mcp/tests/test_jira_tools.py::test_jira_list_issues_success -v

# Запуск тестов агента
uv run pytest agent/tests/
```

### Линтинг и форматирование

```bash
# Проверка кода
uv run ruff check pm_mcp/
uv run ruff check agent/

# Автоформатирование
uv run ruff format pm_mcp/
uv run ruff format agent/

# Исправление автоматически исправимых ошибок
uv run ruff check --fix pm_mcp/
```

### Добавление новых инструментов

Подробнее см. [CLAUDE.md](CLAUDE.md) в разделе "Adding New Tools".

1. Создайте модели в `pm_mcp/tools/<domain>/models.py`
2. Реализуйте сервис в `pm_mcp/services/<domain>_service.py`
3. Зарегистрируйте инструменты в `pm_mcp/tools/<domain>/tools.py`
4. Добавьте mock сервис в `pm_mcp/tests/mocks/mock_services.py`
5. Напишите тесты в `pm_mcp/tests/test_<domain>_tools.py`

## Полезные ссылки

- [MCP Protocol Documentation](https://modelcontextprotocol.io/)
- [A2A Protocol Specification](https://github.com/a2aproject/a2a-spec)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Atlassian API Documentation](https://developer.atlassian.com/cloud/)
- [Google Calendar API Documentation](https://developers.google.com/calendar/api/guides/overview)

## Лицензия

MIT License

## Поддержка

Для вопросов и багов создавайте [issues](../../issues) в репозитории.
