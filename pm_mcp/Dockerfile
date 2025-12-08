# Stage 1: Builder
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies (only mcp-server group, no dev)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --group mcp-server --no-install-project --no-dev

# Copy application code
COPY pm_mcp/ ./pm_mcp/

# Install the project itself
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --group mcp-server --no-dev

# Stage 2: Runtime
FROM python:3.11-slim-bookworm AS runtime

# Create non-root user
RUN groupadd --system --gid 999 appuser \
 && useradd --system --gid 999 --uid 999 --create-home appuser

# Copy virtual environment from builder
COPY --from=builder --chown=appuser:appuser /app /app

# Set environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Switch to non-root user
USER appuser
WORKDIR /app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import pm_mcp; print('ok')" || exit 1

# Run MCP server
CMD ["python", "-m", "pm_mcp"]
