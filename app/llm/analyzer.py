import json
import re
import unicodedata
from typing import Any

from groq import Groq

from app.core.config import settings
from app.dto.search_dto import QueryAnalysisDTO
from app.llm.system_prompt import ANALYSIS_SYSTEM_PROMPT

_ALLOWED_CATEGORIES = {
    "restaurant",
    "cafe",
    "musee",
    "plage",
    "monument",
    "parc",
    "hotel",
    "mosquee",
}
_LOCATION_STOPWORDS = {
    "a",
    "au",
    "aux",
    "dans",
    "de",
    "des",
    "du",
    "et",
    "la",
    "le",
    "les",
    "mais",
    "mes",
    "moi",
    "pres",
    "proche",
    "svp",
    "stp",
    "sur",
}
_CITY_BREAK_TOKENS = {
    "bghit",
    "cafe",
    "cafes",
    "calme",
    "familial",
    "hotel",
    "jam",
    "jam3",
    "manger",
    "monument",
    "musee",
    "parc",
    "pas",
    "plage",
    "restaurant",
    "resto",
    "romantique",
    "wifi",
}
_NEAR_ME_TERMS = (
    "pres de moi",
    "proche de moi",
    "autour de moi",
    "a cote de moi",
    "near me",
    "cerca de mi",
    "vicino a me",
    "perto de mim",
    "in der nahe",
    "a proximite",
    "ma position",
    "ma localisation",
    "autour d ici",
    "autour dici",
    "jba3 dyali",
    "jba3i",
    "hdriya",
    "hdriya jba3i",
    "qareeb dyali",
)
_SEARCH_VERBS = (
    "cherche",
    "recherche",
    "trouve",
    "donne moi",
    "montre moi",
    "propose",
    "suggere",
    "recommend",
    "find",
    "show me",
    "quiero",
    "voglio",
    "ich mochte",
)
_PLACE_QUESTION_TERMS = (
    "ou manger",
    "ou boire",
    "ou dormir",
    "ou aller",
    "ou sortir",
    "que visiter",
    "quoi visiter",
    "que faire",
    "quoi faire",
    "where to eat",
    "where to stay",
    "where to go",
    "what to visit",
    "best place",
    "best places",
    "donde comer",
    "dove mangiare",
)
_GENERAL_QUESTION_PATTERNS = (
    r"\bquelle est\b",
    r"\bquel est\b",
    r"\bqui est\b",
    r"\bwhat is\b",
    r"\bwho is\b",
    r"\bc est quoi\b",
    r"\bc est qui\b",
    r"\btraduis\b",
    r"\btraduire\b",
    r"\bcalcule\b",
    r"\bcombien font\b",
    r"\bmeteo\b",
    r"\bweather\b",
)
_DARIJA_TERMS = (
    "bghit",
    "kayn",
    "kain",
    "daba",
    "ana f",
    "jba3i",
    "jba3 dyali",
    "rkhis",
    "ghali",
    "wla",
    "drari",
    "safi",
)
_ENGLISH_TERMS = (
    "near me",
    "where",
    "find",
    "show me",
    "best",
    "cheap",
    "open now",
)
_SPANISH_TERMS = (
    "donde",
    "cerca de mi",
    "mejor",
    "buscar",
    "quiero",
)
_GERMAN_TERMS = (
    "wo",
    "in der nahe",
    "beste",
    "ich mochte",
    "finden",
)
_ITALIAN_TERMS = (
    "dove",
    "vicino a me",
    "migliore",
    "voglio",
    "trovare",
)
_PORTUGUESE_TERMS = (
    "onde",
    "perto de mim",
    "melhor",
    "quero",
    "encontrar",
)
_CATEGORY_TERMS = {
    "restaurant": (
        "restaurant",
        "restaurants",
        "restaurante",
        "resto",
        "restos",
        "manger",
        "comer",
        "mangiare",
        "essen",
        "dejeuner",
        "diner",
        "eat",
        "snack",
        "grill",
        "mat3am",
        "matam",
    ),
    "cafe": (
        "cafe",
        "cafes",
        "cafeteria",
        "coffee",
        "coffee shop",
        "boire",
        "boisson",
        "juice",
        "jus",
        "brunch",
        "espresso",
        "latte",
        "jam",
        "jam3",
    ),
    "musee": (
        "musee",
        "musees",
        "museum",
        "museo",
        "galerie",
        "expo",
        "exposition",
    ),
    "plage": (
        "plage",
        "plages",
        "beach",
        "playa",
        "praia",
        "spiaggia",
        "bord de mer",
    ),
    "monument": (
        "monument",
        "monuments",
        "site historique",
        "kasbah",
        "medina",
    ),
    "parc": (
        "parc",
        "parcs",
        "parque",
        "jardin",
        "jardins",
        "garden",
        "espace vert",
    ),
    "hotel": (
        "hotel",
        "hotels",
        "alojamiento",
        "albergo",
        "riad",
        "riads",
        "hebergement",
        "logement",
        "auberge",
        "hostel",
        "dormir",
    ),
    "mosquee": (
        "mosquee",
        "mosque",
        "mosques",
        "masjid",
        "masjed",
        "mezquita",
        "moschea",
        "mesquita",
        "priere",
        "prayer",
    ),
}
_PREFERENCE_TERMS = {
    "meilleur": ("meilleur", "meilleurs", "meilleure", "best", "top"),
    "pas cher": ("pas cher", "bon marche", "cheap", "budget", "rkhis", "drar"),
    "luxe": ("luxe", "premium", "haut de gamme", "ghali", "expensive"),
    "calme": ("calme", "quiet", "tranquille", "saktiya"),
    "familial": ("familial", "famille", "family", "kids", "drari", "wlad"),
    "romantique": ("romantique", "romantic", "couple", "amour"),
    "wifi": ("wifi", "wi fi", "internet"),
    "terrasse": ("terrasse", "rooftop", "outside", "exterieur"),
    "ouvert tard": ("ouvert tard", "late night", "ouvert 24h", "24h", "24 7"),
    "vue mer": ("vue mer", "sea view", "ocean view", "bord de mer"),
    "travail": ("travail", "coworking", "teletravail", "ordinateur", "pc", "work"),
    "marocain": ("marocain", "marocaine", "tajine", "tagine"),
    "italien": ("italien", "italienne", "pizza", "pasta", "pates"),
    "vegetarien": ("vegetarien", "vegetarienne", "vege", "veggie", "sans viande"),
    "halal": ("halal",),
    "jus": ("jus", "juice", "smoothie", "jam", "jam3"),
}


class LLMQueryAnalyzer:
    def __init__(self) -> None:
        self._client = Groq(api_key=settings.groq_api_key) if settings.groq_api_key else None

    def analyze(self, query: str) -> QueryAnalysisDTO:
        if self._client is None:
            return self._fallback_analysis(query)

        user_prompt = (
            "Analyse la requete suivante et retourne uniquement le JSON demande.\n"
            f"Requete utilisateur: {query}"
        )

        try:
            completion = self._client.chat.completions.create(
                model=settings.groq_model,
                temperature=0,
                max_completion_tokens=512,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except Exception:
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

        raw_intent = data.get("intent")
        intent = str(raw_intent).strip().lower() if isinstance(raw_intent, str) else heuristic.intent
        if intent not in {"search_places", "other"}:
            intent = heuristic.intent

        raw_detected_language = data.get("detected_language")
        detected_language = self._normalize_detected_language(raw_detected_language, original_query)

        raw_city = data.get("city")
        city = None
        if raw_city is not None:
            city_candidate = str(raw_city).strip()
            if city_candidate and city_candidate not in {"null", "None"}:
                city = city_candidate

        raw_category = data.get("category")
        category = None
        if isinstance(raw_category, str):
            candidate = self._normalize_text(raw_category)
            for allowed_category in _ALLOWED_CATEGORIES:
                if candidate == allowed_category:
                    category = allowed_category
                    break

        raw_preferences = data.get("preferences")
        preferences: list[str] = []
        if isinstance(raw_preferences, list):
            for item in raw_preferences:
                cleaned = self._normalize_text(str(item))
                if cleaned:
                    preferences.append(cleaned)
        preferences = list(dict.fromkeys(preferences))

        raw_limit = data.get("result_limit", heuristic.result_limit)
        if isinstance(raw_limit, str) and raw_limit.isdigit():
            raw_limit = int(raw_limit)
        if not isinstance(raw_limit, int):
            raw_limit = heuristic.result_limit
        result_limit = max(1, min(raw_limit, 20))

        raw_near_me = data.get("near_me", heuristic.near_me)
        if isinstance(raw_near_me, bool):
            near_me = raw_near_me
        elif isinstance(raw_near_me, str):
            near_me = self._normalize_text(raw_near_me) in {"true", "1", "yes", "oui"}
        else:
            near_me = bool(raw_near_me)

        normalized = QueryAnalysisDTO(
            intent=intent,
            detected_language=detected_language,
            city=city,
            category=category,
            preferences=preferences,
            result_limit=result_limit,
            near_me=near_me,
        )

        if normalized.intent == "other" and heuristic.intent == "search_places":
            if any(
                [
                    normalized.category,
                    heuristic.category,
                    normalized.city,
                    heuristic.city,
                    normalized.near_me,
                    heuristic.near_me,
                ]
            ):
                normalized.intent = "search_places"

        if heuristic.category is not None and normalized.category != heuristic.category:
            normalized.category = heuristic.category
        if normalized.city is None and heuristic.city is not None:
            normalized.city = heuristic.city
        if not normalized.preferences and heuristic.preferences:
            normalized.preferences = heuristic.preferences
        if normalized.near_me is False and heuristic.near_me is True:
            normalized.near_me = True

        return normalized

    def _fallback_analysis(self, query: str) -> QueryAnalysisDTO:
        normalized_query = self._normalize_text(query)

        return QueryAnalysisDTO(
            intent=self._infer_intent(normalized_query),
            detected_language=self._detect_language(query, normalized_query),
            city=self._extract_city_candidate(query),
            category=self._extract_category(normalized_query),
            preferences=self._extract_preferences(normalized_query),
            result_limit=self._extract_result_limit(normalized_query),
            near_me=self._is_near_me(normalized_query),
        )

    def _infer_intent(self, normalized_query: str) -> str:
        has_search_verb = any(self._contains_term(normalized_query, term) for term in _SEARCH_VERBS)
        mentions_category = self._extract_category(normalized_query) is not None
        mentions_near_me = self._is_near_me(normalized_query)
        mentions_place_question = any(
            self._contains_term(normalized_query, term) for term in _PLACE_QUESTION_TERMS
        )

        if has_search_verb or mentions_category or mentions_near_me or mentions_place_question:
            return "search_places"

        if any(re.search(pattern, normalized_query) for pattern in _GENERAL_QUESTION_PATTERNS):
            return "other"

        return "search_places"

    def _extract_category(self, normalized_query: str) -> str | None:
        for category, terms in _CATEGORY_TERMS.items():
            if any(self._contains_term(normalized_query, term) for term in terms):
                return category
        return None

    def _extract_preferences(self, normalized_query: str) -> list[str]:
        preferences: list[str] = []
        for label, terms in _PREFERENCE_TERMS.items():
            if any(self._contains_term(normalized_query, term) for term in terms):
                preferences.append(label)
        return preferences

    def _extract_result_limit(self, normalized_query: str) -> int:
        limit_match = re.search(r"\b(?:top\s+)?(\d{1,2})\b", normalized_query)
        if not limit_match:
            return 10
        return max(1, min(int(limit_match.group(1)), 20))

    def _is_near_me(self, normalized_query: str) -> bool:
        if any(self._contains_term(normalized_query, term) for term in _NEAR_ME_TERMS):
            return True
        return bool(re.search(r"\b(?:je suis (?:a|dans)|kain fi|daba fi|ana f)\b", normalized_query))

    def _extract_city_candidate(self, query: str) -> str | None:
        location_patterns = (
            r"\bje\s+suis\s+(?:a|\u00e0|au|aux|dans)\s+([A-Za-z\-\u00c0-\u017f']+(?:\s+[A-Za-z\-\u00c0-\u017f']+){0,4})",
            r"\b(?:a|\u00e0|au|aux|dans|de)\s+([A-Za-z\-\u00c0-\u017f']+(?:\s+[A-Za-z\-\u00c0-\u017f']+){0,4})",
            r"\b(?:kain\s+fi|daba\s+fi|ana\s+f)\s+([A-Za-z\-\u00c0-\u017f']+(?:\s+[A-Za-z\-\u00c0-\u017f']+){0,4})",
        )

        blocked_city_phrases = {
            "a cote",
            "a cote de moi",
            "autour de moi",
            "ici",
            "ma localisation",
            "ma position",
            "me",
            "mi",
            "mim",
            "moi",
            "pres de moi",
            "proche de moi",
        }

        for pattern in location_patterns:
            city_match = re.search(pattern, query, flags=re.IGNORECASE)
            if not city_match:
                continue

            candidate_city = city_match.group(1).strip(" .,!?:;")
            normalized_candidate = self._normalize_text(candidate_city)
            if not normalized_candidate or "moi" in normalized_candidate:
                continue

            words = [word for word in normalized_candidate.split() if word]
            trimmed_words: list[str] = []
            for word in words:
                if word in _CITY_BREAK_TOKENS:
                    break
                trimmed_words.append(word)
            words = trimmed_words

            while words and words[-1] in _LOCATION_STOPWORDS:
                words.pop()

            cleaned_candidate = " ".join(words).strip()
            if not cleaned_candidate or cleaned_candidate in blocked_city_phrases:
                continue

            return cleaned_candidate

        return None

    def _normalize_text(self, value: str) -> str:
        ascii_value = unicodedata.normalize("NFKD", value)
        ascii_value = "".join(ch for ch in ascii_value if not unicodedata.combining(ch))
        ascii_value = ascii_value.lower()
        ascii_value = re.sub(r"[’']", " ", ascii_value)
        ascii_value = re.sub(r"[^a-z0-9\s-]", " ", ascii_value)
        ascii_value = re.sub(r"\s+", " ", ascii_value).strip()
        return ascii_value

    def _contains_term(self, normalized_query: str, term: str) -> bool:
        escaped_term = re.escape(term).replace(r"\ ", r"\s+")
        pattern = rf"(?<!\w){escaped_term}(?!\w)"
        return re.search(pattern, normalized_query) is not None

    def _detect_language(self, query: str, normalized_query: str | None = None) -> str:
        normalized_query = normalized_query or self._normalize_text(query)

        if re.search(r"[\u0600-\u06FF]", query):
            return "ar"
        if any(self._contains_term(normalized_query, term) for term in _DARIJA_TERMS):
            return "darija"
        if any(self._contains_term(normalized_query, term) for term in _ENGLISH_TERMS):
            return "en"
        if any(self._contains_term(normalized_query, term) for term in _SPANISH_TERMS):
            return "es"
        if any(self._contains_term(normalized_query, term) for term in _GERMAN_TERMS):
            return "de"
        if any(self._contains_term(normalized_query, term) for term in _ITALIAN_TERMS):
            return "it"
        if any(self._contains_term(normalized_query, term) for term in _PORTUGUESE_TERMS):
            return "pt"
        return "fr"

    def _normalize_detected_language(self, raw_language: Any, original_query: str) -> str:
        heuristic_language = self._detect_language(original_query)
        if not isinstance(raw_language, str):
            return heuristic_language

        candidate = self._normalize_text(raw_language).replace(" ", "-")
        language_aliases = {
            "ar": "ar",
            "arabic": "ar",
            "arabe": "ar",
            "darija": "darija",
            "de": "de",
            "english": "en",
            "en": "en",
            "anglais": "en",
            "es": "es",
            "espanol": "es",
            "spanish": "es",
            "fr": "fr",
            "francais": "fr",
            "french": "fr",
            "german": "de",
            "allemand": "de",
            "it": "it",
            "italian": "it",
            "italien": "it",
            "other": "other",
            "portuguese": "pt",
            "portugais": "pt",
            "pt": "pt",
        }

        if not candidate:
            return heuristic_language
        return language_aliases.get(candidate, candidate if len(candidate) <= 12 else heuristic_language)
