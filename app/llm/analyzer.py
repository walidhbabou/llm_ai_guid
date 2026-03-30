import json
import re
from typing import Any

from groq import Groq

from app.core.config import settings
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
_NON_SEARCH_PATTERNS = [
    r"\bquelle\s+est\b",
    r"\bwho\s+is\b",
    r"\bwhat\s+is\b",
    r"\bcapitale\b",
    r"\bmeteo\b",
    r"\bm[ée]t[ée]o\b",
    r"\btraduis\b",
    r"\btraduire\b",
    r"\bcalcule\b",
    r"\bcombien\s+font\b",
]


class LLMQueryAnalyzer:
    def __init__(self) -> None:
        self._client = Groq(api_key=settings.groq_api_key) if settings.groq_api_key else None

    def analyze(self, query: str) -> QueryAnalysisDTO:
        if self._client is None:
            return self._fallback_analysis(query)

        user_prompt = (
            "Analyse la requete suivante et retourne uniquement le JSON demande.\\n"
            f"Requete: {query}"
        )

        try:
            completion = self._client.chat.completions.create(
                model=settings.groq_model,
                temperature=0,
                max_completion_tokens=512,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except Exception as exc:
            # Keep the API usable even when Groq credentials are missing/invalid.
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
        heuristic = self._fallback_analysis(original_query)

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
        preferences = [str(item).strip().lower() for item in preferences if str(item).strip()]
        # Preserve order while removing duplicates.
        preferences = list(dict.fromkeys(preferences))

        result_limit = data.get("result_limit", 10)
        if isinstance(result_limit, str) and result_limit.isdigit():
            result_limit = int(result_limit)
        if not isinstance(result_limit, int):
            result_limit = 10
        result_limit = max(1, min(result_limit, 20))

        city = data.get("city")
        if city is not None:
            city = str(city).strip().lower() or None

        intent = data.get("intent")
        if isinstance(intent, str):
            intent = intent.strip().lower()
        if intent not in {"search_places", "other"}:
            intent = heuristic.intent

        near_me_raw = data.get("near_me", False)
        if isinstance(near_me_raw, bool):
            near_me = near_me_raw
        elif isinstance(near_me_raw, str):
            near_me = near_me_raw.strip().lower() in {"true", "1", "yes", "oui"}
        else:
            near_me = bool(near_me_raw)

        if near_me is False and heuristic.near_me is True:
            near_me = True

        normalized = QueryAnalysisDTO(
            intent=intent,
            city=city,
            category=category,
            preferences=preferences,
            result_limit=result_limit,
            near_me=near_me,
        )

        # Lightweight safety net when model misses obvious cues.
        if normalized.category is None and heuristic.category is not None:
            normalized.category = heuristic.category
        if normalized.city is None and heuristic.city is not None:
            normalized.city = heuristic.city
        if not normalized.preferences and heuristic.preferences:
            normalized.preferences = heuristic.preferences

        return normalized

    def _fallback_analysis(self, query: str) -> QueryAnalysisDTO:
        q = query.lower()

        intent = self._infer_intent(query)

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
            intent=intent,
            city=city,
            category=category,
            preferences=preferences,
            result_limit=result_limit,
            near_me=near_me,
        )

    def _infer_intent(self, query: str) -> str:
        q = query.lower().strip()

        has_search_verb = any(
            verb in q
            for verb in [
                "cherche",
                "recherche",
                "trouve",
                "donne moi",
                "propose",
                "recommend",
                "find",
            ]
        )

        mentions_place_category = any(cat in q for cat in _ALLOWED_CATEGORIES)
        mentions_near_me = any(
            term in q
            for term in [
                "pres de moi",
                "près de moi",
                "autour de moi",
                "near me",
                "ma position",
                "ma localisation",
            ]
        )

        if has_search_verb or mentions_place_category or mentions_near_me:
            return "search_places"

        if any(re.search(pattern, q) for pattern in _NON_SEARCH_PATTERNS):
            return "other"

        return "search_places"

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
