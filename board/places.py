"""Match a stored point to a saved place. No distances leave this module."""

from __future__ import annotations

import math
from datetime import datetime
from zoneinfo import ZoneInfo


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6_371_000
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def usable_places(places: list[dict]) -> list[dict]:
    ready = []
    for place in places:
        lat = place.get("lat")
        lon = place.get("lon")
        radius = place.get("radius_m")
        name = place.get("name")
        if not name or lat is None or lon is None or not radius or radius <= 0:
            continue
        ready.append(
            {
                "name": str(name),
                "lat": float(lat),
                "lon": float(lon),
                "radius_m": float(radius),
            }
        )
    return ready


def match_place(lat: float, lon: float, places: list[dict]) -> str | None:
    """Return the smallest saved place that contains the point, or None."""
    hits = []
    for place in usable_places(places):
        if haversine_m(lat, lon, place["lat"], place["lon"]) <= place["radius_m"]:
            hits.append(place)
    if not hits:
        return None
    hits.sort(key=lambda place: (place["radius_m"], place["name"]))
    return hits[0]["name"]


def format_when(tst: int, tz_name: str, now: datetime | None = None) -> str:
    zone = ZoneInfo(tz_name)
    moment = datetime.fromtimestamp(int(tst), zone)
    clock = moment.strftime("%I:%M %p").replace("\u202f", " ").replace("\xa0", " ").lstrip("0")
    today = (now or datetime.now(zone)).astimezone(zone)
    if moment.date() == today.date():
        return clock
    return f"{moment.strftime('%a')} {clock}"


def place_line(lat, lon, places: list[dict]) -> tuple[str, bool]:
    """Return (words, places_are_configured)."""
    ready = usable_places(places)
    if not ready:
        return "Places not set", False
    name = match_place(lat, lon, ready)
    if name is None:
        return "Between saved places", True
    return name, True
