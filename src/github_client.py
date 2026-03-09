"""External client for fetching data from GitHub API."""

import logging
from typing import Any, Dict, List, Optional

import httpx
from fastapi import HTTPException

from config import get_settings

logger = logging.getLogger("gist_api")
settings = get_settings()


class GitHubClient:
    """Client for interacting with the GitHub REST API."""

    BASE_URL = "https://api.github.com"

    def __init__(self, token: Optional[str] = None):
        self.headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "FastAPI-Gist-Service",
        }
        if token:
            self.headers["Authorization"] = f"Bearer {token}"

    async def fetch_user_gists(
        self, username: str, page: int, per_page: int
    ) -> List[Dict[str, Any]]:
        """Fetch and transform public gists for a specific user."""
        url = f"{self.BASE_URL}/users/{username}/gists"

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                logger.info(f"Fetching gists for {username} (page: {page})")
                response = await client.get(
                    url,
                    headers=self.headers,
                    params={"page": page, "per_page": per_page},
                )

                if response.status_code == 404:
                    logger.warning(f"User not found: {username}")
                    raise HTTPException(status_code=404, detail="User not found")

                response.raise_for_status()
                gists_data = response.json()

                # Transform response to the simplified format
                return [
                    {
                        "id": gist.get("id"),
                        "url": gist.get("html_url"),
                        "description": gist.get("description"),
                        "created_at": gist.get("created_at"),
                        "files_count": len(gist.get("files", {})),
                    }
                    for gist in gists_data
                ]

            except HTTPException:
                raise
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"GitHub API error: {e.response.status_code} - {e.response.text}"
                )
                raise HTTPException(
                    status_code=e.response.status_code, detail="External API error"
                )
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")


# Singleton instance to be injected
github_client = GitHubClient(token=settings.github_token)


def get_github_client() -> GitHubClient:
    """Dependency injector yielding the GitHub Client."""
    return github_client
