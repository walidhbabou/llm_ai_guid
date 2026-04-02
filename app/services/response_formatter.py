from app.dto.search_dto import GuideCardDTO, PlaceDTO, QueryAnalysisDTO, SearchResponseDTO


class ResponseFormatterService:
    @staticmethod
    def build_search_response(
        analysis: QueryAnalysisDTO,
        places: list[PlaceDTO],
        assistant_reply: str | None = None,
        suggested_questions: list[str] | None = None,
        guide_cards: list[GuideCardDTO] | None = None,
    ) -> SearchResponseDTO:
        guide_cards = guide_cards or []
        response_mode = "places"
        message = None
        if guide_cards or (analysis.intent == "other" and assistant_reply):
            response_mode = "guide"
            if not places:
                message = "Reponse guide generee pour cette demande."
        elif analysis.intent == "search_places" and not places:
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
            response_mode=response_mode,
            assistant_reply=assistant_reply,
            suggested_questions=suggested_questions or [],
            guide_cards=guide_cards,
            message=message,
        )
