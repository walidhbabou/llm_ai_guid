from math import atan2, cos, radians, sin, sqrt
import re
import unicodedata
from typing import Any

import httpx

from app.core.config import settings
from app.core.exceptions import GoogleMapsError

_PREFERENCE_SEARCH_HINTS = {
    "balade": ("promenade", "corniche"),
    "calme": ("quiet",),
    "coucher de soleil": ("sunset viewpoint", "sunset beach"),
    "culture": ("cultural landmark", "museum"),
    "familial": ("family friendly",),
    "historique": ("historic site", "medina"),
    "photos": ("photo spot", "viewpoint"),
    "romantique": ("romantic place", "rooftop"),
    "terrasse": ("terrace", "rooftop"),
    "vue mer": ("sea view",),
    "vue panoramique": ("viewpoint", "panoramic view"),
}


class GoogleMapsClient:
    GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
    PLACES_TEXT_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    PLACES_NEARBY_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"

    def __init__(self) -> None:
        if not settings.google_maps_api_key:
            raise GoogleMapsError("GOOGLE_MAPS_API_KEY est manquante")

    async def geocode_city(self, city: str) -> tuple[float, float] | None:
        params = {
            "address": city,
            "key": settings.google_maps_api_key,
            "language": settings.google_language,
            "region": settings.google_region,
        }
        data = await self._get(self.GEOCODE_URL, params=params)

        results = data.get("results", [])
        if not results:
            return None

        location = results[0].get("geometry", {}).get("location", {})
        lat = location.get("lat")
        lng = location.get("lng")
        if lat is None or lng is None:
            return None
        return float(lat), float(lng)

    async def reverse_geocode_city(self, latitude: float, longitude: float) -> str | None:
        params = {
            "latlng": f"{latitude},{longitude}",
            "key": settings.google_maps_api_key,
            "language": settings.google_language,
            "result_type": "locality|administrative_area_level_1",
        }
        data = await self._get(self.GEOCODE_URL, params=params)

        for result in data.get("results", []):
            for component in result.get("address_components", []):
                types = component.get("types", [])
                if "locality" in types:
                    return component.get("long_name")
        return None

    async def search_places(
        self,
        *,
        raw_query: str,
        category: str | None,
        preferences: list[str] | None,
        city: str | None,
        limit: int,
        near_me: bool,
        user_latitude: float | None,
        user_longitude: float | None,
    ) -> list[dict[str, Any]]:
        query_variants = self._build_query_variants(
            raw_query=raw_query,
            category=category,
            preferences=preferences,
            city=city,
        )

        if near_me and user_latitude is not None and user_longitude is not None:
            nearby_results = await self._search_query_variants_nearby(
                queries=query_variants,
                latitude=user_latitude,
                longitude=user_longitude,
                limit=limit,
                prefer_distance=True,
                max_distance_meters=settings.google_near_me_radius_meters,
            )
            if nearby_results:
                return nearby_results

        if city:
            coords = await self.geocode_city(city)
            if coords:
                nearby_results = await self._search_query_variants_nearby(
                    queries=query_variants,
                    latitude=coords[0],
                    longitude=coords[1],
                    limit=limit,
                    prefer_distance=False,
                    max_distance_meters=None,
                )
                if nearby_results:
                    return nearby_results

        return await self._search_query_variants_text(
            queries=query_variants,
            limit=limit,
        )

    async def _nearby_search(
        self,
        *,
        category: str | None,
        preferences: list[str] | None,
        latitude: float,
        longitude: float,
        limit: int,
        prefer_distance: bool,
        query_hint: str | None,
        max_distance_meters: int | None,
    ) -> list[dict[str, Any]]:
        keyword = self._build_keyword(
            category=category,
            preferences=preferences,
            query_hint=query_hint,
        )
        params = {
            "key": settings.google_maps_api_key,
            "location": f"{latitude},{longitude}",
            "keyword": keyword,
            "language": settings.google_language,
        }

        if prefer_distance:
            params["rankby"] = "distance"
        else:
            params["radius"] = settings.google_search_radius_meters

        data = await self._get(self.PLACES_NEARBY_URL, params=params)
        results = data.get("results", [])

        if max_distance_meters is None:
            return results[:limit]

        with_distance: list[tuple[float, dict[str, Any]]] = []
        for place in results:
            loc = place.get("geometry", {}).get("location", {})
            lat = loc.get("lat")
            lng = loc.get("lng")
            if lat is None or lng is None:
                continue
            distance = self._distance_meters(latitude, longitude, float(lat), float(lng))
            with_distance.append((distance, place))

        within_radius = [item for item in with_distance if item[0] <= max_distance_meters]
        if within_radius:
            within_radius.sort(key=lambda item: item[0])
            return [item[1] for item in within_radius[:limit]]

        # If nothing is inside the strict radius, still return nearest results.
        with_distance.sort(key=lambda item: item[0])
        return [item[1] for item in with_distance[:limit]]

    def _distance_meters(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        earth_radius_m = 6371000.0
        d_lat = radians(lat2 - lat1)
        d_lng = radians(lng2 - lng1)
        a = sin(d_lat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lng / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        return earth_radius_m * c

    async def _search_query_variants_nearby(
        self,
        *,
        queries: list[str],
        latitude: float,
        longitude: float,
        limit: int,
        prefer_distance: bool,
        max_distance_meters: int | None,
    ) -> list[dict[str, Any]]:
        merged_results: list[dict[str, Any]] = []
        seen: set[str] = set()

        for query in queries:
            results = await self._nearby_search(
                category=None,
                preferences=None,
                latitude=latitude,
                longitude=longitude,
                limit=limit,
                prefer_distance=prefer_distance,
                query_hint=query,
                max_distance_meters=max_distance_meters,
            )
            self._merge_place_results(merged_results, seen, results, limit)
            if len(merged_results) >= limit:
                break

        return merged_results[:limit]

    async def _search_query_variants_text(
        self,
        *,
        queries: list[str],
        limit: int,
    ) -> list[dict[str, Any]]:
        merged_results: list[dict[str, Any]] = []
        seen: set[str] = set()

        for query in queries:
            results = await self._text_search(
                raw_query=query,
                category=None,
                preferences=None,
                city=None,
                limit=limit,
            )
            self._merge_place_results(merged_results, seen, results, limit)
            if len(merged_results) >= limit:
                break

        return merged_results[:limit]

    async def _text_search(
        self,
        *,
        raw_query: str,
        category: str | None,
        preferences: list[str] | None,
        city: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        text_query = self._build_text_query(
            raw_query=raw_query,
            category=category,
            preferences=preferences,
            city=city,
        )
        params = {
            "query": text_query,
            "key": settings.google_maps_api_key,
            "language": settings.google_language,
            "region": settings.google_region,
        }
        data = await self._get(self.PLACES_TEXT_URL, params=params)
        return data.get("results", [])[:limit]

    def build_photo_url(self, photo_reference: str, max_width: int = 800) -> str:
        return (
            "https://maps.googleapis.com/maps/api/place/photo"
            f"?maxwidth={max_width}&photo_reference={photo_reference}&key={settings.google_maps_api_key}"
        )

    def _build_keyword(
        self,
        *,
        category: str | None,
        preferences: list[str] | None,
        query_hint: str | None,
    ) -> str:
        parts: list[str] = []
        if category:
            parts.append(self._category_to_keyword(category))
        if preferences:
            parts.extend(preferences[:3])
        if not parts and query_hint:
            return query_hint.strip()
        if not parts:
            return "tourist attractions"
        return " ".join(parts).strip()

    def _build_text_query(
        self,
        *,
        raw_query: str,
        category: str | None,
        preferences: list[str] | None,
        city: str | None,
    ) -> str:
        if not city:
            return raw_query

        parts: list[str] = []
        if category:
            parts.append(self._category_to_keyword(category))
        if preferences:
            parts.extend(preferences[:3])
        if not parts:
            parts.append(raw_query)

        parts.append(city)
        return " ".join(part.strip() for part in parts if part and part.strip())

    def _build_query_variants(
        self,
        *,
        raw_query: str,
        category: str | None,
        preferences: list[str] | None,
        city: str | None,
    ) -> list[str]:
        raw_query = raw_query.strip()
        variants: list[str] = []

        semantic_parts: list[str] = []
        if category:
            semantic_parts.append(self._category_to_keyword(category))
        semantic_parts.extend(self._preference_to_search_terms(preferences))

        semantic_query = " ".join(semantic_parts[:3]).strip()
        if semantic_query:
            variants.append(f"{semantic_query} {city}".strip() if city else semantic_query)

        if raw_query:
            variants.append(raw_query)

        if city and raw_query and self._normalize_text(city) not in self._normalize_text(raw_query):
            variants.append(f"{raw_query} {city}")

        if category and city:
            variants.append(f"{self._category_to_keyword(category)} {city}")
        elif category:
            variants.append(self._category_to_keyword(category))

        deduped_variants: list[str] = []
        seen: set[str] = set()
        for item in variants:
            cleaned = " ".join(item.split()).strip()
            if not cleaned:
                continue
            normalized = self._normalize_text(cleaned)
            if normalized in seen:
                continue
            seen.add(normalized)
            deduped_variants.append(cleaned)

        return deduped_variants[:4] or ["tourist attractions"]

    def _preference_to_search_terms(self, preferences: list[str] | None) -> list[str]:
        if not preferences:
            return []

        mapped_terms: list[str] = []
        for preference in preferences:
            normalized_preference = self._normalize_text(preference)
            aliases = _PREFERENCE_SEARCH_HINTS.get(normalized_preference)
            if aliases:
                mapped_terms.extend(aliases[:1])
            elif preference.strip():
                mapped_terms.append(preference.strip())

        deduped_terms: list[str] = []
        seen: set[str] = set()
        for item in mapped_terms:
            normalized = self._normalize_text(item)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            deduped_terms.append(item)
        return deduped_terms

    def _merge_place_results(
        self,
        merged_results: list[dict[str, Any]],
        seen: set[str],
        results: list[dict[str, Any]],
        limit: int,
    ) -> None:
        for place in results:
            place_id = str(place.get("place_id") or "").strip()
            if place_id:
                unique_key = place_id
            else:
                loc = place.get("geometry", {}).get("location", {})
                lat = loc.get("lat")
                lng = loc.get("lng")
                name = str(place.get("name") or "").strip().lower()
                unique_key = f"{name}|{lat}|{lng}"

            if not unique_key or unique_key in seen:
                continue

            seen.add(unique_key)
            merged_results.append(place)
            if len(merged_results) >= limit:
                break

    def _category_to_keyword(self, category: str) -> str:
        category_keywords = {
            "mosquee": "mosque",
        }
        return category_keywords.get(category, category)

    def _normalize_text(self, value: str) -> str:
        ascii_value = unicodedata.normalize("NFKD", value)
        ascii_value = "".join(ch for ch in ascii_value if not unicodedata.combining(ch))
        ascii_value = ascii_value.lower()
        ascii_value = re.sub(r"[â€™']", " ", ascii_value)
        ascii_value = re.sub(r"[^a-z0-9\s-]", " ", ascii_value)
        return re.sub(r"\s+", " ", ascii_value).strip()

    async def _get(self, url: str, *, params: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=20.0) as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise GoogleMapsError(f"HTTP error Google Maps: {exc}") from exc

        data = response.json()
        status = data.get("status")

        if status in {"OK", "ZERO_RESULTS"}:
            return data

        error_message = data.get("error_message") or status or "Unknown Google Maps error"
        raise GoogleMapsError(f"Google Maps API a echoue: {error_message}")
