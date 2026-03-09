"""Pydantic models for API responses."""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    """Schema for the health check response."""

    status: str = Field(..., description="Current status of the service")

    model_config = ConfigDict(json_schema_extra={"example": {"status": "healthy"}})


class GistResponse(BaseModel):
    """Simplified schema representing a single GitHub Gist."""

    id: str = Field(description="Unique identifier of the gist")
    url: str = Field(description="URL to view the gist on GitHub")
    description: Optional[str] = Field(description="Description of the gist")
    created_at: str = Field(description="ISO 8601 timestamp of creation")
    files_count: int = Field(description="Number of files contained in the gist")
