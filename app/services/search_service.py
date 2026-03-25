from app.clients.google_maps_client import GoogleMapsClient
from app.dto.search_dto import SearchResponseDTO
from app.mappers.place_mapper import map_google_place_to_dto
from app.services.response_formatter import ResponseFormatterService
from app.llm.analyzer import LLMQueryAnalyzer


class AISearchService:
    def __init__(self) -> None:
        self.analyzer = LLMQueryAnalyzer()
        self.google_maps = GoogleMapsClient()
        self.response_formatter = ResponseFormatterService()

    async def search(
        self,
        *,
        query: str,
        user_latitude: float | None = None,
        user_longitude: float | None = None,
    ) -> SearchResponseDTO:
        analysis = self.analyzer.analyze(query)
        has_user_coords = user_latitude is not None and user_longitude is not None
        inferred_city: str | None = None

        if has_user_coords and analysis.city is None:
            inferred_city = await self.google_maps.reverse_geocode_city(user_latitude, user_longitude)
            if inferred_city:
                analysis.city = inferred_city
            # When the user shared coordinates but did not ask for a specific city,
            # prioritize nearby results around the exact position.
            analysis.near_me = True

        raw_places = await self.google_maps.search_places(
            raw_query=query,
            category=analysis.category,
            city=analysis.city,
            limit=analysis.result_limit,
            near_me=analysis.near_me,
            user_latitude=user_latitude,
            user_longitude=user_longitude,
        )

        mapped_places = [map_google_place_to_dto(p, self.google_maps) for p in raw_places]

        return self.response_formatter.build_search_response(analysis, mapped_places)
