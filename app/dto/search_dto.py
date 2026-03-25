from typing import Any

from pydantic import BaseModel, Field


class UserSearchRequestDTO(BaseModel):
    query: str = Field(min_length=2, max_length=500)
    user_latitude: float | None = Field(default=None, ge=-90, le=90)
    user_longitude: float | None = Field(default=None, ge=-180, le=180)


class QueryAnalysisDTO(BaseModel):
    intent: str = "search_places"
    city: str | None = None
    category: str | None = None
    preferences: list[str] = Field(default_factory=list)
    result_limit: int = Field(default=10, ge=1, le=20)
    near_me: bool = False


class PlaceDTO(BaseModel):
    name: str
    description: str | None = None
    address: str
    latitude: float
    longitude: float
    rating: float | None = None
    types: list[str] = Field(default_factory=list)
    photo_url: str | None = None
    place_id: str
    google_maps_url: str | None = None


class SearchResponseDTO(BaseModel):
    intent: str
    city: str | None = None
    category: str | None = None
    preferences: list[str] = Field(default_factory=list)
    result_limit: int
    near_me: bool
    results_count: int
    results: list[PlaceDTO]
    message: str | None = None


class ApiErrorResponseDTO(BaseModel):
    error: dict[str, Any]
