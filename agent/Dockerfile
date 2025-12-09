# Multi-stage Dockerfile for PM Copilot A2A Agent
# Context: project root
# Build: docker build -f agent/Dockerfile -t agent-a2a .

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

# Install dependencies with cache mount
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --group agent

# ============================================================================
# Stage 2: Production - Minimal runtime image
# ============================================================================
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

WORKDIR /app

# Copy installed dependencies from builder
COPY --from=builder /app/.venv /app/.venv

# Copy pyproject.toml for package metadata
COPY pyproject.toml ./

# Copy ONLY agent source (not pm_mcp - agent uses HTTP transport)
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

# A2A server entry point
CMD ["python", "-m", "agent"]
