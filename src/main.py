"""FastAPI application entry point for GitHub Gists API."""

import uvicorn
from fastapi import FastAPI

from api import router
from config import get_settings, setup_logging

# Initialize logging once for the entire application
setup_logging()


def create_app() -> FastAPI:
    """Application factory for FastAPI."""
    app_instance = FastAPI(
        title="GitHub Gists API",
        description="API to retrieve publicly available GitHub Gists for a user",
        version="1.0.0",
    )

    # Include all routes from api.py
    app_instance.include_router(router)

    return app_instance


app = create_app()


def run_server() -> None:
    """Entry point for running the uvicorn ASGI server."""
    settings = get_settings()
    uvicorn.run("main:app", host="0.0.0.0", port=settings.port, workers=4)


if __name__ == "__main__":
    run_server()
