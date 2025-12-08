# Migrations container - runs Alembic migrations and exits
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies (only migrations group)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --group migrations --no-install-project --no-dev

# Copy migrations and config
COPY migrations/ ./migrations/
COPY alembic.ini ./

# Set environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Run migrations
CMD ["alembic", "upgrade", "head"]
