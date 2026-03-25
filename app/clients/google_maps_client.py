from typing import Any
from math import atan2, cos, radians, sin, sqrt

import httpx

from app.core.config import settings
from app.core.exceptions import GoogleMapsError


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
        city: str | None,
        limit: int,
        near_me: bool,
        user_latitude: float | None,
        user_longitude: float | None,
    ) -> list[dict[str, Any]]:
        if near_me and user_latitude is not None and user_longitude is not None:
            return await self._nearby_search(
                category=category,
                latitude=user_latitude,
                longitude=user_longitude,
                limit=limit,
                prefer_distance=True,
                query_hint=raw_query,
                max_distance_meters=settings.google_near_me_radius_meters,
            )

        if city:
            coords = await self.geocode_city(city)
            if coords:
                return await self._nearby_search(
                    category=category,
                    latitude=coords[0],
                    longitude=coords[1],
                    limit=limit,
                    prefer_distance=False,
                    query_hint=None,
                    max_distance_meters=None,
                )

        return await self._text_search(
            raw_query=raw_query,
            category=category,
            city=city,
            limit=limit,
        )

    async def _nearby_search(
        self,
        *,
        category: str | None,
        latitude: float,
        longitude: float,
        limit: int,
        prefer_distance: bool,
        query_hint: str | None,
        max_distance_meters: int | None,
    ) -> list[dict[str, Any]]:
        keyword = (category or query_hint or "tourist attractions").strip()
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

    async def _text_search(
        self,
        *,
        raw_query: str,
        category: str | None,
        city: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        base = category if category else "lieux touristiques"
        text_query = f"{base} {city}".strip() if city else raw_query
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
