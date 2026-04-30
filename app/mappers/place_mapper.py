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
    types = [str(t).lower() for t in place.get("types", []) if isinstance(t, str)]
    label = _label_from_types(types, language)
    price_level = place.get("price_level")
    open_now = place.get("opening_hours", {}).get("open_now")
    address = place.get("formatted_address") or place.get("vicinity")
    editorial = None
    summary = place.get("editorial_summary")
    if isinstance(summary, dict):
        editorial = summary.get("overview")
    if isinstance(editorial, str):
        editorial = editorial.strip() or None

    if language == "en":
        if editorial:
            base = editorial
        else:
            if "gym" in types:
                base = "A practical spot to work out and stay active."
            elif "park" in types:
                base = "A pleasant green space for a walk, a break, or fresh air."
            elif "museum" in types:
                base = "A cultural stop to discover local history, art, or exhibitions."
            elif "tourist_attraction" in types or "point_of_interest" in types:
                base = "A popular stop to explore and take photos."
            elif "restaurant" in types:
                base = "A good place to eat and take a relaxed break."
            elif "cafe" in types:
                base = "A nice spot for coffee, a snack, or a short pause."
            elif "spa" in types:
                base = "A calm place to relax and unwind."
            else:
                base = f"{label} worth checking out during your outing."

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
                base = "Blasa mzyana باش تدير sport w t7afed 3la l'activité."
            elif "park" in types:
                base = "7di9a zwina l tmchiya, l hdou2, w chi wa9fa khfifa."
            elif "museum" in types:
                base = "Mat7af / blasa thaqafiya باش t3ref 3la t-tarikh w l'art."
            elif "tourist_attraction" in types or "point_of_interest" in types:
                base = "Blasa ma3roufa l t-dwira w tsawer."
            elif "restaurant" in types:
                base = "Blasa mzyana باش takol b calma w ترتاح."
            elif "cafe" in types:
                base = "Cafe mzyan l 9ahwa, snack, w wa9fa sghira."
            elif "spa" in types:
                base = "Blasa hadi2a باش ترتاح w t-rta7 shwiya."
            else:
                base = f"{label} ممكن تعجبك ف sortie dyalk."

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
            base = "Une salle de sport pratique pour s'entraîner et garder le rythme."
        elif "park" in types:
            base = "Un espace vert agreable pour marcher, respirer et se detendre."
        elif "museum" in types:
            base = "Un arret culturel sympa pour decouvrir histoire, art ou expositions."
        elif "tourist_attraction" in types or "point_of_interest" in types:
            base = "Un spot interessant pour explorer et faire quelques photos."
        elif "restaurant" in types:
            base = "Une bonne option pour manger tranquillement pendant ta sortie."
        elif "cafe" in types:
            base = "Un bon coin pour une pause cafe ou un snack."
        elif "spa" in types:
            base = "Un endroit calme pour se detendre et se ressourcer."
        else:
            base = f"Un {label.lower()} a decouvrir pendant ta sortie."

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
