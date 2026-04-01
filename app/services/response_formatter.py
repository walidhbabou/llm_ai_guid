from app.dto.search_dto import PlaceDTO, QueryAnalysisDTO, SearchResponseDTO


class ResponseFormatterService:
    @staticmethod
    def build_search_response(
        analysis: QueryAnalysisDTO,
        places: list[PlaceDTO],
        assistant_reply: str | None = None,
        suggested_questions: list[str] | None = None,
    ) -> SearchResponseDTO:
        message = None
        if analysis.intent == "search_places" and not places:
            message = "Aucun lieu trouve pour cette requete"

        return SearchResponseDTO(
            intent=analysis.intent,
            detected_language=analysis.detected_language,
            city=analysis.city,
            category=analysis.category,
            preferences=analysis.preferences,
            result_limit=analysis.result_limit,
            near_me=analysis.near_me,
            results_count=len(places),
            results=places,
            assistant_reply=assistant_reply,
            suggested_questions=suggested_questions or [],
            message=message,
        )
