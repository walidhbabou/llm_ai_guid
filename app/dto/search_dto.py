from typing import Any, Literal

from pydantic import BaseModel, Field


class UserSearchRequestDTO(BaseModel):
    query: str = Field(min_length=2, max_length=500)
    user_latitude: float | None = Field(default=None, ge=-90, le=90)
    user_longitude: float | None = Field(default=None, ge=-180, le=180)


class QueryAnalysisDTO(BaseModel):
    intent: str = "search_places"
    detected_language: str = "fr"
    city: str | None = None
    category: str | None = None
    preferences: list[str] = Field(default_factory=list)
    result_limit: int = Field(default=10, ge=1, le=20)
    near_me: bool = False
    # Trip planning extras (used when intent is itinerary-like)
    budget_level: Literal["petit", "moyen", "eleve"] | None = None
    time_slot: Literal["matin", "journee", "soir"] | None = None
    vibe: list[
        Literal[
            "culture",
            "nature",
            "food",
            "chill",
            "historique",
            "famille",
            "romantique",
            "shopping",
            "photo_spots",
        ]
    ] = Field(default_factory=list)
    duration_minutes: int | None = Field(default=None, ge=30, le=24 * 60)


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
    duration_minutes: int | None = Field(default=None, ge=1, le=480)


class GuideCardDTO(BaseModel):
    title: str
    description: str
    query: str | None = None
    time_slot: str | None = None
    duration_minutes: int | None = Field(default=None, ge=5, le=480)
    budget_min_mad: int | None = Field(default=None, ge=0, le=10000)
    budget_max_mad: int | None = Field(default=None, ge=0, le=10000)


class ItineraryPlaceDTO(BaseModel):
    """
    Minimal place payload for itinerary steps.
    Keeps the response light and mobile-friendly.
    """

    name: str
    description: str = Field(min_length=10, max_length=240)
    address: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    place_id: str | None = None
    google_maps_url: str | None = None


class ItineraryStepDTO(BaseModel):
    order: int = Field(ge=1, le=50)
    time_slot: Literal["matin", "journee", "soir"] | None = None
    title: str = Field(min_length=3, max_length=80)
    place: ItineraryPlaceDTO
    estimated_duration_minutes: int = Field(ge=10, le=8 * 60)
    transport_hint: str | None = Field(
        default=None, min_length=3, max_length=120, description="Walk/taxi/tram/etc."
    )
    why_go: str = Field(
        min_length=10,
        max_length=220,
        description="1 short, attractive reason for the user.",
    )
    budget_hint_mad: int | None = Field(default=None, ge=0, le=10000)
    user_tips: list[str] = Field(default_factory=list, max_length=6)


class UrbanTripPlanDTO(BaseModel):
    city: str = Field(min_length=2, max_length=80)
    detected_intent: Literal["matin", "journee", "soir"] = "journee"
    budget_level: Literal["petit", "moyen", "eleve"] = "moyen"
    preferences: list[str] = Field(default_factory=list, max_length=10)
    total_estimated_minutes: int = Field(ge=30, le=24 * 60)
    itinerary: list[ItineraryStepDTO] = Field(min_length=2, max_length=12)
    personalized_suggestions: list[str] = Field(default_factory=list, max_length=8)
    safety_notes: list[str] = Field(default_factory=list, max_length=6)
    fallback_options: list[str] = Field(
        default_factory=list,
        max_length=6,
        description="Alternatives if a place is closed / weather changes.",
    )


class SearchResponseDTO(BaseModel):
    intent: str
    detected_language: str = "fr"
    city: str | None = None
    category: str | None = None
    preferences: list[str] = Field(default_factory=list)
    result_limit: int
    near_me: bool
    results_count: int
    results: list[PlaceDTO]
    response_mode: Literal["places", "itinerary"] = "places"
    assistant_reply: str | None = None
    suggested_questions: list[str] = Field(default_factory=list)
    guide_cards: list[GuideCardDTO] = Field(default_factory=list)
    trip_plan: UrbanTripPlanDTO | None = None
    message: str | None = None


class AudioSearchResponseDTO(SearchResponseDTO):
    input_mode: str = "audio"
    transcribed_query: str
    audio_filename: str | None = None


class ApiErrorResponseDTO(BaseModel):
    error: dict[str, Any]
