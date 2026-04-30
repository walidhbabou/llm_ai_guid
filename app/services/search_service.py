from fastapi import UploadFile

from app.clients.google_maps_client import GoogleMapsClient
from fastapi import HTTPException
from app.core.exceptions import GoogleMapsError
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
            try:
                self.google_maps = GoogleMapsClient()
            except GoogleMapsError as exc:
                # Surface a clear HTTP error for missing/invalid Maps configuration in production
                raise HTTPException(status_code=500, detail=str(exc)) from exc
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

            raw_places: list[dict] = []

            # For itinerary-like queries, avoid sending the whole sentence to Google.
            if self._looks_like_itinerary_query(query):
                if not has_user_coords and not analysis.city:
                    raw_places = []
                else:
                    raw_places = await self._search_itinerary_places(
                        google_maps=google_maps,
                        analysis=analysis,
                        user_latitude=user_latitude,
                        user_longitude=user_longitude,
                    )
            else:
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

            if not raw_places and self._looks_like_itinerary_query(query):
                fallback_query = self._build_itinerary_fallback_query(analysis)
                raw_places = await google_maps.search_places(
                    raw_query=fallback_query,
                    category=analysis.category,
                    preferences=analysis.preferences,
                    city=analysis.city,
                    limit=analysis.result_limit,
                    near_me=analysis.near_me,
                    user_latitude=user_latitude,
                    user_longitude=user_longitude,
                )
            mapped_places = [
                map_google_place_to_dto(
                    place,
                    google_maps,
                    language=analysis.detected_language,
                )
                for place in raw_places
            ]

        # Attach an estimated duration to each PlaceDTO so the UI can display time per place
        try:
            for p in mapped_places:
                # use assistant's estimator to keep durations consistent with guide cards
                try:
                    p.duration_minutes = self.assistant._estimate_duration_minutes(p)
                except Exception:
                    p.duration_minutes = None
        except Exception:
            # defensive: if mapping fails, continue without durations
            pass

        assistant_reply, suggested_questions, guide_cards = self.assistant.build_response(
            query=query,
            analysis=analysis,
            places=mapped_places,
        )

        return self.response_formatter.build_search_response(
            analysis,
            mapped_places,
            assistant_reply=assistant_reply,
            suggested_questions=suggested_questions,
            guide_cards=guide_cards,
        )

    async def _search_itinerary_places(
        self,
        *,
        google_maps: GoogleMapsClient,
        analysis,
        user_latitude: float | None,
        user_longitude: float | None,
    ) -> list[dict]:
        # Goal: get a mix of "visit + eat + coffee + sunset" for a day plan.
        # Keep queries short and high-signal for Google.
        queries: list[str] = []

        prefs = set((analysis.preferences or [])[:6])
        if "romantique" in prefs:
            queries.extend(["romantic rooftop", "garden", "sunset viewpoint"])
        if "culture" in prefs or "historique" in prefs:
            queries.extend(["tourist attraction", "museum", "historic site"])
        if "photos" in prefs:
            queries.extend(["photo spot", "viewpoint"])
        if "coucher de soleil" in prefs:
            queries.extend(["sunset viewpoint", "sunset beach"])

        # Default mix
        if not queries:
            queries.extend(["tourist attraction", "restaurant", "cafe", "viewpoint"])
        else:
            queries.extend(["restaurant", "cafe"])

        merged: list[dict] = []
        seen: set[str] = set()

        # Each query returns a few results; merge/dedupe until we reach limit.
        per_query_limit = max(3, min(6, int(analysis.result_limit)))
        for q in queries[:6]:
            results = await google_maps.search_places(
                raw_query=q,
                category=None,
                preferences=None,
                city=analysis.city,
                limit=per_query_limit,
                near_me=analysis.near_me,
                user_latitude=user_latitude,
                user_longitude=user_longitude,
            )
            for place in results:
                place_id = str(place.get("place_id") or "").strip()
                key = place_id or str(place.get("name") or "").strip().lower()
                if not key or key in seen:
                    continue
                seen.add(key)
                merged.append(place)
                if len(merged) >= int(analysis.result_limit):
                    return merged[: int(analysis.result_limit)]

        return merged[: int(analysis.result_limit)]

    def _looks_like_itinerary_query(self, query: str) -> bool:
        normalized = " ".join(query.lower().replace("’", "'").split())
        keywords = (
            "programme",
            "itineraire",
            "itinéraire",
            "aujourd",
            "aujourd'hui",
            "today",
            "day trip",
            "avec ma femme",
            "ma femme",
            "siyaha",
            "sortie",
        )
        return any(k in normalized for k in keywords)

    def _build_itinerary_fallback_query(self, analysis) -> str:
        # Keep it simple for Google TextSearch: short, high-signal keywords.
        prefs = set((analysis.preferences or [])[:4])
        if "romantique" in prefs:
            return "sortie romantique"
        if "culture" in prefs or "historique" in prefs:
            return "lieux touristiques culturels"
        if "photos" in prefs:
            return "spots photo"
        if "coucher de soleil" in prefs:
            return "coucher de soleil point de vue"
        return "lieux touristiques"

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
