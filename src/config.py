"""Configuration and environment variables for the GitHub Gists API."""

import json
import logging
import os
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings using pydantic-settings for validation."""

    # Optional GitHub token for higher rate limits
    github_token: Optional[str] = os.getenv("GITHUB_TOKEN")

    # Server port
    port: int = int(os.getenv("PORT", "8080"))
    log_level: str = os.getenv("LOG_LEVEL", "DEBUG")
    model_config = SettingsConfigDict(env_file=".env")


@lru_cache
def get_settings() -> Settings:
    """Return application settings, cached to avoid re-reading env file."""
    return Settings()


def setup_logging() -> logging.Logger:
    """Configure JSON logging for production."""
    logger = logging.getLogger("gist_api")
    settings = get_settings()
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter(
                json.dumps(
                    {
                        "timestamp": "%(asctime)s",
                        "level": "%(levelname)s",
                        "message": "%(message)s",
                        "module": "%(module)s",
                    }
                )
            )
        )
        logger.addHandler(handler)
        level = getattr(logging, settings.log_level.upper(), logging.INFO)
        logger.setLevel(level)
        # Inject custom logger in uvicorn
        for uvicorn_logger_name in ("uvicorn.error", "uvicorn.access"):
            uv_logger = logging.getLogger(uvicorn_logger_name)
            uv_logger.handlers = [handler]
            uv_logger.setLevel(level)
            uv_logger.propagate = False
    return logger
