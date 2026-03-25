from app.dto.search_dto import PlaceDTO, QueryAnalysisDTO, SearchResponseDTO


class ResponseFormatterService:
    @staticmethod
    def build_search_response(
        analysis: QueryAnalysisDTO,
        places: list[PlaceDTO],
    ) -> SearchResponseDTO:
        message = None
        if not places:
            message = "Aucun lieu trouve pour cette requete"

        return SearchResponseDTO(
            intent=analysis.intent,
            city=analysis.city,
            category=analysis.category,
            preferences=analysis.preferences,
            result_limit=analysis.result_limit,
            near_me=analysis.near_me,
            results_count=len(places),
            results=places,
            message=message,
        )
