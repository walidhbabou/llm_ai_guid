import json
import re
from typing import Any

from openai import OpenAI

from app.core.config import settings
from app.core.exceptions import LLMAnalysisError
from app.dto.search_dto import QueryAnalysisDTO
from app.llm.system_prompt import SYSTEM_PROMPT

_ALLOWED_CATEGORIES = {"restaurant", "cafe", "musee", "plage", "monument", "parc", "hotel"}
_LOCATION_STOPWORDS = {
    "et",
    "ou",
    "mais",
    "mes",
    "de",
    "des",
    "du",
    "donne",
    "donner",
    "moi",
    "svp",
    "stp",
}


class LLMQueryAnalyzer:
    def __init__(self) -> None:
        self._client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

    def analyze(self, query: str) -> QueryAnalysisDTO:
        if self._client is None:
            return self._fallback_analysis(query)

        user_prompt = (
            "Analyse la requete suivante et retourne uniquement le JSON demande.\\n"
            f"Requete: {query}"
        )

        try:
            completion = self._client.chat.completions.create(
                model=settings.openai_model,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except Exception as exc:
            # Keep the API usable even when OpenAI credentials are missing/invalid.
            return self._fallback_analysis(query)

        content = completion.choices[0].message.content or "{}"
        data = self._safe_json_parse(content)
        if not data:
            return self._fallback_analysis(query)

        return self._normalize_analysis(data, query)

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

    def _normalize_analysis(self, data: dict[str, Any], original_query: str) -> QueryAnalysisDTO:
        category = data.get("category")
        if isinstance(category, str):
            category = category.strip().lower()
            if category not in _ALLOWED_CATEGORIES:
                category = None
        else:
            category = None

        preferences = data.get("preferences")
        if not isinstance(preferences, list):
            preferences = []
        preferences = [str(item).strip() for item in preferences if str(item).strip()]

        result_limit = data.get("result_limit", 10)
        if not isinstance(result_limit, int):
            result_limit = 10
        result_limit = max(1, min(result_limit, 20))

        city = data.get("city")
        if city is not None:
            city = str(city).strip() or None

        intent = data.get("intent")
        if not isinstance(intent, str) or not intent.strip():
            intent = "search_places"

        near_me = bool(data.get("near_me", False))

        normalized = QueryAnalysisDTO(
            intent=intent,
            city=city,
            category=category,
            preferences=preferences,
            result_limit=result_limit,
            near_me=near_me,
        )

        # Lightweight safety net when model misses obvious cues.
        heuristic = self._fallback_analysis(original_query)
        if normalized.category is None and heuristic.category is not None:
            normalized.category = heuristic.category
        if normalized.city is None and heuristic.city is not None:
            normalized.city = heuristic.city
        if normalized.near_me is False and heuristic.near_me is True:
            normalized.near_me = True

        return normalized

    def _fallback_analysis(self, query: str) -> QueryAnalysisDTO:
        q = query.lower()

        category = None
        category_map = {
            "restaurant": ["restaurant", "resto", "restaurants"],
            "cafe": ["cafe", "cafes", "cafe\u0301"],
            "musee": ["musee", "musees", "mus\u00e9e", "mus\u00e9es"],
            "plage": ["plage", "plages"],
            "monument": ["monument", "monuments"],
            "parc": ["parc", "parcs"],
            "hotel": ["hotel", "hotels", "h\u00f4tel", "h\u00f4tels"],
        }
        for key, terms in category_map.items():
            if any(term in q for term in terms):
                category = key
                break

        city = self._extract_city_candidate(query)

        limit_match = re.search(r"\b(\d{1,2})\b", q)
        result_limit = int(limit_match.group(1)) if limit_match else 10
        result_limit = max(1, min(result_limit, 20))

        near_me_terms = [
            "proche de moi",
            "autour de moi",
            "pres de moi",
            "pr\u00e8s de moi",
            "a cote de moi",
            "\u00e0 cote de moi",
            "a cote",
            "\u00e0 cote",
            "near me",
            "a proximit\u00e9",
            "\u00e0 proximit\u00e9",
            "ma position",
            "ma localisation",
            "autour d'ici",
            "autour dici",
            "je suis a",
            "je suis \u00e0",
            "je suis dans",
        ]
        near_me = any(term in q for term in near_me_terms)

        preferences = []
        for pref in ["meilleur", "meilleurs", "pas cher", "calme", "familial", "romantique", "ouvert"]:
            if pref in q:
                preferences.append(pref)

        return QueryAnalysisDTO(
            intent="search_places",
            city=city,
            category=category,
            preferences=preferences,
            result_limit=result_limit,
            near_me=near_me,
        )

    def _extract_city_candidate(self, query: str) -> str | None:
        location_patterns = [
            r"\bje\s+suis\s+(?:a|\u00e0|au|aux|dans)\s+([A-Za-z\-\u00c0-\u017f']+(?:\s+[A-Za-z\-\u00c0-\u017f']+){0,4})",
            r"\b(?:a|\u00e0|au|aux|de|dans)\s+([A-Za-z\-\u00c0-\u017f']+(?:\s+[A-Za-z\-\u00c0-\u017f']+){0,4})",
        ]

        blocked_city_phrases = {
            "moi",
            "cote",
            "cote de moi",
            "a cote de moi",
            "pres de moi",
            "près de moi",
            "proche de moi",
            "autour de moi",
            "ma position",
            "ma localisation",
            "ici",
        }

        for pattern in location_patterns:
            city_match = re.search(pattern, query, flags=re.IGNORECASE)
            if not city_match:
                continue

            candidate_city = city_match.group(1).strip(" .,!?:;")
            if "moi" in candidate_city.lower():
                continue

            words = [w for w in candidate_city.split() if w]
            while words and words[-1].lower() in _LOCATION_STOPWORDS:
                words.pop()

            if not words:
                continue

            cleaned_candidate = " ".join(words)
            if cleaned_candidate.lower() in blocked_city_phrases:
                continue

            return cleaned_candidate

        return None
