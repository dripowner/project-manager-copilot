# Auth Service Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev --group auth

# Copy source code
COPY auth_service/ ./auth_service/
COPY migrations/ ./migrations/

# Run migrations and start server
CMD ["uv", "run", "python", "-m", "auth_service"]
