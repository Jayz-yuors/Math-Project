# app.py
import streamlit as st
from typing import Dict, List, Tuple
from utils.geocode import get_coordinates
from utils.map_display import display_map
from utils.place_search import suggest_places
import openrouteservice
from config.api_keys import OPENROUTESERVICE_API_KEY
import json

st.set_page_config(page_title="City Map Navigator 🗺", layout="centered")

st.title("🚗 City Map Navigator")
st.markdown("Use real-world data to find and visualize the shortest route between two places.")

# -------------------------
# Helpers
# -------------------------
def format_distance(meters: float, units: str) -> str:
    if units == "mi":
        miles = meters / 1609.344
        return f"{miles:.2f} mi"
    # default km
    km = meters / 1000.0
    return f"{km:.2f} km"

def format_duration(seconds: float) -> str:
    seconds = int(round(seconds))
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"

def ensure_state_keys():
    defaults = {
        "routes": [],  # list of dicts: distance_m, duration_s, coords_latlon, coords_lonlat, steps, profile
        "selected_route_index": 0,
        "last_query": {},
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

ensure_state_keys()

# -------------------------
# Input Form
# -------------------------
with st.form("route_form"):
    col1, col2 = st.columns(2)
    with col1:
        start_query = st.text_input("Starting Point", "Gateway of India, Mumbai")
        start_suggestions = suggest_places(start_query) if len(start_query) >= 1 else []
        start_labels = [s["label"] for s in start_suggestions] or [start_query]
        start_choice = st.selectbox("Select start", options=start_labels, index=0)
    with col2:
        end_query = st.text_input("Destination", "Chhatrapati Shivaji Maharaj Terminus, Mumbai")
        end_suggestions = suggest_places(end_query) if len(end_query) >= 1 else []
        end_labels = [s["label"] for s in end_suggestions] or [end_query]
        end_choice = st.selectbox("Select destination", options=end_labels, index=0)

    col3, col4, col5 = st.columns(3)
    with col3:
        compare_modes = st.checkbox("Compare modes", value=False, help="Overlay car, cycling, walking")
        if compare_modes:
            modes = st.multiselect(
                "Modes",
                options=["driving-car", "cycling-regular", "foot-walking"],
                default=["driving-car", "cycling-regular", "foot-walking"],
            )
        else:
            mode = st.selectbox(
                "Travel mode",
                options=["driving-car", "cycling-regular", "foot-walking"],
                index=0,
                help="Select routing profile",
            )
    with col4:
        units = st.selectbox("Units", options=["km", "mi"], index=0)
    with col5:
        want_alts = st.checkbox("Show alternatives (if supported)", value=True)

    col6, col7 = st.columns(2)
    with col6:
        alt_count = st.slider("# alternatives", min_value=1, max_value=3, value=2, disabled=not want_alts)
    with col7:
        show_steps = st.checkbox("Turn-by-turn steps", value=True)

    submitted = st.form_submit_button("Find Path")

if submitted:
    st.info("Fetching coordinates and calculating route...")

    # Try to use selected suggestions' coordinates; fallback to geocode
    start_lookup = {s["label"]: (s["lat"], s["lon"]) for s in start_suggestions}
    end_lookup = {s["label"]: (s["lat"], s["lon"]) for s in end_suggestions}
    start_coords = start_lookup.get(start_choice) or get_coordinates(start_choice)
    end_coords = end_lookup.get(end_choice) or get_coordinates(end_choice)

    if start_coords and end_coords:
        client = openrouteservice.Client(key=OPENROUTESERVICE_API_KEY)

        def fetch_route_for_profile(profile: str) -> List[Dict]:
            coords = [
                (start_coords[1], start_coords[0]),  # (lon, lat)
                (end_coords[1], end_coords[0]),
            ]
            kwargs: Dict = {
                "coordinates": coords,
                "profile": profile,
                "format": "json",
            }
            if show_steps:
                kwargs["instructions"] = True
            # Always avoid ferries (sea routes)
            kwargs["options"] = {"avoid_features": ["ferries"]}
            if want_alts:
                # Request alternatives when supported; we'll handle rejections
                kwargs["options"]["alternative_routes"] = {"target_count": int(alt_count)}

            # Attempt request with graceful fallbacks
            try:
                result = client.directions(**kwargs)
            except openrouteservice.exceptions.ApiError as api_err:
                msg = str(api_err)
                # Remove only the offending alternative_routes key if rejected
                if "Unknown parameter" in msg and "alternative_routes" in msg and "options" in kwargs:
                    _ = kwargs["options"].pop("alternative_routes", None)
                    if not kwargs["options"]:
                        kwargs.pop("options", None)
                    result = client.directions(**kwargs)
                else:
                    raise
            except TypeError:
                # Client too old for options/instructions
                if "options" in kwargs:
                    kwargs.pop("options", None)
                try:
                    result = client.directions(**kwargs)
                except TypeError:
                    kwargs.pop("instructions", None)
                    result = client.directions(**kwargs)

            routes = result.get("routes", [])
            parsed: List[Dict] = []
            for r in routes:
                geometry_obj = r.get("geometry")
                if isinstance(geometry_obj, dict) and geometry_obj.get("type") == "LineString":
                    coords_lonlat = geometry_obj.get("coordinates", [])
                else:
                    decoded = openrouteservice.convert.decode_polyline(geometry_obj)
                    coords_lonlat = decoded["coordinates"]
                coords_latlon: List[Tuple[float, float]] = [(c[1], c[0]) for c in coords_lonlat]
                summary = r.get("summary", {})
                distance_m = float(summary.get("distance", 0.0))
                duration_s = float(summary.get("duration", 0.0))
                steps = []
                segments = r.get("segments") or []
                if segments and show_steps:
                    steps = segments[0].get("steps", [])
                parsed.append(
                    {
                        "distance_m": distance_m,
                        "duration_s": duration_s,
                        "coords_latlon": coords_latlon,
                        "coords_lonlat": coords_lonlat,
                        "steps": steps,
                        "profile": profile,
                    }
                )
            return parsed

        try:
            if 'compare_modes' in locals() and compare_modes:
                selected_profiles = modes or ["driving-car", "cycling-regular", "foot-walking"]
            else:
                selected_profiles = [mode]

            routes_by_profile: Dict[str, List[Dict]] = {}
            for p in selected_profiles:
                routes_by_profile[p] = fetch_route_for_profile(p)

            # Flatten primary (first route per profile)
            collected: List[Dict] = []
            for p in selected_profiles:
                if routes_by_profile.get(p):
                    collected.append(routes_by_profile[p][0])

            if not collected:
                st.warning("No routes found. Try different inputs or mode.")
            else:
                st.session_state.routes = collected
                st.session_state.selected_route_index = 0
                st.session_state.last_query = {
                    "start": start_choice,
                    "end": end_choice,
                    "start_coords": start_coords,
                    "end_coords": end_coords,
                    "units": units,
                    "profiles": selected_profiles,
                }
                st.success("Route(s) loaded")

        except Exception as e:
            st.error(f"Error fetching route: {e}")
    else:
        st.warning("Could not fetch coordinates for the given addresses.")

# -------------------------
# Results Rendering
# -------------------------
if st.session_state.get("routes"):
    routes = st.session_state.routes
    start_coords = st.session_state.last_query.get("start_coords")
    end_coords = st.session_state.last_query.get("end_coords")
    units = st.session_state.last_query.get("units", "km")

    labels: List[str] = []
    for idx, r in enumerate(routes):
        profile_label = {
            "driving-car": "Car",
            "cycling-regular": "Bike",
            "foot-walking": "Walk",
        }.get(r.get("profile"), r.get("profile", ""))
        labels.append(
            f"{profile_label}: {format_distance(r['distance_m'], units)} / {format_duration(r['duration_s'])}"
        )

    # Allow selecting among alternatives/modes
    choice = st.selectbox(
        "Choose a route",
        options=list(range(len(routes))),
        format_func=lambda i: labels[i],
        index=st.session_state.selected_route_index,
    )
    if choice != st.session_state.selected_route_index:
        st.session_state.selected_route_index = choice

    selected = routes[st.session_state.selected_route_index]
    # Other routes shown as alternative overlays
    alts = [r["coords_latlon"] for i, r in enumerate(routes) if i != st.session_state.selected_route_index]
    alt_labels = [labels[i] for i in range(len(routes)) if i != st.session_state.selected_route_index]

    # Metrics
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Total distance", format_distance(selected["distance_m"], units))
    with m2:
        st.metric("Estimated time", format_duration(selected["duration_s"]))
    with m3:
        st.metric("Routes shown", f"{len(routes)}")

    # Map
    display_map(
        start_coords,
        end_coords,
        selected["coords_latlon"],
        alt_paths=alts,
        labels=[labels[st.session_state.selected_route_index]] + alt_labels,
        path_color="blue",
    )

    # Steps
    if selected.get("steps"):
        with st.expander("Turn-by-turn instructions"):
            for i, step in enumerate(selected["steps"], start=1):
                inst = (step.get("instruction") or "").strip()
                sd = float(step.get("distance", 0.0))
                du = float(step.get("duration", 0.0))
                # Add a simple icon based on maneuver/type
                maneuver = step.get("type")
                icon = "➡️"
                if maneuver in (0, 1):
                    icon = "⬆️"
                elif maneuver in (2, 3):
                    icon = "↪️"
                elif maneuver in (4, 5):
                    icon = "⤴️"
                elif maneuver in (6, 7):
                    icon = "⤵️"
                elif maneuver == 10:
                    icon = "🛣️"
                elif maneuver == 11:
                    icon = "⚠️"
                st.markdown(f"{icon} **Step {i}:** {inst}  ")
                st.caption(f"{format_distance(sd, units)} • {format_duration(du)}")

    # Download GeoJSON
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "profiles": st.session_state.last_query.get("profiles"),
                    "distance": selected["distance_m"],
                    "duration": selected["duration_s"],
                    "units": units,
                    "start": st.session_state.last_query.get("start"),
                    "end": st.session_state.last_query.get("end"),
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": selected["coords_lonlat"],  # lon, lat
                },
            }
        ],
    }
    st.download_button(
        label="Download route (GeoJSON)",
        data=json.dumps(geojson, indent=2),
        file_name="route.geojson",
        mime="application/geo+json",
    )