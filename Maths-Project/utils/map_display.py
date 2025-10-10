# utils/map_display.py
import folium
from streamlit_folium import st_folium
from typing import List, Optional, Sequence, Tuple

LatLon = Tuple[float, float]

def _compute_bounds(all_points: Sequence[LatLon]) -> Tuple[LatLon, LatLon]:
    lats = [lat for lat, _ in all_points]
    lons = [lon for _, lon in all_points]
    return (min(lats), min(lons)), (max(lats), max(lons))

def display_map(
    coord1: LatLon,
    coord2: LatLon,
    path_coords: List[LatLon],
    alt_paths: Optional[List[List[LatLon]]] = None,
    labels: Optional[List[str]] = None,
    path_color: str = "blue",
    alt_colors: Optional[List[str]] = None,
    zoom_start: int = 12,
    tiles: str = "OpenStreetMap",
) -> None:
    """Display a folium map with start/destination markers and one primary route,
    optionally overlaying alternative routes with distinct colors and labels.

    The first label (if provided) is used for the primary route; subsequent
    labels (if any) are applied to alternative routes in order.
    """

    m = folium.Map(location=coord1, zoom_start=zoom_start, tiles=tiles)

    # Markers
    folium.Marker(coord1, popup="Start", icon=folium.Icon(color="green")).add_to(m)
    folium.Marker(coord2, popup="Destination", icon=folium.Icon(color="red")).add_to(m)

    # Primary route
    folium.PolyLine(
        path_coords,
        color=path_color,
        weight=6,
        opacity=0.8,
        tooltip=(labels[0] if labels and len(labels) >= 1 else "Selected route"),
    ).add_to(m)

    # Alternative routes
    if alt_paths:
        palette = alt_colors or ["gray", "purple", "orange", "cadetblue", "darkred"]
        for idx, coords in enumerate(alt_paths):
            color = palette[idx % len(palette)]
            label = None
            if labels and (idx + 1) < len(labels):
                label = labels[idx + 1]
            folium.PolyLine(
                coords,
                color=color,
                weight=4,
                opacity=0.6,
                tooltip=(label or f"Alternative {idx+1}"),
            ).add_to(m)

    # Auto fit bounds to include all content
    all_points: List[LatLon] = [coord1, coord2] + list(path_coords)
    if alt_paths:
        for ap in alt_paths:
            all_points.extend(ap)
    sw, ne = _compute_bounds(all_points)
    m.fit_bounds([sw, ne], padding=(30, 30))

    st_folium(m, width=800, height=520)