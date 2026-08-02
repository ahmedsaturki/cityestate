"""
Google Maps Skill — خدمات الموقع والخرائط
==========================================
Location services: geocoding, reverse geocoding, nearby search,
property location analysis, and commute time calculation.
"""

import json
import logging
import math

logger = logging.getLogger("skills.google_maps")


class GoogleMapsSkill:
    """Location and mapping skill."""

    def __init__(self):
        self._nominatim_url = "https://nominatim.openstreetmap.org"
        self._headers = {
            "User-Agent": "CityEstateBot/1.0 (real-estate-automation)"
        }

    async def geocode(self, address: str) -> dict:
        """Convert address to coordinates."""
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self._nominatim_url}/search",
                    params={
                        "q": address,
                        "format": "json",
                        "limit": 1,
                        "addressdetails": 1,
                    },
                    headers=self._headers,
                    timeout=10,
                )
                data = resp.json()
                if data:
                    return {
                        "status": "success",
                        "address": address,
                        "lat": float(data[0]["lat"]),
                        "lon": float(data[0]["lon"]),
                        "display_name": data[0].get("display_name", ""),
                        "address_details": data[0].get("address", {}),
                    }
                return {"status": "not_found", "address": address}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def reverse_geocode(self, lat: float, lon: float) -> dict:
        """Convert coordinates to address."""
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self._nominatim_url}/reverse",
                    params={
                        "lat": lat,
                        "lon": lon,
                        "format": "json",
                        "addressdetails": 1,
                    },
                    headers=self._headers,
                    timeout=10,
                )
                data = resp.json()
                return {
                    "status": "success",
                    "lat": lat,
                    "lon": lon,
                    "display_name": data.get("display_name", ""),
                    "address": data.get("address", {}),
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def nearby_search(
        self,
        lat: float,
        lon: float,
        query: str = "real estate",
        radius_meters: int = 5000,
    ) -> dict:
        """Search for places near a location using Overpass API."""
        try:
            import httpx

            # Map query to Overpass categories
            category_map = {
                "real estate": '["shop"="estate_agent"]',
                "school": '["amenity"="school"]',
                "hospital": '["amenity"="hospital"]',
                "pharmacy": '["amenity"="pharmacy"]',
                "restaurant": '["amenity"="restaurant"]',
                "supermarket": '["shop"="supermarket"]',
                "park": '["leisure"="park"]',
                "gym": '["leisure"="fitness_centre"]',
                "mosque": '["amenity"="place_of_worship"]["religion"="muslim"]',
                "church": '["amenity"="place_of_worship"]["religion"="christian"]',
            }

            tag = category_map.get(query.lower(), f'["name"~"{query}",i]')
            overpass_query = f"""
            [out:json][timeout:25];
            (
              node{tag}(around:{radius_meters},{lat},{lon});
              way{tag}(around:{radius_meters},{lat},{lon});
            );
            out center body;
            """

            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://overpass-api.de/api/interpreter",
                    data={"data": overpass_query},
                    timeout=30,
                )
                data = resp.json()

                places = []
                for elem in data.get("elements", [])[:20]:
                    place_lat = elem.get("lat") or elem.get("center", {}).get("lat")
                    place_lon = elem.get("lon") or elem.get("center", {}).get("lon")
                    if place_lat and place_lon:
                        places.append({
                            "name": elem.get("tags", {}).get("name", "Unknown"),
                            "lat": place_lat,
                            "lon": place_lon,
                            "type": elem.get("tags", {}).get("shop") or elem.get("tags", {}).get("amenity", ""),
                            "distance_m": self._haversine(lat, lon, place_lat, place_lon),
                        })

                places.sort(key=lambda x: x["distance_m"])
                return {
                    "status": "success",
                    "query": query,
                    "center": {"lat": lat, "lon": lon},
                    "radius_meters": radius_meters,
                    "results": places,
                    "count": len(places),
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def analyze_property_location(self, lat: float, lon: float) -> dict:
        """Comprehensive location analysis for a property."""
        import asyncio

        analyses = await asyncio.gather(
            self.reverse_geocode(lat, lon),
            self.nearby_search(lat, lon, "real estate", 2000),
            self.nearby_search(lat, lon, "school", 3000),
            self.nearby_search(lat, lon, "hospital", 3000),
            self.nearby_search(lat, lon, "supermarket", 1500),
            self.nearby_search(lat, lon, "pharmacy", 1500),
            self.nearby_search(lat, lon, "mosque", 1000),
            return_exceptions=True,
        )

        return {
            "status": "success",
            "location": analyses[0] if isinstance(analyses[0], dict) else {},
            "nearby": {
                "real_estate": analyses[1].get("count", 0) if isinstance(analyses[1], dict) else 0,
                "schools": analyses[2].get("count", 0) if isinstance(analyses[2], dict) else 0,
                "hospitals": analyses[3].get("count", 0) if isinstance(analyses[3], dict) else 0,
                "supermarkets": analyses[4].get("count", 0) if isinstance(analyses[4], dict) else 0,
                "pharmacies": analyses[5].get("count", 0) if isinstance(analyses[5], dict) else 0,
                "mosques": analyses[6].get("count", 0) if isinstance(analyses[6], dict) else 0,
            },
            "score": self._calculate_location_score(analyses),
        }

    async def calculate_distance(self, origin: str, destination: str) -> dict:
        """Calculate distance between two addresses."""
        try:
            origin_geo = await self.geocode(origin)
            dest_geo = await self.geocode(destination)

            if origin_geo["status"] != "success" or dest_geo["status"] != "success":
                return {"status": "error", "error": "Could not geocode one or both locations"}

            distance = self._haversine(
                origin_geo["lat"], origin_geo["lon"],
                dest_geo["lat"], dest_geo["lon"],
            )

            return {
                "status": "success",
                "origin": origin,
                "destination": destination,
                "distance_km": round(distance / 1000, 2),
                "distance_m": round(distance),
                "estimated_drive_time_min": round(distance / 800, 1),  # ~48 km/h avg
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _haversine(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance in meters between two points."""
        R = 6371000
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    def _calculate_location_score(self, analyses: list) -> dict:
        """Calculate a location quality score (0-100)."""
        score = 50  # Base score
        weights = {"real_estate": 5, "schools": 8, "hospitals": 8, "supermarkets": 6, "pharmacies": 5, "mosques": 4}
        max_bonus = sum(weights.values())

        for i, key in enumerate(["real_estate", "schools", "hospitals", "supermarkets", "pharmacies", "mosques"]):
            if isinstance(analyses[i + 1], dict):
                count = analyses[i + 1].get("count", 0)
                bonus = min(count * weights[key] / 10, weights[key])
                score += bonus

        return {"total": min(round(score), 100), "max_possible": 50 + max_bonus}


def get_maps_tools():
    """Return CrewAI-compatible tools for maps and location."""
    from crewai.tools import BaseTool
    from pydantic import BaseModel, Field

    class GeocodeInput(BaseModel):
        address: str = Field(description="Address to geocode")

    class GeocodeTool(BaseTool):
        name: str = "geocode_address"
        description: str = "Convert an address to latitude/longitude coordinates."
        args_schema: type = GeocodeInput

        def _run(self, address: str) -> str:
            import asyncio
            skill = GoogleMapsSkill()
            result = asyncio.run(skill.geocode(address))
            return json.dumps(result, ensure_ascii=False)

    class LocationAnalysisInput(BaseModel):
        lat: float = Field(description="Latitude")
        lon: float = Field(description="Longitude")

    class LocationAnalysisTool(BaseTool):
        name: str = "analyze_location"
        description: str = "Comprehensive location analysis: nearby schools, hospitals, supermarkets, mosques, and location score."
        args_schema: type = LocationAnalysisInput

        def _run(self, lat: float, lon: float) -> str:
            import asyncio
            skill = GoogleMapsSkill()
            result = asyncio.run(skill.analyze_property_location(lat, lon))
            return json.dumps(result, ensure_ascii=False)

    class NearbySearchInput(BaseModel):
        lat: float = Field(description="Latitude")
        lon: float = Field(description="Longitude")
        query: str = Field(default="real estate", description="Type of place to search for")
        radius: int = Field(default=5000, description="Search radius in meters")

    class NearbySearchTool(BaseTool):
        name: str = "nearby_search"
        description: str = "Search for nearby places (schools, hospitals, shops, mosques, etc.) by type."
        args_schema: type = NearbySearchInput

        def _run(self, lat: float, lon: float, query: str = "real estate", radius: int = 5000) -> str:
            import asyncio
            skill = GoogleMapsSkill()
            result = asyncio.run(skill.nearby_search(lat, lon, query, radius))
            return json.dumps(result, ensure_ascii=False)

    return [GeocodeTool(), LocationAnalysisTool(), NearbySearchTool()]
