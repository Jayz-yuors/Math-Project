# utils/place_search.py
from typing import List, Dict
import openrouteservice
from config.api_keys import OPENROUTESERVICE_API_KEY

_client = openrouteservice.Client(key=OPENROUTESERVICE_API_KEY)


def suggest_places(query: str, limit: int = 8) -> List[Dict]:
    """Return autocomplete suggestions for a query using ORS Pelias.

    Each suggestion contains: { 'label': str, 'lat': float, 'lon': float }
    """
    if not query or not query.strip():
        return []

    # Prefer autocomplete endpoint; fallback to search if unavailable
    try:
        result = _client.pelias_autocomplete(text=query, size=limit)
    except Exception:
        # Fallback to generic search
        result = _client.pelias_search(text=query, size=limit)

    features = (result or {}).get("features", [])
    suggestions: List[Dict] = []
    for f in features:
        props = f.get("properties", {})
        label = props.get("label") or props.get("name") or "Unknown"
        coords = f.get("geometry", {}).get("coordinates") or []
        if len(coords) >= 2:
            lon, lat = coords[0], coords[1]
            suggestions.append({"label": label, "lat": float(lat), "lon": float(lon)})
    return suggestions