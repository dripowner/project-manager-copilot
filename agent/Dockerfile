# Multi-stage Dockerfile for PM Copilot Agent
# Context: project root
# Build: docker build -f agent/Dockerfile -t pm-agent .

# ============================================================================
# Stage 1: Build - Install dependencies
# ============================================================================
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

WORKDIR /app

# Set uv environment variables for optimal caching
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies with cache mount (без --no-dev для установки всех групп)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --group agent --group mcp-server

# ============================================================================
# Stage 2: Production - Minimal runtime image
# ============================================================================
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

WORKDIR /app

# Copy installed dependencies from builder
COPY --from=builder /app/.venv /app/.venv

# Copy pyproject.toml for package metadata
COPY pyproject.toml ./

# Copy only agent source code (no tests)
COPY agent/ ./agent/

# Set production environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONOPTIMIZE=2 \
    PATH="/app/.venv/bin:$PATH"

# Run as non-root user for security
RUN useradd -m -u 1000 agent && \
    chown -R agent:agent /app

USER agent

# Production entry point
CMD ["python", "-m", "agent", "interactive"]
