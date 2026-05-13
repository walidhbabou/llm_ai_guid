from app.clients.google_maps_client import GoogleMapsClient
from app.dto.search_dto import PlaceDTO


def _label_from_types(types: list[str], language: str) -> str:
    if language == "en":
        if "gym" in types:
            return "Gym"
        if "spa" in types:
            return "Spa"
        if "stadium" in types:
            return "Sports venue"
        if "mosque" in types:
            return "Mosque"
        if "cafe" in types:
            return "Cafe"
        if "restaurant" in types:
            return "Restaurant"
        if "museum" in types:
            return "Museum"
        if "park" in types:
            return "Park"
        if "lodging" in types:
            return "Hotel"
        if "tourist_attraction" in types:
            return "Tourist spot"
        return "Place"

    if language == "darija":
        if "gym" in types:
            return "Salle sport"
        if "spa" in types:
            return "Spa"
        if "stadium" in types:
            return "Stade"
        if "mosque" in types:
            return "Jama3"
        if "cafe" in types:
            return "Cafe"
        if "restaurant" in types:
            return "Restaurant"
        if "museum" in types:
            return "Mat7af"
        if "park" in types:
            return "7di9a"
        if "lodging" in types:
            return "Hotel"
        if "tourist_attraction" in types:
            return "Blasa siyahia"
        return "Blasa"

    if "gym" in types:
        return "Salle de sport"
    if "spa" in types:
        return "Spa"
    if "stadium" in types:
        return "Stade"
    if "mosque" in types:
        return "Mosquee"
    if "cafe" in types:
        return "Cafe"
    if "restaurant" in types:
        return "Restaurant"
    if "museum" in types:
        return "Musee"
    if "park" in types:
        return "Parc"
    if "lodging" in types:
        return "Hotel"
    if "tourist_attraction" in types:
        return "Lieu touristique"
    return "Lieu"


def _price_label(price_level: int | None, language: str) -> str | None:
    if price_level is None:
        return None

    if language == "en":
        labels = {
            0: "budget-friendly",
            1: "budget-friendly",
            2: "mid-range",
            3: "upscale",
            4: "premium",
        }
    elif language == "darija":
        labels = {
            0: "rkhis",
            1: "rkhis",
            2: "moutawassit",
            3: "ghali",
            4: "premium",
        }
    else:
        labels = {
            0: "plutot pas cher",
            1: "plutot pas cher",
            2: "gamme moyenne",
            3: "haut de gamme",
            4: "premium",
        }
    return labels.get(price_level)


def _status_label(open_now: bool | None, language: str) -> str | None:
    if open_now is None:
        return None

    if language == "en":
        return "currently open" if open_now else "currently closed"
    if language == "darija":
        return "7al daba" if open_now else "msedoud daba"
    return "ouvert actuellement" if open_now else "ferme actuellement"


def _build_description(place: dict, language: str) -> str | None:
    editorial = None
    summary = place.get("editorial_summary")
    if isinstance(summary, dict):
        editorial = summary.get("overview")
    if isinstance(editorial, str):
        editorial = editorial.strip() or None

    place_name = (place.get("name") or "").strip()

    if language == "en":
        if editorial:
            base = editorial
        else:
            if "gym" in types:
                base = f"A well-equipped fitness spot to keep active during your stay — ideal before or after a day of sightseeing."
            elif "park" in types:
                base = f"A leafy escape in the heart of the city, perfect for a slow morning walk, a picnic, or simply breathing in fresh air away from the crowds."
            elif "museum" in types:
                base = f"A rich cultural stop where history, art, and local heritage come alive through carefully curated collections — allow yourself at least an hour."
            elif "tourist_attraction" in types or "point_of_interest" in types:
                base = f"One of the city's standout landmarks, worth visiting for its architecture, history, and the stunning photos you will take there."
            elif "restaurant" in types:
                base = f"A reliable address for a satisfying meal — locals come here for the generous portions and the warm, unpretentious atmosphere."
            elif "cafe" in types:
                base = f"A cozy spot to slow down over a good coffee or fresh juice — the kind of place where an hour disappears without noticing."
            elif "spa" in types:
                base = f"A calm retreat offering a break from the bustle of the city — hammam, massage, or just a quiet hour to yourself."
            elif "lodging" in types:
                base = f"A comfortable base for your stay, well-located and appreciated by travellers for its atmosphere and hospitality."
            else:
                base = f"A noteworthy {label.lower()} that fits naturally into your itinerary and deserves a visit."

        status_label = _status_label(open_now, language)
        price_label = _price_label(price_level, language)
        extras = ", ".join([x for x in (status_label, price_label) if x])
        if extras:
            base = f"{base} ({extras})."
        return base

    if language == "darija":
        if editorial:
            base = editorial
        else:
            if "gym" in types:
                base = "Salle sport mzyana bash t7afed 3la activite dyalk waqt siyaha — ideal 9bel wla b3d nhar d visit."
            elif "park" in types:
                base = "7di9a khdra f qelb lmdina, mzyana l tmchiya b shwiya, picnic, wla bash tekhrej mn z7am shwiya w t3mel wa9fa."
            elif "museum" in types:
                base = "Blasa thaqafiya zwina, fihà tarikh w fnoun w patrimoine — khssek t3ti 3liha sa3a m3a shi w t9der testa3mel waktek."
            elif "tourist_attraction" in types or "point_of_interest" in types:
                base = "Wa7ed l ma3alim li lazem tzor — architecture, tarikh, w tsawer zwinin t9dr tdirha hna."
            elif "restaurant" in types:
                base = "Adresse mzyana li kaykhdm — saken kayjiw hna 3la lmakla lkbira w l jaw dafi w bla takallof."
            elif "cafe" in types:
                base = "Blasa hania bash tshreb 9ahwa wla jus w terta7 — naw3 dial cafe li sa3a kaytfout bla ma t7ess."
            elif "spa" in types:
                base = "Blasa hadiya w mri7a, b3idan 3la z7am lmdina — hammam, massage, wla wa9t safi 3lik."
            elif "lodging" in types:
                base = "Base mzyana l iqametek, mertah w b location mzyan — l moussafrin kayt7snu 3la l jaw w d-diyafa."
            else:
                base = f"{label} zwina kayt7aqa tzorha w tdirha f programme dyalk."

        status_label = _status_label(open_now, language)
        price_label = _price_label(price_level, language)
        extras = ", ".join([x for x in (status_label, price_label) if x])
        if extras:
            base = f"{base} ({extras})."
        return base

    # fr
    if editorial:
        base = editorial
    else:
        if "gym" in types:
            base = "Une salle de sport bien equipee pour maintenir le rythme pendant ton sejour — ideale avant ou apres une journee de visites."
        elif "park" in types:
            base = "Un ecrin de verdure au coeur de la ville, parfait pour une balade matinale, un pique-nique improvise ou simplement souffler loin de l'agitation."
        elif "museum" in types:
            base = "Un arret culturel incontournable ou l'histoire et l'art local prennent vie — compte au moins une heure pour en profiter pleinement."
        elif "tourist_attraction" in types or "point_of_interest" in types:
            base = "L'un des sites emblematiques de la ville, a visiter pour son architecture, son histoire et les photos memorables que tu en rapporteras."
        elif "restaurant" in types:
            base = "Une adresse de confiance pour un repas satisfaisant — les locaux y viennent pour les portions genereuses et l'ambiance chaleureuse et sans chichi."
        elif "cafe" in types:
            base = "Un coin cosy pour prendre son temps autour d'un bon cafe ou d'un jus frais — le genre d'endroit ou une heure disparait sans qu'on s'en rende compte."
        elif "spa" in types:
            base = "Un havre de calme pour s'extraire du brouhaha de la ville — hammam, massage ou simplement une heure de tranquillite bien meritee."
        elif "lodging" in types:
            base = "Un point de chute agreable et bien situe, apprecie par les voyageurs pour son atmosphere et son accueil."
        else:
            base = f"Un {label.lower()} qui merite le detour et s'integre naturellement dans un programme de visite."

    status_label = _status_label(open_now, language)
    price_label = _price_label(price_level, language)
    extras = ", ".join([x for x in (status_label, price_label) if x])
    if extras:
        base = f"{base} ({extras})."
    
    return base


def map_google_place_to_dto(
    place: dict,
    google_client: GoogleMapsClient,
    *,
    language: str = "fr",
) -> PlaceDTO:
    geometry = place.get("geometry", {}).get("location", {})
    photos = place.get("photos", [])

    photo_url = None
    photo_urls: list[str] = []
    if photos:
        for item in photos[:8]:
            ref = item.get("photo_reference")
            if not ref:
                continue
            photo_urls.append(google_client.build_photo_url(ref))
        if photo_urls:
            photo_url = photo_urls[0]

    place_id = place.get("place_id", "")

    return PlaceDTO(
        name=place.get("name", ""),
        description=_build_description(place, language),
        address=place.get("formatted_address") or place.get("vicinity") or "",
        latitude=float(geometry.get("lat", 0.0)),
        longitude=float(geometry.get("lng", 0.0)),
        rating=place.get("rating"),
        types=place.get("types", []),
        photo_url=photo_url,
        photo_urls=photo_urls,
        place_id=place_id,
        google_maps_url=(
            f"https://www.google.com/maps/place/?q=place_id:{place_id}" if place_id else None
        ),
    )
