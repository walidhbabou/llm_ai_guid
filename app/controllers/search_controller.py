from app.dto.search_dto import SearchResponseDTO, UserSearchRequestDTO
from app.services.search_service import AISearchService


class SearchController:
    def __init__(self) -> None:
        self.service = AISearchService()

    async def search(self, payload: UserSearchRequestDTO) -> SearchResponseDTO:
        return await self.service.search(
            query=payload.query,
            user_latitude=payload.user_latitude,
            user_longitude=payload.user_longitude,
        )
