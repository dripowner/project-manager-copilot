"""Entry point for auth service."""

import uvicorn

from auth_service.config import get_settings

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "auth_service.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
    )
