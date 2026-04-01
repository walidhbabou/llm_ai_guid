from fastapi import UploadFile

from app.dto.search_dto import AudioSearchResponseDTO, SearchResponseDTO, UserSearchRequestDTO
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

    async def search_audio(
        self,
        *,
        audio: UploadFile,
        user_latitude: float | None = None,
        user_longitude: float | None = None,
        language: str | None = None,
    ) -> AudioSearchResponseDTO:
        return await self.service.search_from_audio(
            audio=audio,
            user_latitude=user_latitude,
            user_longitude=user_longitude,
            language=language,
        )
