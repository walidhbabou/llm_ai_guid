from app.clients.google_maps_client import GoogleMapsClient
from app.dto.search_dto import PlaceDTO


def _label_from_types(types: list[str]) -> str:
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


def _build_description(place: dict) -> str | None:
    types = [str(t).lower() for t in place.get("types", []) if isinstance(t, str)]
    label = _label_from_types(types)
    rating = place.get("rating")
    address = place.get("formatted_address") or place.get("vicinity")

    if rating is not None and address:
        return f"{label} note {rating}/5, situe a {address}."
    if rating is not None:
        return f"{label} note {rating}/5."
    if address:
        return f"{label} situe a {address}."
    return f"{label} local recommande."


def map_google_place_to_dto(place: dict, google_client: GoogleMapsClient) -> PlaceDTO:
    geometry = place.get("geometry", {}).get("location", {})
    photos = place.get("photos", [])

    photo_url = None
    if photos:
        ref = photos[0].get("photo_reference")
        if ref:
            photo_url = google_client.build_photo_url(ref)

    place_id = place.get("place_id", "")

    return PlaceDTO(
        name=place.get("name", ""),
        description=_build_description(place),
        address=place.get("formatted_address") or place.get("vicinity") or "",
        latitude=float(geometry.get("lat", 0.0)),
        longitude=float(geometry.get("lng", 0.0)),
        rating=place.get("rating"),
        types=place.get("types", []),
        photo_url=photo_url,
        place_id=place_id,
        google_maps_url=(
            f"https://www.google.com/maps/place/?q=place_id:{place_id}" if place_id else None
        ),
    )
