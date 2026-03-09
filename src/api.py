"""FastAPI HTTP Routers and dependency injections."""

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Query

from cache import CacheProvider, get_cache
from github_client import GitHubClient, get_github_client
from models import GistResponse, HealthResponse

logger = logging.getLogger("gist_api")

# Create router for all gist endpoints
router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> Dict[str, str]:
    """Health check endpoint for container orchestration."""
    return {"status": "healthy"}


@router.get("/{username}", response_model=List[GistResponse])
async def get_user_gists(
    username: str,
    page: int = Query(1, ge=1, description="Page number for pagination"),
    per_page: int = Query(30, le=100, description="Items per page (max: 100)"),
    cache: CacheProvider = Depends(get_cache),
    github: GitHubClient = Depends(get_github_client),
) -> List[Dict[str, Any]]:
    """Retrieve public gists for a GitHub user. Utilizes Dependency Injection."""
    cache_key = f"{username}_{page}_{per_page}"

    # 1. Attempt to resolve from cache
    logger.debug(f"Checking cache for key: {cache_key}")
    cached_gists = cache.get(cache_key)
    if cached_gists is not None:
        logger.info(f"Cache hit for user: {username}")
        return cached_gists

    # 2. Fetch from external service if cache miss
    logger.debug(f"Cache miss for {username}. Calling GitHub...")
    gists = await github.fetch_user_gists(username, page, per_page)

    # 3. Store in cache
    cache.set(cache_key, gists)

    return gists
