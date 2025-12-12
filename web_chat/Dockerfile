# Multi-stage Dockerfile for PM Copilot Chainlit Web Interface
# Context: project root
# Build: docker build -f web_chat/Dockerfile -t web-chat .

# ============================================================================
# Stage 1: Build - Install dependencies
# ============================================================================
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

WORKDIR /app

# Set uv environment variables for optimal caching
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies: web-chat group (includes chainlit, a2a-sdk, etc)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --group web-chat

# ============================================================================
# Stage 2: Production - Minimal runtime image
# ============================================================================
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

WORKDIR /app

# Copy installed dependencies from builder
COPY --from=builder /app/.venv /app/.venv

# Copy pyproject.toml for package metadata
COPY pyproject.toml ./

# Copy web_chat application code
COPY web_chat/ ./web_chat/

# Set production environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PATH="/app/.venv/bin:$PATH"

# Run as non-root user for security
RUN useradd -m -u 1000 webuser && \
    chown -R webuser:webuser /app

USER webuser

# Chainlit server entry point
CMD ["chainlit", "run", "web_chat/app.py", "--host", "0.0.0.0", "--port", "8002"]
