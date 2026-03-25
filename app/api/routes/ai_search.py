from fastapi import APIRouter

from app.controllers.search_controller import SearchController
from app.dto.search_dto import SearchResponseDTO, UserSearchRequestDTO

router = APIRouter(prefix="/api/ai", tags=["ai-search"])
controller = SearchController()


@router.post("/search", response_model=SearchResponseDTO)
async def search_places(payload: UserSearchRequestDTO) -> SearchResponseDTO:
    return await controller.search(payload)
