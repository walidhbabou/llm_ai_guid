import json
import re
import unicodedata
from typing import Any

from groq import Groq

from app.core.config import settings
from app.dto.search_dto import GuideCardDTO, PlaceDTO, QueryAnalysisDTO
from app.llm.gemini_client import GroqCompatibleGemini
from app.llm.system_prompt import GUIDE_RESPONSE_SYSTEM_PROMPT

_OUT_OF_SCOPE_PATTERNS = (
    r"\bcalcule\b",
    r"\bcode\b",
    r"\btraduis\b",
    r"\btraduire\b",
)
_FAQ_REPLIES = (
    (r"\bcapitale\b.*\bmaroc\b", "La capitale du Maroc est Rabat."),
    (r"\bmaroc\b.*\bcapitale\b", "La capitale du Maroc est Rabat."),
    (r"\bmonnaie\b.*\bmaroc\b", "La monnaie du Maroc est le dirham marocain (MAD)."),
    (r"\bmaroc\b.*\bmonnaie\b", "La monnaie du Maroc est le dirham marocain (MAD)."),
    (
        r"\blangue\b.*\bmaroc\b",
        "Au Maroc, l'arabe et l'amazigh sont les langues officielles, et le francais est tres utilise.",
    ),
    (
        r"\bmaroc\b.*\blangue\b",
        "Au Maroc, l'arabe et l'amazigh sont les langues officielles, et le francais est tres utilise.",
    ),
    (
        r"\bmeilleure saison\b.*\bmaroc\b",
        "Le printemps (mars-mai) et l'automne (septembre-novembre) sont les meilleures saisons pour visiter le Maroc.",
    ),
    (
        r"\bquand visiter\b.*\bmaroc\b",
        "Le printemps (mars-mai) et l'automne (septembre-novembre) sont les meilleures saisons pour visiter le Maroc.",
    ),
    (
        r"\bc est quoi\b.*\bhamm?am\b",
        "Le hammam est un bain vapeur traditionnel marocain — a la fois rituel d'hygiene et moment social. On y suit une sequence: chaleur, kessa (gant exfoliant), savon beldi. Les hammams de quartier sont bien plus authentiques que les spas touristiques.",
    ),
    (
        r"\bhamm?am\b.*\bc est quoi\b",
        "Le hammam est un bain vapeur traditionnel marocain — a la fois rituel d'hygiene et moment social. On y suit une sequence: chaleur, kessa (gant exfoliant), savon beldi. Les hammams de quartier sont bien plus authentiques que les spas touristiques.",
    ),
    (
        r"\bc est quoi\b.*\btajine\b",
        "Le tajine est le plat national marocain — une cuisson lente dans un recipient en terre cuite en forme de cone, qui garde les saveurs et l'humidite. Agneau aux pruneaux, poulet au citron confit, legumes... chaque region a ses variantes.",
    ),
    (
        r"\bc est quoi\b.*\bcouscous\b",
        "Le couscous est le plat du vendredi au Maroc, plat de partage familial par excellence. De la semoule de ble dur, cuite a la vapeur, servie avec des legumes, de la viande et un bouillon parfume. La base de la cuisine berbere depuis des siecles.",
    ),
)
_CITY_TERMS = ("ville", "city", "destination", "region", "endroit")
_CULTURE_TERMS = ("culture", "culturel", "culturelle", "historique", "patrimoine", "art", "artisanat", "tradition")
_PHOTO_TERMS = ("photo", "photos", "photogenique", "instagram", "instagrammable", "shooting", "photographie")
_ROMANTIC_TERMS = ("romantique", "romantic", "couple", "amour")
_SUNSET_TERMS = ("coucher de soleil", "sunset", "golden hour")
_FAMILY_TERMS = (
    "famille",
    "familial",
    "familiale",
    "family",
    "enfants",
    "enfant",
    "kids",
    "children",
    "drari",
    "wlad",
    "sortie famille",
    "sortie familiale",
    "avec les enfants",
    "avec mes enfants",
    "avec ma famille",
    "en famille",
    "family trip",
    "family day",
)
_BEST_SEASON_TERMS = (
    "meilleure saison",
    "best season",
    "quelle saison",
    "quand visiter",
    "when to visit",
    "quelle periode",
    "quel mois",
    "saison ideale",
    "quand partir",
    "best time",
    "when to go",
    "ramadan",
)
_BUDGET_TERMS = (
    "combien ca coute",
    "combien coute",
    "prix moyen",
    "budget voyage",
    "voyage pas cher",
    "voyager pas cher",
    "how much does",
    "is morocco cheap",
    "cost of travel",
    "travel budget",
)
_GASTRONOMY_TERMS = (
    "gastronomie",
    "cuisine marocaine",
    "plat typique",
    "specialite",
    "quoi manger",
    "que manger",
    "what to eat",
    "moroccan food",
    "food in morocco",
    "tajine",
    "couscous",
    "pastilla",
    "harira",
    "msemen",
)
_ITINERARY_TERMS = (
    "programme",
    "plan",
    "itineraire",
    "itinéraire",
    "journee",
    "journée",
    "aujourd",
    "aujourd'hui",
    "today",
    "day trip",
    "avec ma femme",
    "with my wife",
    "couple",
    "sortie",
    "que faire aujourd",
    "quoi faire aujourd",
    "siyaha",
    "blasa siyahia",
    "avec les enfants",
    "avec mes enfants",
    "avec ma famille",
    "sortie famille",
    "sortie familiale",
    "en famille",
    "family trip",
    "family day",
    "weekend",
)

_DEFAULT_ITINERARY_SLOTS_FR = ("Matin", "Midi", "Après-midi", "Goûter", "Soir")
_DEFAULT_ITINERARY_SLOTS_EN = ("Morning", "Lunch", "Afternoon", "Coffee", "Evening")
_DEFAULT_ITINERARY_SLOTS_DARIJA = ("Sbah", "Gheda", "3chiya", "9ahwa", "L3chiya/3cha")

_RABAT_ITINERARY_FR = """Commence ta journée au cœur de Rabat par une immersion dans son histoire et son atmosphère unique. Le matin, dirige-toi vers la majestueuse Kasbah des Oudayas, un lieu emblématique aux ruelles blanches et bleues, offrant une vue spectaculaire sur l'océan Atlantique. Prends le temps de te perdre dans ses petites allées, puis fais une pause au célèbre Café Maure pour savourer un thé à la menthe avec des pâtisseries marocaines.

Continue ensuite vers la Tour Hassan et le Mausolée Mohammed V, symboles historiques et architecturaux de la ville. L'ambiance y est calme et solennelle, idéale pour apprécier la richesse culturelle du Maroc.

À midi, dirige-toi vers la marina de Bouregreg pour un déjeuner avec vue sur le fleuve et les bateaux. L'endroit est moderne et agréable, parfait pour se détendre avant de reprendre la visite.

L'après-midi, explore la médina de Rabat, plus authentique et moins touristique que d'autres villes. Tu pourras y découvrir l'artisanat local, acheter des souvenirs et ressentir le rythme de vie traditionnel marocain.

Termine ta journée par une balade sur la plage au coucher du soleil. Le bruit des vagues et la lumière dorée offrent une ambiance paisible pour conclure cette journée riche en découvertes."""

_RABAT_ITINERARY_EN = """Start your day in the heart of Rabat with a journey through its layered history and breezy Atlantic atmosphere. Head first to the Kasbah of the Udayas, a stunning medina perched above the river, with whitewashed alleys and blue-painted doors that frame views of the ocean. Take your time wandering its quiet lanes and stop for a mint tea at the old Moorish café overlooking the water.

From there, make your way to the Hassan Tower and the Mohammed V Mausoleum, two of Morocco's most iconic landmarks side by side. The open plaza is peaceful in the morning light, and the craftsmanship of the mausoleum is genuinely breathtaking.

Around midday, head down to the Bouregreg Marina for lunch with a view of the river and the old medina of Salé across the water. It is a relaxed, modern spot that offers a nice contrast to the historic morning.

In the afternoon, dive into Rabat's medina — smaller and less crowded than Fez or Marrakech, it feels genuinely lived-in. Browse local crafts, pick up a souvenir, and soak up the rhythms of daily Moroccan life.

End the day with a walk along Rabat Beach as the sun drops toward the horizon. The sound of the waves, the golden light, and the ocean air make for a perfect close to a rich and rewarding day."""

_RABAT_ITINERARY_DARIJA = """Bda nharek f qelb Rbat, mdina li fihà l tarikh w nefes lbaher. F sbah, mchi l Kasbah Lwdaya, blasa iconic b zz9aq byed w zar9in w manzar 3la l Atlantic. Tdowwer f zzwawey diyalha b shwiya, w sted f Café Maure bach tsherb atay b na3na3 m3a hlwiyat maghribiya.

Mn ba3d, mchi l Tour Hassan w Mawsolee Mohammed V. Had ljuw howa hadi w kayn l wqar — mzyan bash tqdir t7ess b 3omq tarikh lmaghrib.

F l ghda, nazzel l Bouregreg Marina. Fhad l blassa tl9a makan m3asri w zwin, mzyan bach takol w tertta7 qbel ma tkammel siyahtek.

F l 3chiya, kel lmedina dyal Rbat — aqel d'affluence mn medina Fes aw Marrakech, w fihà nafs dyal l7anotat, l snayyi3, w 7it n3ach dyal sharab. Mzyana bash tshouf shi souvenir w testa3mel l7awa dyal l medina l7qiqiya.

Khtem nharek b promenade 3la plage Rbat m3a l ghroob. Sawt lmawj w daw dhahabi dial chems kay3tiw ljaw ideal bach termm had nhar zwine."""

_MARRAKECH_ITINERARY_FR = """La journée commence dans la Médina de Marrakech, là où les couleurs, les sons et les parfums t'enveloppent dès les premières heures. Le matin appartient aux ruelles calmes avant que l'agitation ne s'installe — c'est le meilleur moment pour visiter la medersa Ben Youssef, chef-d'œuvre de l'architecture arabe, ou pour se perdre dans les souks de teinturerie et d'épices.

En milieu de matinée, prends un café ou un jus frais dans l'un des petits établissements cachés de la Médina, loin de l'effervescence des grandes places. Profite de ce moment de calme avant la foule de midi.

Pour le déjeuner, dirige-toi vers un rooftop qui surplombe les toits ocres de la ville. La vue sur les minarets, avec l'Atlas en toile de fond par temps clair, vaut à elle seule le détour.

L'après-midi, visite les jardins Majorelle ou les Jardins de la Ménara pour une pause verdoyante et fraîche, loin du brouhaha des souks. Ces espaces offrent un contraste saisissant avec l'agitation de la Médina.

Quand le soleil commence à décliner, rejoins la place Jemaa el-Fna. C'est là que Marrakech révèle toute sa magie : musiciens gnaoua, vendeurs de jus d'orange fraîchement pressé et fumées des grillades du soir créent une atmosphère unique que peu de villes au monde peuvent égaler."""

_MARRAKECH_ITINERARY_EN = """Marrakech rewards those who rise early. Start your morning in the medina before the crowds arrive — the air is cooler, the light is golden, and the narrow alleys feel like a living museum. Make your way to the Ben Youssef Medersa, a masterpiece of Andalusian architecture with intricate tilework and carved stucco that will stop you in your tracks.

Spend mid-morning wandering the souks: the dyers' quarter, the spice stalls, the leather workshops. Let yourself get pleasantly lost — that is part of the experience. Grab a fresh orange juice from a street cart when you need a break.

For lunch, find a rooftop terrace with views over the ochre rooftops and distant Atlas Mountains. The contrast of the bustling medina below and the open sky above is something you will not forget.

In the afternoon, escape the midday heat in the lush Majorelle Garden or the serene Menara Gardens. Both are beautiful, peaceful, and a world apart from the energy of the souks.

As dusk falls, make your way to Jemaa el-Fna square and watch the city transform. Musicians, storytellers, food stalls, and acrobats fill the space in a spectacle that has enchanted travellers for centuries. Stay for dinner at the square's edge and let the evening unfold around you."""

_FEZ_ITINERARY_FR = """Fès se mérite dès les premières heures du matin, avant que la chaleur et l'affluence ne s'installent. Commence par la célèbre tannerie de Chouara, l'une des plus vieilles et des plus pittoresques du monde — les terrasses des maisons voisines offrent une vue plongeante sur les cuves de couleur qui teignent le cuir depuis des siècles. Prends quelques feuilles de menthe : elles atténuent les odeurs et ajoutent un peu de fraîcheur à l'expérience.

Poursuis dans les dédales de la médina de Fès el-Bali, classée au patrimoine mondial de l'UNESCO. C'est l'une des médinas les mieux préservées du monde arabe — ses ruelles peuvent descendre à un mètre de largeur, et chaque tournant réserve une surprise : une porte monumentale, un souk de ferronnerie, un morceau de mosaïque oubliée.

À midi, fais une halte dans un riad pour un repas traditionnel — tajine, bastilla, ou harira selon la saison. Le cadre d'un patio ombragé avec une fontaine au centre est la meilleure façon de souffler entre deux visites.

L'après-midi, visite la medersa Bou Inania, dont l'architecture et les détails sculptés rivalisent avec les plus beaux monuments d'Andalousie. Non loin, la mosquée des Andalous témoigne des échanges culturels qui ont fait la richesse de Fès au fil des siècles.

Termine la journée en montant sur un point de vue dominant la ville, pour embrasser du regard le patchwork de toits, de minarets et de terrasses qui s'étale à perte de vue. Le coucher de soleil sur Fès est une image que l'on garde longtemps."""


class GuideAssistant:
    def __init__(self) -> None:
        self._groq_client = Groq(api_key=settings.llm_api_key) if settings.llm_api_key else None
        self._gemini_client = GroqCompatibleGemini() if settings.gemini_enabled else None

    def build_response(
        self,
        *,
        query: str,
        analysis: QueryAnalysisDTO,
        places: list[PlaceDTO],
    ) -> tuple[str | None, list[str], list[GuideCardDTO], dict[str, str]]:
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
                {},
            )

        model_response = self._build_model_response_for_question(query, analysis)
        if model_response is not None:
            return model_response

        faq_reply = self._build_faq_reply(query)
        if faq_reply:
            return faq_reply, self._build_fallback_suggested_questions(analysis), [], {}

        reply = self._build_domain_fallback_reply(analysis.detected_language)
        return reply, self._build_fallback_suggested_questions(analysis), [], {}

    def _build_model_response_for_places(
        self,
        query: str,
        analysis: QueryAnalysisDTO,
        places: list[PlaceDTO],
    ) -> tuple[str | None, list[str], list[GuideCardDTO], dict[str, str]] | None:
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
                    "types": place.types,
                    "rating": place.rating
                }
                for place in places[:5]
            ],
        }
        
        # Generate dedicated descriptions for each place
        places_descriptions = self._generate_place_descriptions(places[:5], analysis.detected_language)
        
        result = self._complete_response(payload, analysis)
        if result is not None:
            reply, questions, cards, _ = result
            return reply, questions, cards, places_descriptions
        
        return None

    def _generate_place_descriptions(self, places: list[PlaceDTO], language: str) -> dict[str, str]:
        """Generate expert descriptions for each place using Gemini."""
        descriptions: dict[str, str] = {}
        
        if self._gemini_client is None:
            return descriptions
        
        for place in places:
            try:
                prompt = (
                    f"Vous êtes un expert en tourisme et culture locale.\n"
                    f"Décrivez ce lieu de manière captivante, d'expert local, en {language}.\n\n"
                    f"Lieu: {place.name}\n"
                    f"Adresse: {place.address}\n"
                    f"Types: {', '.join(place.types)}\n"
                    f"Note: {place.rating}/5" if place.rating else ""
                    f"\n\nDescription actuelle Google Maps:\n{place.description}\n\n"
                    f"Générez une description courte (15-25 mots) qui évoque l'atmosphère, l'expérience unique, "
                    f"pourquoi ce lieu est spécial. Soyez vivant, captivant, pas générique."
                )
                
                completion = self._gemini_client.chat.completions.create(
                    model=settings.gemini_model,
                    temperature=0.6,
                    max_completion_tokens=100,
                    messages=[
                        {"role": "user", "content": prompt},
                    ],
                )
                
                description = completion.choices[0].message.content or ""
                description = description.strip()
                if description and len(description) > 5:
                    descriptions[place.name] = description
            except Exception:
                # Fallback silently if generation fails
                continue
        
        return descriptions

    def _build_model_response_for_question(
        self,
        query: str,
        analysis: QueryAnalysisDTO,
    ) -> tuple[str | None, list[str], list[GuideCardDTO], dict[str, str]] | None:
        payload = {
            "mode": "general_question",
            "user_query": query,
            "detected_language": analysis.detected_language,
            "city": analysis.city,
            "category": analysis.category,
            "preferences": analysis.preferences or [],
        }
        return self._complete_response(payload, analysis)

    def _complete_response(
        self,
        payload: dict[str, Any],
        analysis: QueryAnalysisDTO,
    ) -> tuple[str | None, list[str], list[GuideCardDTO], dict[str, str]] | None:
        is_itinerary = payload.get("mode") == "itinerary_plan"
        clients: list[tuple[Any, str]] = []

        # Gemini writes the final narrative first; Groq remains the fallback.
        if self._gemini_client is not None:
            clients.append((self._gemini_client, settings.gemini_model))
        if self._groq_client is not None:
            clients.append((self._groq_client, settings.groq_model))

        if not clients:
            return None

        max_tokens = 1500 if is_itinerary else 1200
        temperature = 0.55 if is_itinerary else 0.45

        for client, model_name in clients:
            try:
                completion = client.chat.completions.create(
                    model=model_name,
                    temperature=temperature,
                    max_completion_tokens=max_tokens,
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
                continue

            raw_content = completion.choices[0].message.content or "{}"
            data = self._safe_json_parse(raw_content)
            if not data:
                continue

            assistant_reply = data.get("assistant_reply")
            if not isinstance(assistant_reply, str):
                continue

            cleaned_reply = assistant_reply.strip()
            if not cleaned_reply:
                continue

            suggested_questions = self._clean_suggested_questions(
                data.get("suggested_questions"),
                analysis,
            )

            places_descriptions = data.get("places_descriptions") or {}
            if not isinstance(places_descriptions, dict):
                places_descriptions = {}

            return cleaned_reply, suggested_questions, [], places_descriptions

        return None

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
    ) -> tuple[str | None, list[str], list[GuideCardDTO], dict[str, str]] | None:
        normalized_query = self._normalize_text(query)
        language = analysis.detected_language

        if self._looks_like_itinerary_request(normalized_query):
            return self._build_itinerary_reply(language, analysis.city, places)

        if self._looks_like_family_city_request(normalized_query):
            return self._build_family_city_reply(language)

        if self._looks_like_city_photo_request(normalized_query):
            return self._build_city_photo_reply(language)

        if self._looks_like_best_season_request(normalized_query):
            return self._build_best_season_reply(language)

        if self._looks_like_budget_request(normalized_query):
            return self._build_budget_travel_reply(language)

        if places:
            return None

        if self._contains_any_term(normalized_query, _ROMANTIC_TERMS) and self._contains_any_term(
            normalized_query, _SUNSET_TERMS
        ):
            return self._build_romantic_sunset_reply(language, analysis.city)

        if self._contains_any_term(normalized_query, _PHOTO_TERMS):
            return self._build_photo_spot_reply(language, analysis.city)

        if self._contains_any_term(normalized_query, _FAMILY_TERMS):
            return self._build_family_outing_reply(language, analysis.city)

        return None

    def _looks_like_family_city_request(self, normalized_query: str) -> bool:
        has_city_term = self._contains_any_term(normalized_query, _CITY_TERMS)
        has_family_term = self._contains_any_term(normalized_query, _FAMILY_TERMS)
        has_place_search = self._extract_category(normalized_query) is not None
        if has_place_search:
            return False
        return has_city_term and has_family_term

    def _looks_like_best_season_request(self, normalized_query: str) -> bool:
        return self._contains_any_term(normalized_query, _BEST_SEASON_TERMS)

    def _looks_like_budget_request(self, normalized_query: str) -> bool:
        return self._contains_any_term(normalized_query, _BUDGET_TERMS)

    def _extract_category(self, normalized_query: str) -> str | None:
        from app.llm.analyzer import _CATEGORY_TERMS
        for category, terms in _CATEGORY_TERMS.items():
            if any(self._contains_term(normalized_query, t) for t in terms):
                return category
        return None

    def _looks_like_itinerary_request(self, normalized_query: str) -> bool:
        return any(self._contains_term(normalized_query, term) for term in _ITINERARY_TERMS)

    def _build_itinerary_reply(
        self,
        language: str,
        city: str | None,
        places: list[PlaceDTO],
    ) -> tuple[str, list[str], list[GuideCardDTO], dict[str, str]]:
        city_segment = f" a {city}" if city and language not in {"en"} else (f" in {city}" if city else "")

        if not places:
            if language == "en":
                return (
                    "I can build a simple itinerary, but I need a city or your location (near me).",
                    ["Plan a day in Marrakech", "Find places near me", "Romantic sunset spots near me"],
                    [],
                    {},
                )
            if language == "darija":
                return (
                    "N9dar ndir lik programme, walakin khassni mdina wla position dyalk (qrib menni).",
                    ["Dir lia programme f Marrakech", "Qelleb qrib menni", "Blays romantique lghorob chams qrib menni"],
                    [],
                    {},
                )
            return (
                "Je peux te faire un programme, mais il me faut une ville ou ta position (pres de moi).",
                ["Fais-moi un programme a Marrakech", "Cherche pres de moi", "Sortie romantique pres de moi"],
                [],
                {},
            )

        selected = places[:5]
        slots = (
            _DEFAULT_ITINERARY_SLOTS_EN
            if language == "en"
            else (_DEFAULT_ITINERARY_SLOTS_DARIJA if language == "darija" else _DEFAULT_ITINERARY_SLOTS_FR)
        )

        cards: list[GuideCardDTO] = []
        for idx, place in enumerate(selected):
            time_slot = slots[min(idx, len(slots) - 1)]
            duration = self._estimate_duration_minutes(place)
            budget_min, budget_max = self._estimate_budget_mad(place, language)

            desc_parts: list[str] = []
            if place.description:
                desc_parts.append(place.description)
            if place.address:
                if language == "en":
                    desc_parts.append(f"Address: {place.address}.")
                elif language == "darija":
                    desc_parts.append(f"L3onwan: {place.address}.")
                else:
                    desc_parts.append(f"Adresse: {place.address}.")

            cards.append(
                GuideCardDTO(
                    title=place.name,
                    description=" ".join(part.strip() for part in desc_parts if part and part.strip()).strip()
                    or (place.address or place.name),
                    query=place.name,
                    time_slot=time_slot,
                    duration_minutes=duration,
                    budget_min_mad=budget_min,
                    budget_max_mad=budget_max,
                )
            )

        model_response = self._build_model_response_for_itinerary(language, city, cards)
        if model_response is not None:
            assistant_reply, suggested_questions, _, _ = model_response
            return assistant_reply, suggested_questions, cards, {}

        # Hardcoded immersive itineraries for specific cities/languages
        _HARDCODED: dict[tuple[str, str], str] = {
            ("rabat", "fr"): _RABAT_ITINERARY_FR,
            ("rabat", "en"): _RABAT_ITINERARY_EN,
            ("rabat", "darija"): _RABAT_ITINERARY_DARIJA,
            ("marrakech", "fr"): _MARRAKECH_ITINERARY_FR,
            ("marrakech", "en"): _MARRAKECH_ITINERARY_EN,
            ("fes", "fr"): _FEZ_ITINERARY_FR,
            ("fez", "fr"): _FEZ_ITINERARY_FR,
            ("fez", "en"): _FEZ_ITINERARY_FR,
        }
        if city:
            hardcoded_text = _HARDCODED.get((city.lower(), language))
            if hardcoded_text:
                if language == "en":
                    suggested_questions = [
                        "Add more cultural spots",
                        "Make it budget-friendly",
                        "Plan a romantic evening",
                    ]
                elif language == "darija":
                    suggested_questions = [
                        "Zid lia blasat thaqafiya",
                        "Khliha rkhisa",
                        "Dir programme romantique",
                    ]
                else:
                    suggested_questions = [
                        "Ajoute des lieux culturels",
                        "Fais un programme moins cher",
                        "Plan pour le coucher de soleil",
                    ]
                return hardcoded_text, suggested_questions, cards, {}

        # Fallback (no LLM available)
        reply = self._format_itinerary_fallback_reply(language, city_segment, cards)
        if language == "en":
            questions = ["Make it cheaper", "Swap one stop for a museum", "Build a romantic plan near me"]
        elif language == "darija":
            questions = ["Bghito rkhis", "Bddl chi blasa b mat7af", "Dir programme romantique qrib menni"]
        else:
            questions = ["Fais-le moins cher", "Remplace une etape par un musee", "Programme romantique pres de moi"]

        return reply, questions, cards, {}

    def _format_itinerary_fallback_reply(
        self,
        language: str,
        city_segment: str,
        cards: list[GuideCardDTO],
    ) -> str:
        # Plain-text (no markdown): structured itinerary with per-step details.
        total_min = sum(c.budget_min_mad or 0 for c in cards)
        total_max = sum(c.budget_max_mad or 0 for c in cards)
        total_duration = sum(c.duration_minutes or 0 for c in cards)

        if language == "en":
            header = (
                f"Here is a day plan{city_segment}.\n"
                f"Total: ~{total_duration} min, {total_min}-{total_max} MAD per person (approx).\n"
            )
            labels = {
                "address": "Address",
                "idea": "Idea",
                "duration": "Duration",
                "budget": "Budget",
                "tip": "Tip",
            }
        elif language == "darija":
            header = (
                f"Hada programme{city_segment}.\n"
                f"Total: ~{total_duration} min, {total_min}-{total_max} MAD لكل واحد (ta9riban).\n"
            )
            labels = {
                "address": "L3onwan",
                "idea": "Fekra",
                "duration": "Modda",
                "budget": "Budget",
                "tip": "Nsi7a",
            }
        else:
            header = (
                f"Voici un programme{city_segment}.\n"
                f"Total: ~{total_duration} min, {total_min}-{total_max} MAD par personne (approx).\n"
            )
            labels = {
                "address": "Adresse",
                "idea": "Idée",
                "duration": "Durée",
                "budget": "Budget",
                "tip": "Astuce",
            }

        grouped: dict[str, list[GuideCardDTO]] = {}
        order: list[str] = []
        for c in cards:
            slot = (c.time_slot or "").strip() or ("Etape" if language != "en" else "Step")
            if slot not in grouped:
                grouped[slot] = []
                order.append(slot)
            grouped[slot].append(c)

        lines: list[str] = [header.rstrip()]
        for slot in order:
            lines.append("")
            lines.append(f"{slot}:")
            for idx, c in enumerate(grouped[slot], start=1):
                why = (c.description or "").strip()
                duration = f"~{c.duration_minutes} min" if c.duration_minutes else ""
                budget = (
                    f"{c.budget_min_mad}-{c.budget_max_mad} MAD / pers (approx)"
                    if c.budget_min_mad is not None and c.budget_max_mad is not None
                    else ""
                )
                idea = self._build_generic_itinerary_idea(language, c)
                tip = self._build_generic_itinerary_tip(language, c)

                lines.append(f"{idx}) {c.title} — {why or (c.title or '').strip()}")
                if c.query and c.query != c.title:
                    # keep it short; query is mostly for UI action
                    pass
                if c.description and c.description != why:
                    pass
                if c.description and why and why != c.description:
                    pass
                if c.description and not why:
                    pass
                if c.description and why:
                    pass
                if c.query:
                    pass

                # We intentionally do not show coordinates here (not available in guide cards).
                if c.description and not why:
                    pass

                # Address is embedded inside description sometimes; keep single "Adresse" line only if we detect it.
                # In this backend, the description already contains "Adresse: ...", so we avoid duplicating it.
                # We still expose idea/duration/budget/tip consistently.
                if idea:
                    lines.append(f"   {labels['idea']}: {idea}")
                if duration:
                    lines.append(f"   {labels['duration']}: {duration}")
                if budget:
                    lines.append(f"   {labels['budget']}: {budget}")
                if tip:
                    lines.append(f"   {labels['tip']}: {tip}")

        return "\n".join(lines).strip()

    def _build_generic_itinerary_idea(self, language: str, card: GuideCardDTO) -> str:
        title = (card.title or "").strip()
        desc = (card.description or "").lower()
        if language == "en":
            if "museum" in desc or "musee" in desc or "mat7af" in desc:
                return "Take your time, focus on 2–3 sections you like, and grab a few photos."
            if "restaurant" in desc:
                return "Choose one signature dish, share a side, and keep room for a later snack."
            if "corniche" in desc or "view" in desc or "vue" in desc:
                return "Walk slowly, stop for photos, and enjoy the golden hour."
            return f"Enjoy {title} at a relaxed pace and take a few good stops."
        if language == "darija":
            if "museum" in desc or "musee" in desc or "mat7af" in desc:
                return "Dkhoul b rwiya, khtar 2-3 qsmat li 3jbok, w ddir chi tsawer."
            if "restaurant" in desc:
                return "Khtar plat principal, qssm chi haja, w khlli blas l snack mn b3d."
            if "corniche" in desc or "vue" in desc or "view" in desc:
                return "Tmcha b shwiya, w9ef l tsawer, w tmt3 b golden hour."
            return f"Tmta3 b {title} b calma w ddir waqfat zwinin."
        # fr
        if "museum" in desc or "musee" in desc or "mat7af" in desc:
            return "Prenez votre temps, ciblez 2–3 sections qui vous plaisent, et faites quelques photos."
        if "restaurant" in desc:
            return "Choisissez un plat signature, partagez un accompagnement, et gardez une place pour un snack plus tard."
        if "corniche" in desc or "vue" in desc or "view" in desc:
            return "Balade tranquille, pauses photo, et profitez de la golden hour."
        return f"Profitez de {title} a votre rythme, avec quelques pauses sympa."

    def _build_generic_itinerary_tip(self, language: str, card: GuideCardDTO) -> str:
        duration = card.duration_minutes or 0
        if language == "en":
            if duration >= 75:
                return "Start a bit earlier to avoid crowds, and keep 10–15 min buffer for moving around."
            return "Keep 10 min buffer for walking and small detours."
        if language == "darija":
            if duration >= 75:
                return "Bda b bkri shwiya bach tjnnb z7am, w khlli 10-15 dqiqa buffer l tmchi."
            return "Khlّي 10 dqiqa buffer l tmchi w detours sghar."
        # fr
        if duration >= 75:
            return "Commencez un peu plus tot pour eviter la foule, et gardez 10–15 min de marge entre les etapes."
        return "Gardez ~10 min de marge pour marcher et faire de petits detours."

    def _build_model_response_for_itinerary(
        self,
        language: str,
        city: str | None,
        cards: list[GuideCardDTO],
    ) -> tuple[str | None, list[str], list[GuideCardDTO]] | None:
        payload = {
            "mode": "itinerary_plan",
            "detected_language": language,
            "city": city,
            "steps": [
                {
                    "time_slot": c.time_slot,
                    "name": c.title,
                    "description": c.description,
                    "duration_minutes": c.duration_minutes,
                    "budget_min_mad": c.budget_min_mad,
                    "budget_max_mad": c.budget_max_mad,
                }
                for c in cards
            ],
        }
        # Reuse existing completion pipe (returns assistant_reply + suggested_questions)
        return self._complete_response(payload, QueryAnalysisDTO(detected_language=language))

    def _estimate_duration_minutes(self, place: PlaceDTO) -> int:
        types = [t.lower() for t in (place.types or []) if isinstance(t, str)]
        if "museum" in types:
            return 90
        if "park" in types:
            return 60
        if "restaurant" in types:
            return 75
        if "cafe" in types:
            return 45
        if "tourist_attraction" in types:
            return 60
        if "lodging" in types:
            return 30
        return 60

    def _estimate_budget_mad(self, place: PlaceDTO, language: str) -> tuple[int, int]:
        types = [t.lower() for t in (place.types or []) if isinstance(t, str)]
        desc = (place.description or "").lower()

        if any(t in types for t in ("park", "tourist_attraction")) and "restaurant" not in types and "cafe" not in types:
            return (0, 50)

        if "budget-friendly" in desc or "pas cher" in desc or "plutot pas cher" in desc or "rkhis" in desc:
            return (40, 120)
        if "mid-range" in desc or "gamme moyenne" in desc or "moutawassit" in desc:
            return (120, 250)
        if "upscale" in desc or "haut de gamme" in desc or "ghali" in desc or "premium" in desc:
            return (250, 600)

        if "cafe" in types:
            return (25, 80)
        if "restaurant" in types:
            return (80, 250)

        return (50, 200)

    def _build_city_photo_reply(self, language: str) -> tuple[str, list[str], list[GuideCardDTO], dict[str, str]]:
        if language == "en":
            return (
                "Morocco has some of the most photogenic cities in the world — the choice depends on your style. "
                "Fez is unmatched for heritage and detail photography: the medieval medina, the Chouara tanneries "
                "seen from above in the morning light, the carved stucco of Bou Inania medersa. "
                "Chefchaouen is a dream for color and calm compositions — blue-washed alleys, soft mountain light, "
                "and intimate portraits of daily life. "
                "Marrakech delivers rich ochre colors, dramatic architecture, and lively street scenes at Jemaa el-Fna. "
                "Essaouira offers white ramparts against an Atlantic sky, fishing boats, and golden hour over the ocean. "
                "Aït-Benhaddou is cinematic — a ksar fortress in the pre-Saharan desert that has starred in dozens of films. "
                "Tangier is underrated: the old medina, the strait, and the mix of cultures create a unique visual story. "
                "Tell me your style (architecture, portraits, landscapes, street life) and I will choose the perfect city.",
                [
                    "Best city for street photography in Morocco",
                    "Find photo spots in Chefchaouen",
                    "Sunrise spots in Fez medina",
                ],
                self._build_city_photo_cards(language),
                {},
            )

        if language == "darija":
            return (
                "Lmaghrib fih mdun photogeniqin bzaf — lkhiyar kaysewwel 3la style dyalk. "
                "Fes la misil fihà l heritage w tafasil: lmedina lqadima, tanneries Chouara mn fo9 f sbah, "
                "w nqoush Bou Inania. Chefchaouen 7lma l alwan w calme: zz9aq zar9in, daw hani dial jibal, w portraits zwinin. "
                "Marrakech 3ndhà alwan s7rawiya, 3mara jmila, w jaw Jemaa el-Fna. "
                "Essaouira kaydir ssour lbyad m3a ssama l'atlantique, bwatim dial sayadin, w golden hour 3la lbaher. "
                "Aït-Benhaddou cinématographique — ksar ssahra dial lfilam lkibra. "
                "Tanger ma3rouf b7al ma khsso — lmedina l9adima, lmdiq, w mix dyal t9afat. "
                "Golli lia style dyalk w n9tar7 lik l mdina li thyyem.",
                [
                    "Ahsan mdina l street photo f lmaghrib",
                    "Spots photo f Chefchaouen",
                    "Mawdi sunrise f medina Fes",
                ],
                self._build_city_photo_cards(language),
                {},
            )

        return (
            "Le Maroc compte parmi les destinations les plus photogeniques du monde — le choix depend de votre style. "
            "Fes est imbattable pour la photographie de patrimoine et de detail : la medina medievale, "
            "les tanneries Chouara vues d'en haut le matin, les sculptures en stuc de la medersa Bou Inania. "
            "Chefchaouen est un reve pour les compositions colorees et calmes — ruelles bleues, lumiere douce de montagne, "
            "et portraits intimistes de la vie quotidienne. "
            "Marrakech offre des ocres chauds, une architecture dramatique et les scenes de rue vivantes de Jemaa el-Fna. "
            "Essaouira propose les remparts blancs sur le ciel atlantique, les bateaux de peche et la golden hour sur l'ocean. "
            "Aït-Benhaddou est cinematographique — un ksar de pre-Sahara qui a servi de decor a des dizaines de films. "
            "Tanger est sous-estimee : la vieille medina, le detroit de Gibraltar et le melange des cultures creent un recit visuel unique. "
            "Dis-moi ton style (architecture, portrait, paysage, vie de rue) et je choisis la ville ideale.",
            [
                "Meilleure ville pour la street photo au Maroc ?",
                "Trouve des spots photo a Chefchaouen",
                "Spots pour le lever de soleil dans la medina de Fes",
            ],
            self._build_city_photo_cards(language),
            {},
        )

    def _build_romantic_sunset_reply(
        self,
        language: str,
        city: str | None,
    ) -> tuple[str, list[str], list[GuideCardDTO], dict[str, str]]:
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
                {},
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
                {},
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
            {},
        )

    def _build_photo_spot_reply(
        self,
        language: str,
        city: str | None,
    ) -> tuple[str, list[str], list[GuideCardDTO], dict[str, str]]:
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
                {},
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
                {},
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
            {},
        )

    def _build_family_city_reply(self, language: str) -> tuple[str, list[str], list[GuideCardDTO], dict[str, str]]:
        if language == "en":
            return (
                "For a family trip in Morocco, the best cities depend on your children's age and what you enjoy together. "
                "Agadir tops the list for young children: a 9-km protected beach, calm water, a waterpark (Oasiria), "
                "and a family-friendly promenade. Marrakech is magical for all ages — the calèche rides around the medina, "
                "the Majorelle and Menara gardens, and the spectacle of Jemaa el-Fna square. Rabat surprises with its zoo, "
                "the Chellah gardens, and safe, uncrowded beaches at Plage de Rabat. Ifrane, in the Middle Atlas, is perfect "
                "for nature lovers: cedar forests, monkeys, a turquoise lake, and ski slopes in winter. "
                "Essaouira is ideal for older children who enjoy history and the ocean atmosphere. "
                "Tell me the age range and I will narrow it down.",
                [
                    "Family activities in Marrakech",
                    "Agadir family beach",
                    "Where to take kids in Rabat",
                ],
                self._build_family_city_cards(language),
                {},
            )

        if language == "darija":
            return (
                "Ila bghiti sortie familiale f lmaghrib, kol mdina 3ndha shi m3rof. "
                "Agadir hiya l khiyar lol l drari sghir: plage 9 km mahmiiya, may hadi, parc aquatique Oasiria, "
                "w corniche mzyana l familia. Marrakech katsahhel l kol sin: calèche f lmedina, jnane Majorelle w Ménara, "
                "w jaw Jemaa el-Fna li kayshdd ndar l wlad. Rbat 3ndhom zoo mzyan, jnane Chellah, w plajet hadiya. "
                "Ifrane f Atlas mzyana l tabi3a: ghaba d arz, qroud, buhira zarqa, w thalj f chta. "
                "3tini 3omr drari w khassiyatek w nwrilik shi mzyan.",
                [
                    "Aktivitat familia f Marrakech",
                    "Plage familia f Agadir",
                    "Fin nmchi m3a drari f Rbat",
                ],
                self._build_family_city_cards(language),
                {},
            )

        return (
            "Pour une sortie familiale au Maroc, le choix de la ville depend de l'age des enfants et de vos envies. "
            "Agadir est imbattable pour les jeunes enfants : plage securisee de 9 km, eaux calmes, parc aquatique Oasiria, "
            "et promenade familiale tres agreable. Marrakech est magique pour tous les ages — les calèches dans la medina, "
            "les jardins Majorelle et Menara, et le spectacle de la place Jemaa el-Fna captivent petits et grands. "
            "Rabat surprend avec son zoo bien entretenu, les jardins de Chellah et des plages calmes. "
            "Ifrane, dans le Moyen-Atlas, est parfaite pour la nature : forets de cedres, singes barbares, lac turquoise "
            "et pistes de ski en hiver. Essaouira convient mieux aux enfants plus grands qui apprecient l'histoire et l'ocean. "
            "Dis-moi l'age des enfants et le type d'activite souhaite, je te recommande la meilleure option.",
            [
                "Activites pour enfants a Marrakech",
                "Plage familiale a Agadir",
                "Que faire avec des enfants a Rabat",
            ],
            self._build_family_city_cards(language),
            {},
        )

    def _build_family_outing_reply(
        self,
        language: str,
        city: str | None,
    ) -> tuple[str, list[str], list[GuideCardDTO], dict[str, str]]:
        city_segment = f" a {city}" if city and language == "fr" else (f" in {city}" if city and language == "en" else (f" f {city}" if city else ""))

        if language == "en":
            if city:
                reply = (
                    f"For a family outing{city_segment}, I would look for parks, gardens, beaches, "
                    "child-friendly museums, and outdoor attractions. Share your location or let me search "
                    "and I will pick the best spots."
                )
            else:
                reply = (
                    "For a family outing in Morocco, the best options are parks, calm beaches, zoos, gardens, "
                    "and family-friendly attractions. Give me a city or your location and I will find specific spots."
                )
            return (
                reply,
                [
                    f"Find family parks{' in ' + city if city else ' near me'}",
                    f"Calm beaches for families{' in ' + city if city else ' in Agadir'}",
                    "Family activities in Marrakech",
                ],
                self._build_family_outing_cards(language, city),
                {},
            )

        if language == "darija":
            if city:
                reply = (
                    f"Bash dir sortie familiale{city_segment}, qelleb 3la hdaye9, jnanat, plajet hadiya, "
                    "mat7af l drari, w mawadi kharjiya mzyanin l familia. 3tini position dyalk w nqelleb lik."
                )
            else:
                reply = (
                    "L sortie familiale f lmaghrib, ahsan khiyarat hom hdaye9, plajet hadiya, zoo, jnanat, "
                    "w mawadi familiya. 3tini smit lmdina wla position dyalk w nqelleb lik."
                )
            return (
                reply,
                [
                    f"Qelleb hdaye9 familiya{' f ' + city if city else ' qrib menni'}",
                    f"Plajet hadiya{' f ' + city if city else ' f Agadir'}",
                    "Aktivitat familia f Marrakech",
                ],
                self._build_family_outing_cards(language, city),
                {},
            )

        if city:
            reply = (
                f"Pour une sortie familiale{city_segment}, je viserais les parcs, jardins, plages calmes, "
                "musees interactifs et attractions en plein air. Donne-moi ta position ou laisse-moi chercher "
                "et je te selectionne les meilleurs endroits pour toute la famille."
            )
        else:
            reply = (
                "Pour une sortie familiale au Maroc, les meilleures options sont les parcs, les plages calmes, "
                "les zoos, les jardins et les attractions en plein air. "
                "Donne-moi une ville ou ta position et je trouve des endroits precis."
            )
        return (
            reply,
            [
                f"Parcs familiaux{' a ' + city if city else ' pres de moi'}",
                f"Plages calmes pour famille{' a ' + city if city else ' a Agadir'}",
                "Activites familles a Marrakech",
            ],
            self._build_family_outing_cards(language, city),
            {},
        )

    def _build_best_season_reply(self, language: str) -> tuple[str, list[str], list[GuideCardDTO], dict[str, str]]:
        if language == "en":
            return (
                "Spring (March to May) and autumn (September to November) are the ideal seasons to visit Morocco. "
                "Temperatures are pleasant across the country, landscapes are lush in spring, and the light is beautiful in autumn. "
                "Summer (July-August) is very hot inland — Fez and Marrakech can reach 42-45°C — but the Atlantic coast "
                "(Essaouira, Agadir) stays breezy and comfortable. Winter is mild on the coast but cold in the mountains, "
                "with snow on the Toubkal and skiing at Ifrane. Ramadan is a unique cultural experience — the nighttime "
                "atmosphere in medinas is exceptional — but some restaurants close during the day. "
                "For the Sahara desert, November to March is perfect (warm days, cool nights). "
                "For the mountains and hiking, June or September are ideal.",
                [
                    "Best city to visit in spring",
                    "What to do in Morocco in summer",
                    "Plan a desert trip in winter",
                ],
                [],
                {},
            )

        if language == "darija":
            return (
                "Rbi3 (mars-mai) w khrib (septembre-novembre) homa ahsan wa9t bash tzur lmaghrib. "
                "F rbi3, lhawa mzyan w tabiya khadra w daw jwab. F khrib, daba mzyan bzaf. "
                "F sayf (yulyu-ghucht), Fes w Marrakech kaywslu 42-45 deraja — skhoun bzaf. "
                "Walakin ssahil latlantiki (Essaouira, Agadir) barid w mri7. "
                "F chta, ssahil dafi2 walakin ljibal barda w kayn talj 3la Toubkal, w ski f Ifrane. "
                "Ramadan, jwa lil f lmdan exceptional walakin chi mat3am msakerin f nhar. "
                "L ssahra, November-mars ahsan wa9t.",
                [
                    "Ashan mdina f rbi3",
                    "Ash ndiru f lmaghrib f sayf",
                    "Programme ssahra f chta",
                ],
                [],
                {},
            )

        return (
            "Le printemps (mars-mai) et l'automne (septembre-novembre) sont les meilleures periodes pour visiter le Maroc. "
            "Les temperatures sont agreables partout, les paysages verdissent au printemps et les couleurs sont riches en automne. "
            "L'ete (juillet-aout) est tres chaud dans les villes interieures — Fes et Marrakech peuvent atteindre 42-45°C — "
            "mais la cote atlantique (Essaouira, Agadir) reste venteuse et confortable. "
            "L'hiver est doux sur la cote mais froid en montagne, avec de la neige sur le Toubkal et du ski a Ifrane. "
            "Le Ramadan est une experience culturelle unique — l'atmosphere nocturne dans les medinas est exceptionnelle — "
            "mais certains restaurants ferment en journee. Pour le desert du Sahara, novembre a mars est ideal "
            "(journees chaudes, nuits fraiches). Pour la montagne et la randonnee, juin ou septembre sont parfaits.",
            [
                "Quelle ville visiter au printemps ?",
                "Que faire au Maroc en ete ?",
                "Planifier un voyage dans le desert en hiver",
            ],
            [],
            {},
        )

    def _build_budget_travel_reply(self, language: str) -> tuple[str, list[str], list[GuideCardDTO], dict[str, str]]:
        if language == "en":
            return (
                "Morocco is one of the most affordable destinations in the Mediterranean and North Africa. "
                "A local meal (sandwich, harira, brochettes) costs 20-60 MAD. A sit-down restaurant meal is 80-200 MAD. "
                "Budget guesthouses (funduqs, small riads) start at 150-300 MAD per night. "
                "Intercity buses (CTM/Supratours) are very affordable: Casablanca to Marrakech is around 90-120 MAD. "
                "Trains are comfortable and not expensive. "
                "Taxis within cities: always negotiate or insist on the meter. "
                "The most budget-friendly cities: Fez and Meknes are less touristic than Marrakech, so prices are lower. "
                "Avoid the medina tourist traps and eat where locals eat — the quality is often better.",
                [
                    "Cheap restaurants in Fez",
                    "Budget riads in Marrakech",
                    "How to get from Casablanca to Marrakech cheaply",
                ],
                [],
                {},
            )

        if language == "darija":
            return (
                "Lmaghrib wa7d men arzas dyur f lmaditerranee. "
                "Makla m7alliya (sandwich, harira, brochettes) kaykhlef 20-60 MAD. "
                "Restaurant 3adi 80-200 MAD. Riad sghir wla funduq mn 150-300 MAD flila. "
                "Bus intercite CTM/Supratours rkhisin: Casablanca l Marrakech 90-120 MAD. "
                "Tren mri7 w la ghali. Petit taxi: dima 3awed 3la 3addad wla tfawet thaman qbel. "
                "Ashan mdun budget: Fes w Meknes akhal l siya7a mn Marrakech = taman rkhis. "
                "Kul fin kayaklu nas lmaghribin — juda ghir a7san.",
                [
                    "Mat3am rkhis f Fes",
                    "Riad rkhis f Marrakech",
                    "Kif nmchi mn Casablanca l Marrakech b taman rkhis",
                ],
                [],
                {},
            )

        return (
            "Le Maroc est l'une des destinations les plus accessibles du bassin mediterraneen. "
            "Un repas local (sandwich, harira, brochettes) coute 20-60 MAD. Un restaurant assis 80-200 MAD. "
            "Les petits gites et funduqs commencent a 150-300 MAD la nuit. "
            "Les bus intercites CTM/Supratours sont tres abordables : Casablanca-Marrakech tourne autour de 90-120 MAD. "
            "Le train est confortable et raisonnable. "
            "Les petits taxis en ville : insiste toujours sur le compteur ou negocie avant de monter. "
            "Les villes les plus economiques : Fes et Meknes, moins touristiques que Marrakech, ont des prix plus bas. "
            "Mange la ou mangent les locaux — c'est souvent moins cher et bien meilleur.",
            [
                "Restaurants pas chers a Fes",
                "Riads abordables a Marrakech",
                "Comment aller de Casablanca a Marrakech pas cher",
            ],
            [],
            {},
        )

    def _build_family_city_cards(self, language: str) -> list[GuideCardDTO]:
        if language == "en":
            return [
                self._card("Agadir", "9-km protected beach, calm water, waterpark Oasiria — top pick for young children.", "family activities in Agadir"),
                self._card("Marrakech", "Calèche rides, Majorelle garden, Jemaa el-Fna spectacle — magical for all ages.", "family activities in Marrakech"),
                self._card("Rabat", "Well-maintained zoo, Chellah gardens, calm beaches — perfect for families on a budget.", "family activities in Rabat"),
                self._card("Ifrane", "Cedar forest, monkeys, turquoise lake, ski slopes — ideal for nature-loving families.", "family activities in Ifrane"),
            ]
        if language == "darija":
            return [
                self._card("Agadir", "Plage 9 km mahmiiya, may hadi, Oasiria — ahsan khiyar l drari sghir.", "aktivitat familia f Agadir"),
                self._card("Marrakech", "Calèche, jnane Majorelle, Jemaa el-Fna — mzyan l kol sin.", "aktivitat familia f Marrakech"),
                self._card("Rbat", "Zoo mzyan, jnane Chellah, plajet hadiya — mzyan l familia b budget.", "aktivitat familia f Rbat"),
                self._card("Ifrane", "Ghaba d arz, qroud, buhira zarqa, thalj — mzyan l wlad li kay7bu tabi3a.", "aktivitat familia f Ifrane"),
            ]
        return [
            self._card("Agadir", "Plage securisee de 9 km, eaux calmes, parc aquatique Oasiria — idéal pour les jeunes enfants.", "activites famille a Agadir"),
            self._card("Marrakech", "Calèches, jardin Majorelle, place Jemaa el-Fna — magique pour tous les ages.", "activites famille a Marrakech"),
            self._card("Rabat", "Zoo bien entretenu, jardins de Chellah, plages calmes — parfait pour les families avec budget.", "activites famille a Rabat"),
            self._card("Ifrane", "Foret de cedres, singes barbares, lac turquoise, ski — ideal pour les families qui aiment la nature.", "activites famille a Ifrane"),
        ]

    def _build_family_outing_cards(self, language: str, city: str | None) -> list[GuideCardDTO]:
        default_city = city or "Marrakech"
        if language == "en":
            return [
                self._card("Park / Garden", "Open-air space, shade and greenery for children to run and play freely.", f"family park in {default_city}"),
                self._card("Calm beach", "Safe, shallow water ideal for young children and relaxed family swimming.", f"calm beach for families in {default_city}"),
                self._card("Museum", "Interactive exhibits and cultural immersion — great for curious older children.", f"family museum in {default_city}"),
                self._card("Outdoor attraction", "Zoo, botanical garden or nature trail — keeps kids engaged for hours.", f"outdoor attraction in {default_city}"),
            ]
        if language == "darija":
            return [
                self._card("Hdiya / Jnina", "Mkan mftuh, dhal w khadriya bach drari yel3bu.", f"hdiya familia f {default_city}"),
                self._card("Plage hadya", "May hadi w 9sirr — mzyan l drari sghir w sebha familia.", f"plage hadya familia f {default_city}"),
                self._card("Mat7af", "3arad interactif w thaqafa — mzyan l wlad li 3ndhom fiha.", f"mat7af familia f {default_city}"),
                self._card("Mawdi kharji", "Zoo, jnane botanika wla sentier tabi3i — kaybqa drari mnhmakin sa3at.", f"mawdi kharji f {default_city}"),
            ]
        return [
            self._card("Parc / Jardin", "Espace ouvert, ombre et verdure pour que les enfants puissent courir et jouer librement.", f"parc familial a {default_city}"),
            self._card("Plage calme", "Eaux peu profondes et securisees — ideal pour les jeunes enfants et la baignade en famille.", f"plage calme famille a {default_city}"),
            self._card("Musee", "Expositions interactives et immersion culturelle — excellent pour les enfants plus grands et curieux.", f"musee famille a {default_city}"),
            self._card("Attraction en plein air", "Zoo, jardin botanique ou sentier nature — tient les enfants occupes des heures.", f"attraction plein air a {default_city}"),
        ]

    def _build_city_photo_cards(self, language: str) -> list[GuideCardDTO]:
        if language == "en":
            return [
                self._card("Fez", "Medieval medina, Chouara tanneries at dawn, sculpted stucco — unmatched for heritage detail photography.", "photo spots in Fez"),
                self._card("Chefchaouen", "Blue-washed alleys, soft mountain light, calm compositions and intimate portraits.", "photo spots in Chefchaouen"),
                self._card("Marrakech", "Warm ochre tones, ornate palaces, souks, and the electric spectacle of Jemaa el-Fna at dusk.", "photo spots in Marrakech"),
                self._card("Essaouira", "White ramparts against Atlantic sky, fishing port, and cinematic golden-hour light.", "photo spots in Essaouira"),
                self._card("Aït-Benhaddou", "Pre-Saharan ksar fortress, desert light, and a dramatic cinematic landscape.", "photo spots in Ait Benhaddou"),
                self._card("Tangier", "Old medina, Gibraltar strait views, and a unique blend of African and European cultures.", "photo spots in Tangier"),
            ]

        if language == "darija":
            return [
                self._card("Fes", "Medina qadima, tanneries Chouara f sbah, nqoush Bou Inania — la misil l heritage photo.", "spots photo f Fes"),
                self._card("Chefchaouen", "Z9aq zar9in, daw hani dial jibal, tsawer calma w portraits zwinin.", "spots photo f Chefchaouen"),
                self._card("Marrakech", "Alwan s7rawiya, 9sur kbira, aswaq, w jaw Jemaa el-Fna f 3chiya.", "spots photo f Marrakech"),
                self._card("Essaouira", "Ssour lyad m3a ssama latlantique, minaء sayadin, w golden hour 3la lbaher.", "spots photo f Essaouira"),
                self._card("Aït-Benhaddou", "Ksar ssahra, daw dyal sahara, w manzar cinématographique 3ali.", "spots photo f Ait Benhaddou"),
                self._card("Tanger", "Medina l9adima, manzar 3la lmdiq, w mix tbayyin dyal t9afat.", "spots photo f Tanger"),
            ]

        return [
            self._card("Fes", "Medina medievale, tanneries Chouara a l'aube, stuc sculpte — imbattable pour le patrimoine et le detail.", "spots photo a Fes"),
            self._card("Chefchaouen", "Ruelles bleues, lumiere douce de montagne, compositions calmes et portraits intimistes.", "spots photo a Chefchaouen"),
            self._card("Marrakech", "Ocres chauds, palais ornes, souks et le spectacle electrique de Jemaa el-Fna au crepuscule.", "spots photo a Marrakech"),
            self._card("Essaouira", "Remparts blancs sur ciel atlantique, port de peche et lumiere cinematographique de golden hour.", "spots photo a Essaouira"),
            self._card("Aït-Benhaddou", "Ksar de pre-Sahara, lumiere desert et paysage dramatique tres cinematographique.", "spots photo a Ait Benhaddou"),
            self._card("Tanger", "Vieille medina, vue sur le detroit de Gibraltar et melange unique de cultures africaine et europeenne.", "spots photo a Tanger"),
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