import json
import re
import unicodedata
from typing import Any

from groq import Groq

from app.core.config import settings
from app.dto.search_dto import PlaceDTO, QueryAnalysisDTO
from app.llm.system_prompt import GUIDE_RESPONSE_SYSTEM_PROMPT

_OUT_OF_SCOPE_PATTERNS = (
    r"\bcalcule\b",
    r"\bcode\b",
    r"\bprogramme\b",
    r"\btraduis\b",
    r"\btraduire\b",
)
_FAQ_REPLIES = (
    (r"\bcapitale\b.*\bmaroc\b", "La capitale du Maroc est Rabat."),
    (r"\bmonnaie\b.*\bmaroc\b", "La monnaie du Maroc est le dirham marocain (MAD)."),
    (
        r"\blangue\b.*\bmaroc\b",
        "Au Maroc, l'arabe et l'amazigh sont les langues officielles, et le francais est tres utilise.",
    ),
    (
        r"\bmeilleure saison\b.*\bmaroc\b",
        "Le printemps et l'automne sont souvent les saisons les plus agreables pour visiter le Maroc.",
    ),
)


class GuideAssistant:
    def __init__(self) -> None:
        self._client = Groq(api_key=settings.groq_api_key) if settings.groq_api_key else None

    def build_response(
        self,
        *,
        query: str,
        analysis: QueryAnalysisDTO,
        places: list[PlaceDTO],
    ) -> tuple[str | None, list[str]]:
        if analysis.intent == "search_places":
            model_response = self._build_model_response_for_places(query, analysis, places)
            if model_response is not None:
                return model_response

            return (
                self._build_search_fallback_reply(analysis, places),
                self._build_fallback_suggested_questions(analysis),
            )

        model_response = self._build_model_response_for_question(query, analysis)
        if model_response is not None:
            return model_response

        faq_reply = self._build_faq_reply(query)
        if faq_reply:
            return faq_reply, self._build_fallback_suggested_questions(analysis)

        reply = self._build_domain_fallback_reply(analysis.detected_language)
        return reply, self._build_fallback_suggested_questions(analysis)

    def _build_model_response_for_places(
        self,
        query: str,
        analysis: QueryAnalysisDTO,
        places: list[PlaceDTO],
    ) -> tuple[str | None, list[str]] | None:
        payload = {
            "mode": "search_results",
            "user_query": query,
            "detected_language": analysis.detected_language,
            "analysis": analysis.model_dump(),
            "places": [
                {
                    "name": place.name,
                    "description": place.description,
                    "address": place.address,
                    "rating": place.rating,
                }
                for place in places[:5]
            ],
        }
        return self._complete_response(payload, analysis)

    def _build_model_response_for_question(
        self,
        query: str,
        analysis: QueryAnalysisDTO,
    ) -> tuple[str | None, list[str]] | None:
        payload = {
            "mode": "general_question",
            "user_query": query,
            "detected_language": analysis.detected_language,
        }
        return self._complete_response(payload, analysis)

    def _complete_response(
        self,
        payload: dict[str, Any],
        analysis: QueryAnalysisDTO,
    ) -> tuple[str | None, list[str]] | None:
        if self._client is None:
            return None

        try:
            completion = self._client.chat.completions.create(
                model=settings.groq_model,
                temperature=0.2,
                max_completion_tokens=260,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": GUIDE_RESPONSE_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            "Utilise uniquement les informations suivantes pour produire la reponse.\n"
                            f"{json.dumps(payload, ensure_ascii=False)}"
                        ),
                    },
                ],
            )
        except Exception:
            return None

        raw_content = completion.choices[0].message.content or "{}"
        data = self._safe_json_parse(raw_content)
        if not data:
            return None

        assistant_reply = data.get("assistant_reply")
        if not isinstance(assistant_reply, str):
            return None

        cleaned_reply = assistant_reply.strip()
        if not cleaned_reply:
            return None

        suggested_questions = self._clean_suggested_questions(
            data.get("suggested_questions"),
            analysis,
        )
        return cleaned_reply, suggested_questions

    def _safe_json_parse(self, raw_text: str) -> dict[str, Any] | None:
        try:
            parsed = json.loads(raw_text)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            pass

        match = re.search(r"\{[\s\S]*\}", raw_text)
        if not match:
            return None

        try:
            parsed = json.loads(match.group(0))
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None

    def _build_search_fallback_reply(
        self,
        analysis: QueryAnalysisDTO,
        places: list[PlaceDTO],
    ) -> str:
        language = analysis.detected_language
        category_label = self._humanize_category(analysis.category, language)
        city_segment = f" a {analysis.city}" if analysis.city else ""

        if language == "en":
            if not places:
                return (
                    f"I could not find {category_label}{city_segment} for this request. "
                    "Try a simpler area, category, or filter."
                )
            top_places = ", ".join(self._format_place(place) for place in places[:3])
            return f"I found {len(places)} {category_label}{city_segment}. Top options: {top_places}."

        if language == "darija":
            if not places:
                return (
                    f"Ma lqitch {category_label}{city_segment} li kaynssbo had talab. "
                    "Jarrab b mdina, zona, wla criteria ashal."
                )
            top_places = ", ".join(self._format_place(place) for place in places[:3])
            return f"Lqit {len(places)} {category_label}{city_segment}. Aham ikhtiyarat: {top_places}."

        if not places:
            if analysis.preferences:
                prefs = ", ".join(analysis.preferences)
                return (
                    f"Je n'ai pas trouve de {category_label}{city_segment} qui correspondent bien a {prefs}. "
                    "Essaie avec une ville, un quartier ou des criteres plus simples."
                )
            return (
                f"Je n'ai pas trouve de {category_label}{city_segment} pour cette demande. "
                "Essaie avec une categorie plus precise, une ville ou une recherche proche de toi."
            )

        top_places = ", ".join(self._format_place(place) for place in places[:3])
        prefs_segment = ""
        if analysis.preferences:
            prefs_segment = f" qui semblent correspondre a {', '.join(analysis.preferences)}"

        reply = f"J'ai trouve {len(places)} {category_label}{city_segment}{prefs_segment}. "
        reply += f"Les premiers choix sont {top_places}."
        if len(places) > 3:
            reply += " Je peux aussi affiner par budget, ambiance ou zone."
        return reply

    def _build_faq_reply(self, query: str) -> str | None:
        lowered_query = self._normalize_text(query)

        if any(re.search(pattern, lowered_query) for pattern in _OUT_OF_SCOPE_PATTERNS):
            return None

        for pattern, reply in _FAQ_REPLIES:
            if re.search(pattern, lowered_query):
                return reply
        return None

    def _build_domain_fallback_reply(self, language: str) -> str:
        if language == "en":
            return (
                "I mainly help with places to visit, where to eat, where to stay, and practical travel questions. "
                "Ask me in that direction and I will guide you."
            )
        if language == "darija":
            return (
                "Ana kan3awn b lmawadin dial fin tmchi, fin takol, fin tbat, "
                "w as2ila basita dial guide touristique. Sowlni b had lmanhaj w n3awnk."
            )
        return (
            "Je peux surtout aider a trouver des lieux, proposer des sorties et repondre a des "
            "questions simples de guide touristique. Reformule ta demande dans ce cadre et je t'aiderai."
        )

    def _clean_suggested_questions(
        self,
        raw_questions: Any,
        analysis: QueryAnalysisDTO,
    ) -> list[str]:
        if not isinstance(raw_questions, list):
            return self._build_fallback_suggested_questions(analysis)

        cleaned_questions: list[str] = []
        for item in raw_questions:
            if not isinstance(item, str):
                continue
            question = item.strip()
            if question:
                cleaned_questions.append(question)

        cleaned_questions = list(dict.fromkeys(cleaned_questions))[:3]
        if len(cleaned_questions) >= 2:
            return cleaned_questions
        return self._build_fallback_suggested_questions(analysis)

    def _build_fallback_suggested_questions(self, analysis: QueryAnalysisDTO) -> list[str]:
        language = analysis.detected_language

        if language == "en":
            if analysis.intent == "search_places":
                return [
                    "Show me the closest ones",
                    "Filter by rating",
                    "Give me a cheaper option",
                ]
            return [
                "What can I visit there?",
                "Find a good restaurant near me",
                "Show me a well-rated hotel",
            ]

        if language == "darija":
            if analysis.intent == "search_places":
                return [
                    "Werri lia li qrab",
                    "Sefi ghir li note dyalhom mzyana",
                    "Bghit option rkhisa",
                ]
            return [
                "Ash n9dar nzor tmma?",
                "Qelleb lia 3la restaurant qrib",
                "Werri lia hotel mzyan",
            ]

        if analysis.intent == "search_places":
            return [
                "Montre-moi les plus proches",
                "Filtre par note",
                "Propose-moi une option moins chere",
            ]
        return [
            "Que puis-je visiter la-bas ?",
            "Trouve-moi un restaurant proche de moi",
            "Montre-moi un hotel bien note",
        ]

    def _format_place(self, place: PlaceDTO) -> str:
        if place.rating is not None:
            return f"{place.name} ({place.rating}/5)"
        return place.name

    def _humanize_category(self, category: str | None, language: str) -> str:
        if language == "en":
            labels = {
                "cafe": "cafes",
                "hotel": "hotels",
                "monument": "monuments",
                "mosquee": "mosques",
                "musee": "museums",
                "parc": "parks",
                "plage": "beaches",
                "restaurant": "restaurants",
            }
        elif language == "darija":
            labels = {
                "cafe": "cafiyat",
                "hotel": "hotilat",
                "monument": "ma3alim",
                "mosquee": "jawami3",
                "musee": "mat7af",
                "parc": "7daye9",
                "plage": "plajat",
                "restaurant": "mat3amat",
            }
        else:
            labels = {
                "cafe": "cafes",
                "hotel": "hotels",
                "monument": "monuments",
                "mosquee": "mosquees",
                "musee": "musees",
                "parc": "parcs",
                "plage": "plages",
                "restaurant": "restaurants",
            }

        if category is None:
            return "lieux" if language != "en" else "places"
        return labels.get(category, category)

    def _normalize_text(self, value: str) -> str:
        ascii_value = unicodedata.normalize("NFKD", value)
        ascii_value = "".join(ch for ch in ascii_value if not unicodedata.combining(ch))
        ascii_value = ascii_value.lower()
        ascii_value = re.sub(r"[’']", " ", ascii_value)
        ascii_value = re.sub(r"[^a-z0-9\s-]", " ", ascii_value)
        ascii_value = re.sub(r"\s+", " ", ascii_value).strip()
        return ascii_value
