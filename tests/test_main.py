"""Real-world integration tests for the GitHub Gists API."""

import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.mark.asyncio
@pytest.mark.parametrize("username", ["octocat", "hemuku90"])
async def test_get_user_gists_success(username):
    """Test successful retrieval of user gists from GitHub API.

    Test CI-CD with ArgoCD
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(f"/{username}")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        gist = data[0]
        assert "id" in gist
        assert "url" in gist
        assert "description" in gist
        assert "created_at" in gist
        assert "files_count" in gist


@pytest.mark.asyncio
async def test_health_endpoint():
    """Test health check endpoint returns healthy status /health"""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
@pytest.mark.parametrize("username", ["octocat", "hemuku90"])
async def test_get_user_gists_pagination(username):
    """Test pagination parameters against real GitHub API."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Get first page with 1 item
        response1 = await client.get(f"/{username}?page=1&per_page=1")
        assert response1.status_code == 200
        data1 = response1.json()

        # Determine if user has multiple gists for complete testing
        if len(data1) == 1:
            # Get second page with 1 item
            response2 = await client.get(f"/{username}?page=2&per_page=1")
            assert response2.status_code == 200
            data2 = response2.json()

            # Ensure pagination actually gives different results if user has > 1 gist
            if len(data2) == 1:
                assert data1[0]["id"] != data2[0]["id"]


@pytest.mark.asyncio
@pytest.mark.parametrize("username", ["octocat", "hemuku90"])
@pytest.mark.parametrize(
    "page,per_page",
    [
        (1, 30),
        (2, 10),
    ],
)
async def test_pagination_parameters_validation(username, page, per_page):
    """Test that valid pagination parameter combinations are accepted."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Use a real user to ensure 200 OK
        response = await client.get(f"/{username}?page={page}&per_page={per_page}")

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_user_gists_user_not_found():
    """Test 404 response for non-existent GitHub user."""
    # Using a handle that is extremely unlikely to exist
    fake_user = "this-user-definitely-does-not-exist-123456789"
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(f"/{fake_user}")

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


@pytest.mark.asyncio
@pytest.mark.parametrize("username", ["octocat", "hemuku90"])
async def test_cache_hit_returns_consistent_data(username):
    """Test that repeated requests return consistent data (via cache)."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # First request to prime cache
        response1 = await client.get(f"/{username}?per_page=1")
        assert response1.status_code == 200

        # Second request should be from cache
        response2 = await client.get(f"/{username}?per_page=1")
        assert response2.status_code == 200

        assert response1.json() == response2.json()


@pytest.mark.asyncio
async def test_invalid_page_parameter():
    """Test that invalid page parameter is handled locally by FastAPI."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/octocat?page=0")

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_per_page_exceeds_maximum():
    """Test that per_page exceeding maximum is rejected locally by FastAPI."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/octocat?per_page=200")

    assert response.status_code == 422
