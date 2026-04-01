from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile

from app.controllers.search_controller import SearchController
from app.dto.search_dto import AudioSearchResponseDTO, SearchResponseDTO, UserSearchRequestDTO

router = APIRouter(prefix="/api/ai", tags=["ai-search"])
controller = SearchController()


@router.post("/search", response_model=SearchResponseDTO)
async def search_places(payload: UserSearchRequestDTO) -> SearchResponseDTO:
    return await controller.search(payload)


@router.post("/search/audio", response_model=AudioSearchResponseDTO)
async def search_places_from_audio(
    audio: Annotated[UploadFile, File(...)],
    user_latitude: Annotated[float | None, Form(ge=-90, le=90)] = None,
    user_longitude: Annotated[float | None, Form(ge=-180, le=180)] = None,
    language: Annotated[str | None, Form()] = None,
) -> AudioSearchResponseDTO:
    return await controller.search_audio(
        audio=audio,
        user_latitude=user_latitude,
        user_longitude=user_longitude,
        language=language,
    )
