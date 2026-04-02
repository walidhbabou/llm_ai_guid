import json
import re
import unicodedata
from typing import Any

from groq import Groq

from app.core.config import settings
from app.dto.search_dto import GuideCardDTO, PlaceDTO, QueryAnalysisDTO
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
_CITY_TERMS = ("ville", "city", "destination")
_CULTURE_TERMS = ("culture", "culturel", "culturelle", "historique", "patrimoine", "art")
_PHOTO_TERMS = ("photo", "photos", "photogenique", "instagram", "instagrammable", "shooting")
_ROMANTIC_TERMS = ("romantique", "romantic", "couple", "amour")
_SUNSET_TERMS = ("coucher de soleil", "sunset", "golden hour")


class GuideAssistant:
    def __init__(self) -> None:
        self._client = Groq(api_key=settings.llm_api_key) if settings.llm_api_key else None

    def build_response(
        self,
        *,
        query: str,
        analysis: QueryAnalysisDTO,
        places: list[PlaceDTO],
    ) -> tuple[str | None, list[str], list[GuideCardDTO]]:
        thematic_response = self._build_thematic_fallback_reply(query, analysis, places)
        if thematic_response is not None:
            return thematic_response

        if analysis.intent == "search_places":
            model_response = self._build_model_response_for_places(query, analysis, places)
            if model_response is not None:
                return model_response

            return (
                self._build_search_fallback_reply(analysis, places),
                self._build_fallback_suggested_questions(analysis),
                [],
            )

        model_response = self._build_model_response_for_question(query, analysis)
        if model_response is not None:
            return model_response

        faq_reply = self._build_faq_reply(query)
        if faq_reply:
            return faq_reply, self._build_fallback_suggested_questions(analysis), []

        reply = self._build_domain_fallback_reply(analysis.detected_language)
        return reply, self._build_fallback_suggested_questions(analysis), []

    def _build_model_response_for_places(
        self,
        query: str,
        analysis: QueryAnalysisDTO,
        places: list[PlaceDTO],
    ) -> tuple[str | None, list[str], list[GuideCardDTO]] | None:
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
    ) -> tuple[str | None, list[str], list[GuideCardDTO]] | None:
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
    ) -> tuple[str | None, list[str], list[GuideCardDTO]] | None:
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
        return cleaned_reply, suggested_questions, []

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

    def _build_thematic_fallback_reply(
        self,
        query: str,
        analysis: QueryAnalysisDTO,
        places: list[PlaceDTO],
    ) -> tuple[str | None, list[str], list[GuideCardDTO]] | None:
        normalized_query = self._normalize_text(query)
        language = analysis.detected_language

        if self._looks_like_city_photo_request(normalized_query):
            return self._build_city_photo_reply(language)

        if places:
            return None

        if self._contains_any_term(normalized_query, _ROMANTIC_TERMS) and self._contains_any_term(
            normalized_query, _SUNSET_TERMS
        ):
            return self._build_romantic_sunset_reply(language, analysis.city)

        if self._contains_any_term(normalized_query, _PHOTO_TERMS):
            return self._build_photo_spot_reply(language, analysis.city)

        return None

    def _build_city_photo_reply(self, language: str) -> tuple[str, list[str], list[GuideCardDTO]]:
        if language == "en":
            return (
                "For a cultural and photogenic city in Morocco, Fez is great for heritage and crafts, "
                "Marrakech for colors and palaces, Chefchaouen for blue streets, and Essaouira for ocean views "
                "and ramparts. Tell me your style and I will narrow it down.",
                [
                    "Which city is best for street photography?",
                    "Which city is best for sunset photos?",
                    "Find photo spots in Marrakech",
                ],
                self._build_city_photo_cards(language),
            )

        if language == "darija":
            return (
                "Ila bghiti mdina thaqafiya w photogenique f lmaghrib, Fes mzyana lmedina w sna3a, "
                "Marrakech l alwan w l9sur, Chefchaouen lz9aq zar9in, w Essaouira lbaher w ssour. "
                "Golli lia chno style li bghiti w n9tar7 3lik ahsan wa7da.",
                [
                    "Anahiya ahsan mdina l street photo?",
                    "Anahiya ahsan mdina l sunset photos?",
                    "Qelleb lia spots photo f Marrakech",
                ],
                self._build_city_photo_cards(language),
            )

        return (
            "Pour une ville culturelle et photogenique au Maroc, Fes est excellente pour le patrimoine et "
            "l'artisanat, Marrakech pour les couleurs et les palais, Chefchaouen pour les ruelles bleues, "
            "et Essaouira pour l'ocean et les remparts. Dis-moi ton style et je te dirai laquelle choisir.",
            [
                "Quelle ville pour de la street photo ?",
                "Quelle ville pour des photos au coucher du soleil ?",
                "Trouve-moi des spots photo a Marrakech",
            ],
            self._build_city_photo_cards(language),
        )

    def _build_romantic_sunset_reply(
        self,
        language: str,
        city: str | None,
    ) -> tuple[str, list[str], list[GuideCardDTO]]:
        city_segment = f" a {city}" if city else ""

        if language == "en":
            if city:
                reply = (
                    f"For a romantic sunset{city_segment}, I would focus on rooftops, calm beaches, "
                    "corniches, gardens, or panoramic viewpoints."
                )
            else:
                reply = (
                    "For a romantic sunset, I can guide you much better if you give me a city or your location. "
                    "The best options are usually a rooftop, a calm beach, a corniche, a garden, or a viewpoint."
                )
            return (
                reply,
                [
                    "Find me a romantic rooftop in Rabat",
                    "Show me sunset spots in Agadir",
                    "Search near me",
                ],
                self._build_romantic_sunset_cards(language, city),
            )

        if language == "darija":
            if city:
                reply = (
                    f"Bash tl9a blasa romantique lghorob chams{city_segment}, 9elleb 3la rooftop, plage hadya, "
                    "corniche, jnina, wla point de vue mzyan."
                )
            else:
                reply = (
                    "Bash n3awnk mzyan f had talab, 3tini smit lmdina wla khalli position dyalk. "
                    "Ghaliban ahsan ikhtiyarat homa rooftop, plage hadya, corniche, jnina, wla point de vue."
                )
            return (
                reply,
                [
                    "Qelleb lia rooftop romantique f Rabat",
                    "Werri lia blays lghorob chams f Agadir",
                    "Qelleb qrib menni",
                ],
                self._build_romantic_sunset_cards(language, city),
            )

        if city:
            reply = (
                f"Pour un coucher de soleil romantique{city_segment}, je viserais surtout un rooftop, "
                "une plage calme, une corniche, un jardin ou un point de vue panoramique."
            )
        else:
            reply = (
                "Pour ce type de demande, j'ai besoin d'une ville ou de ta position pour etre precis. "
                "En general, les meilleurs choix sont un rooftop, une plage calme, une corniche, un jardin "
                "ou un point de vue panoramique."
            )
        return (
            reply,
            [
                "Trouve-moi un rooftop romantique a Rabat",
                "Montre-moi un coucher de soleil a Agadir",
                "Cherche pres de moi",
            ],
            self._build_romantic_sunset_cards(language, city),
        )

    def _build_photo_spot_reply(
        self,
        language: str,
        city: str | None,
    ) -> tuple[str, list[str], list[GuideCardDTO]]:
        city_segment = f" a {city}" if city else ""

        if language == "en":
            if city:
                reply = (
                    f"For good photos{city_segment}, I would look first at the medina, monuments, colorful streets, "
                    "a corniche, or a panoramic viewpoint."
                )
            else:
                reply = (
                    "For good photo spots, tell me a city or share your location. I can then target medinas, "
                    "monuments, viewpoints, colorful streets, or waterfront walks."
                )
            return (
                reply,
                [
                    "Find photo spots in Fez",
                    "Show me panoramic viewpoints in Tangier",
                    "Find a photogenic place near me",
                ],
                self._build_photo_spot_cards(language, city),
            )

        if language == "darija":
            if city:
                reply = (
                    f"Ila bghiti spots mzyanin dyal tsawer{city_segment}, bda b lmedina, lma3alim, zz9aq mlowwin, "
                    "corniche, wla point de vue."
                )
            else:
                reply = (
                    "Ila bghiti spots mzyanin dyal tsawer, 3tini mdina wla khalli position dyalk. "
                    "N9dar n9elleb lik 3la medina, ma3alim, viewpoints, wla mchi dyal lbaher."
                )
            return (
                reply,
                [
                    "Qelleb lia spots photo f Fes",
                    "Werri lia viewpoints f Tanger",
                    "Qelleb blasa photogenique qrib menni",
                ],
                self._build_photo_spot_cards(language, city),
            )

        if city:
            reply = (
                f"Pour de belles photos{city_segment}, je viserais d'abord la medina, les monuments, les rues "
                "colorees, la corniche ou un point de vue panoramique."
            )
        else:
            reply = (
                "Pour des spots photo reussis, donne-moi une ville ou ta position. Je pourrai alors viser la medina, "
                "les monuments, les points de vue, les rues colorees ou une balade en bord de mer."
            )
        return (
            reply,
            [
                "Trouve-moi des spots photo a Fes",
                "Montre-moi des points de vue a Tanger",
                "Cherche un lieu photogenique pres de moi",
            ],
            self._build_photo_spot_cards(language, city),
        )

    def _build_city_photo_cards(self, language: str) -> list[GuideCardDTO]:
        if language == "en":
            return [
                self._card(
                    "Fez",
                    "Best for heritage, craft details, old medina alleys, and textured street photography.",
                    "photo spots in Fez",
                ),
                self._card(
                    "Marrakech",
                    "Strong colors, palaces, gardens, and lively scenes for architecture and portraits.",
                    "photo spots in Marrakech",
                ),
                self._card(
                    "Chefchaouen",
                    "Blue streets and soft light for calm urban photos and visual storytelling.",
                    "photo spots in Chefchaouen",
                ),
                self._card(
                    "Essaouira",
                    "Ramparts, ocean, port, and golden hour make it great for coastal photography.",
                    "photo spots in Essaouira",
                ),
            ]

        if language == "darija":
            return [
                self._card(
                    "Fes",
                    "Mzyana l patrimoine, sna3a, zz9aq dial lmedina, w street photo b details zwinin.",
                    "spots photo f Fes",
                ),
                self._card(
                    "Marrakech",
                    "Alwan qwiya, l9sur, jnanat, w jaw hay bash tsawer architecture w portraits.",
                    "spots photo f Marrakech",
                ),
                self._card(
                    "Chefchaouen",
                    "Z9aq zar9in w daw hani, mzyana l tsawer hadi2a w storytelling.",
                    "spots photo f Chefchaouen",
                ),
                self._card(
                    "Essaouira",
                    "Ssour, lbaher, l port, w golden hour kay3tiw tsawer zwinin bzaf.",
                    "spots photo f Essaouira",
                ),
            ]

        return [
            self._card(
                "Fes",
                "Ideale pour le patrimoine, l'artisanat, les ruelles de la medina et la street photo pleine de details.",
                "spots photo a Fes",
            ),
            self._card(
                "Marrakech",
                "Parfaite pour les couleurs, les palais, les jardins et les scenes vivantes d'architecture ou de portrait.",
                "spots photo a Marrakech",
            ),
            self._card(
                "Chefchaouen",
                "Tres bonne option pour les ruelles bleues, la lumiere douce et une ambiance photo plus calme.",
                "spots photo a Chefchaouen",
            ),
            self._card(
                "Essaouira",
                "Excellente pour les remparts, l'ocean, le port et les photos au coucher du soleil.",
                "spots photo a Essaouira",
            ),
        ]

    def _build_romantic_sunset_cards(
        self,
        language: str,
        city: str | None,
    ) -> list[GuideCardDTO]:
        default_city = city or "Rabat"

        if language == "en":
            return [
                self._card("Rooftop", "Great for city lights, privacy, and a panoramic sunset view.", f"romantic rooftop in {default_city}"),
                self._card("Calm beach", "Best if you want sea views, quiet vibes, and open sunset light.", f"calm beach in {default_city}"),
                self._card("Corniche", "Good for a walk, sea breeze, and sunset photos as a couple.", f"corniche sunset in {default_city}"),
                self._card("Viewpoint", "Useful if you want a broad panoramic view and golden-hour photos.", f"panoramic viewpoint in {default_city}"),
            ]

        if language == "darija":
            return [
                self._card("Rooftop", "Mzyan l ambiance, vue 3la lmdina, w lghorob chams b romantic vibe.", f"rooftop romantique f {default_city}"),
                self._card("Plage hadya", "Mzyana ila bghiti lbaher, hdou2, w daw zwin dial sunset.", f"plage hadya f {default_city}"),
                self._card("Corniche", "Mzyana l tmchiya, lhawaa, w tsawer couples m3a sunset.", f"corniche sunset f {default_city}"),
                self._card("Point de vue", "Mzyan ila bghiti vue kbira w photos panoramiques.", f"point de vue panoramique f {default_city}"),
            ]

        return [
            self._card("Rooftop", "Ideal pour une ambiance intime, une belle vue urbaine et un coucher de soleil en hauteur.", f"rooftop romantique a {default_city}"),
            self._card("Plage calme", "Tres bon choix si vous voulez la mer, le calme et une lumiere douce au coucher du soleil.", f"plage calme a {default_city}"),
            self._card("Corniche", "Pratique pour une promenade romantique avec vue ouverte et belles photos de fin de journee.", f"corniche coucher de soleil a {default_city}"),
            self._card("Point de vue", "Utile si vous cherchez une vue panoramique et un spot photo tres visuel.", f"point de vue panoramique a {default_city}"),
        ]

    def _build_photo_spot_cards(
        self,
        language: str,
        city: str | None,
    ) -> list[GuideCardDTO]:
        default_city = city or "Fes"

        if language == "en":
            return [
                self._card("Medina", "Best for textures, doors, alleys, and street scenes.", f"medina photo spots in {default_city}"),
                self._card("Monuments", "Useful for architecture, symmetry, and iconic city shots.", f"monuments in {default_city}"),
                self._card("Viewpoint", "Good if you want an overview and wide-angle city photos.", f"panoramic viewpoint in {default_city}"),
                self._card("Corniche", "A solid option for ocean walks, movement, and golden-hour shots.", f"corniche in {default_city}"),
            ]

        if language == "darija":
            return [
                self._card("Medina", "Mzyana l textures, lbiban, zz9aq, w street scenes.", f"spots photo lmedina f {default_city}"),
                self._card("Ma3alim", "Mzyanin l architecture, symmetry, w tsawer iconic.", f"ma3alim f {default_city}"),
                self._card("Point de vue", "Mzyan ila bghiti vue 3amma w tsawer wide.", f"point de vue panoramique f {default_city}"),
                self._card("Corniche", "Mzyana l mchi, lbaher, w tsawer golden hour.", f"corniche f {default_city}"),
            ]

        return [
            self._card("Medina", "Bonne base pour les textures, les portes, les ruelles et la street photo.", f"spots photo medina a {default_city}"),
            self._card("Monuments", "Tres utile pour l'architecture, les cadrages symetriques et les images iconiques.", f"monuments a {default_city}"),
            self._card("Point de vue", "Bon choix si vous voulez une vue d'ensemble et des photos larges de la ville.", f"point de vue panoramique a {default_city}"),
            self._card("Corniche", "Pratique pour les balades en bord de mer, le mouvement et la golden hour.", f"corniche a {default_city}"),
        ]

    def _card(self, title: str, description: str, query: str | None = None) -> GuideCardDTO:
        return GuideCardDTO(title=title, description=description, query=query)

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

    def _contains_any_term(self, normalized_query: str, terms: tuple[str, ...]) -> bool:
        return any(self._contains_term(normalized_query, term) for term in terms)

    def _contains_term(self, normalized_query: str, term: str) -> bool:
        escaped_term = re.escape(term).replace(r"\ ", r"\s+")
        pattern = rf"(?<!\w){escaped_term}(?!\w)"
        return re.search(pattern, normalized_query) is not None

    def _looks_like_city_photo_request(self, normalized_query: str) -> bool:
        has_city_term = self._contains_any_term(normalized_query, _CITY_TERMS)
        has_theme_term = self._contains_any_term(normalized_query, _CULTURE_TERMS + _PHOTO_TERMS)
        return has_city_term and has_theme_term

    def _normalize_text(self, value: str) -> str:
        ascii_value = unicodedata.normalize("NFKD", value)
        ascii_value = "".join(ch for ch in ascii_value if not unicodedata.combining(ch))
        ascii_value = ascii_value.lower()
        ascii_value = re.sub(r"[’']", " ", ascii_value)
        ascii_value = re.sub(r"[^a-z0-9\s-]", " ", ascii_value)
        ascii_value = re.sub(r"\s+", " ", ascii_value).strip()
        return ascii_value
