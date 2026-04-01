from fastapi import UploadFile

from app.clients.google_maps_client import GoogleMapsClient
from app.dto.search_dto import AudioSearchResponseDTO, SearchResponseDTO
from app.llm.assistant import GuideAssistant
from app.mappers.place_mapper import map_google_place_to_dto
from app.services.audio_transcription_service import AudioTranscriptionService
from app.services.response_formatter import ResponseFormatterService
from app.llm.analyzer import LLMQueryAnalyzer


class AISearchService:
    def __init__(self) -> None:
        self.analyzer = LLMQueryAnalyzer()
        self.assistant = GuideAssistant()
        self.audio_transcription = AudioTranscriptionService()
        self.google_maps: GoogleMapsClient | None = None
        self.response_formatter = ResponseFormatterService()

    def _get_google_maps(self) -> GoogleMapsClient:
        if self.google_maps is None:
            self.google_maps = GoogleMapsClient()
        return self.google_maps

    async def search(
        self,
        *,
        query: str,
        user_latitude: float | None = None,
        user_longitude: float | None = None,
    ) -> SearchResponseDTO:
        analysis = self.analyzer.analyze(query)
        mapped_places = []

        if analysis.intent == "search_places":
            google_maps = self._get_google_maps()
            has_user_coords = user_latitude is not None and user_longitude is not None

            if has_user_coords and analysis.city is None:
                inferred_city = await google_maps.reverse_geocode_city(user_latitude, user_longitude)
                if inferred_city:
                    analysis.city = inferred_city
                # When the user shared coordinates but did not ask for a specific city,
                # prioritize nearby results around the exact position.
                analysis.near_me = True

            raw_places = await google_maps.search_places(
                raw_query=query,
                category=analysis.category,
                preferences=analysis.preferences,
                city=analysis.city,
                limit=analysis.result_limit,
                near_me=analysis.near_me,
                user_latitude=user_latitude,
                user_longitude=user_longitude,
            )
            mapped_places = [map_google_place_to_dto(place, google_maps) for place in raw_places]

        assistant_reply, suggested_questions = self.assistant.build_response(
            query=query,
            analysis=analysis,
            places=mapped_places,
        )

        return self.response_formatter.build_search_response(
            analysis,
            mapped_places,
            assistant_reply=assistant_reply,
            suggested_questions=suggested_questions,
        )

    async def search_from_audio(
        self,
        *,
        audio: UploadFile,
        user_latitude: float | None = None,
        user_longitude: float | None = None,
        language: str | None = None,
    ) -> AudioSearchResponseDTO:
        try:
            audio_bytes = await audio.read()
            transcribed_query = self.audio_transcription.transcribe(
                audio_bytes=audio_bytes,
                filename=audio.filename or "question.webm",
                language=language,
            )
        finally:
            await audio.close()

        search_response = await self.search(
            query=transcribed_query,
            user_latitude=user_latitude,
            user_longitude=user_longitude,
        )

        return AudioSearchResponseDTO(
            **search_response.model_dump(),
            transcribed_query=transcribed_query,
            audio_filename=audio.filename,
        )
