import streamlit as st
import openrouteservice
from rapidfuzz import process, fuzz
from typing import Dict, List, Tuple
import folium
from streamlit_folium import folium_static
import json
import math

# Configuration and Setup
st.set_page_config(page_title="Smart City Navigator 🚗", layout="wide")

API_KEY = "eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6Ijg3YTI4ODI2YTc0OTRjODNiM2JkYTYzMDYxMGQxMWRjIiwiaCI6Im11cm11cjY0In0="
client = openrouteservice.Client(key=API_KEY)

# Initialize session state
if 'start_coords' not in st.session_state:
    st.session_state.start_coords = None
if 'end_coords' not in st.session_state:
    st.session_state.end_coords = None
if 'routes' not in st.session_state:
    st.session_state.routes = []
if 'selected_route_index' not in st.session_state:
    st.session_state.selected_route_index = 0

# Helper Functions
def format_distance(meters: float, units: str = "km") -> str:
    """Format distance in meters to km or miles with 2 decimal places."""
    if units == "mi":
        miles = meters / 1609.344
        return f"{miles:.2f} mi"
    km = meters / 1000.0
    return f"{km:.2f} km"

def format_duration(seconds: float) -> str:
    """Format duration in seconds to hours and minutes."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"

def autocomplete(query: str, max_results: int = 5) -> List[Dict]:
    """Get location suggestions from OpenRouteService."""
    if not query or len(query.strip()) < 2:
        return []
    
    try:
        # Try autocomplete first
        results = client.pelias_autocomplete(text=query)
        suggestions = []
        
        if results and 'features' in results:
            for feat in results['features']:
                if 'geometry' not in feat:
                    continue
                props = feat['properties']
                coords = feat['geometry']['coordinates']
                suggestions.append({
                    "label": props.get('label', props.get('name', 'Unknown')),
                    "lat": coords[1],
                    "lon": coords[0]
                })
        
        # If autocomplete fails or returns no results, try search
        if not suggestions:
            search_results = client.pelias_search(text=query)
            if search_results and 'features' in search_results:
                for feat in search_results['features']:
                    if 'geometry' not in feat:
                        continue
                    props = feat['properties']
                    coords = feat['geometry']['coordinates']
                    suggestions.append({
                        "label": props.get('label', props.get('name', 'Unknown')),
                        "lat": coords[1],
                        "lon": coords[0]
                    })
        
        # Remove duplicates while preserving order
        seen = set()
        unique_suggestions = []
        for s in suggestions:
            if s['label'] not in seen and all(x is not None for x in [s['lat'], s['lon']]):
                seen.add(s['label'])
                unique_suggestions.append(s)
        
        return unique_suggestions[:max_results]
    except Exception as e:
        st.error(f"Error getting suggestions: {str(e)}")
        return []

def get_route(start_coords: Tuple[float, float], end_coords: Tuple[float, float], 
              profile: str = "driving-car", alternatives: bool = True) -> List[Dict]:
    """Calculate route between two points."""
    try:
        coords = [
            (start_coords[1], start_coords[0]),  # (lon, lat)
            (end_coords[1], end_coords[0]),
        ]
        
        # Basic parameters without alternatives
        params = {
            "coordinates": coords,
            "profile": profile,
            "format": "geojson",
            "instructions": True
        }
        
        response = client.directions(**params)
        routes = [response]
        
        # If alternatives are requested, make additional calls with slightly modified coordinates
        if alternatives:
            try:
                # Try slightly different paths by adjusting coordinates
                offset = 0.0005  # About 50 meters
                variations = [
                    [(coords[0][0], coords[0][1] + offset), coords[1]],  # Shift start north
                    [(coords[0][0] + offset, coords[0][1]), coords[1]],  # Shift start east
                ]
                
                for var_coords in variations:
                    try:
                        alt_params = params.copy()
                        alt_params["coordinates"] = var_coords
                        alt_response = client.directions(**alt_params)
                        if alt_response and alt_response != response:
                            routes.append(alt_response)
                    except:
                        continue
                        
            except:
                # If generating alternatives fails, continue with the main route
                pass
        
        # Extract and return all features
        all_features = []
        for r in routes:
            if 'features' in r:
                all_features.extend(r['features'])
            else:
                all_features.append(r)
        
        return all_features
    except Exception as e:
        st.error(f"Error calculating route: {str(e)}")
        return []

def route_between(src_coords, dest_coords):
    try:
        route = client.directions(
            coordinates=[src_coords, dest_coords],
            profile='driving-car',
            format='geojson'
        )
        return route
    except Exception:
        return None

# -------------------------
# Graph / Algorithm helpers
# -------------------------
def haversine_distance(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    # Returns distance in meters between two (lat, lon) points
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    R = 6371000.0
    hav = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 2 * R * math.asin(math.sqrt(hav))

def build_graph_from_coords(coords_latlon: List[Tuple[float, float]]):
    # nodes: list of (lat, lon); adjacency matrix with weights (meters); edges only between consecutive points
    nodes = list(coords_latlon)
    n = len(nodes)
    adj = [[0.0 if i==j else float('inf') for j in range(n)] for i in range(n)]
    # Connect consecutive points (polyline neighbors)
    for i in range(n-1):
        d = haversine_distance(nodes[i], nodes[i+1])
        adj[i][i+1] = d
        adj[i+1][i] = d
    return nodes, adj

def dijkstra_trace(adj_matrix: List[List[float]], start_index: int):
    # Record each step: distances, visited, predecessors, current node
    n = len(adj_matrix)
    dist = [float('inf')] * n
    prev = [None] * n
    visited = [False] * n
    dist[start_index] = 0.0
    steps = []

    for _ in range(n):
        # select unvisited node with smallest dist
        u = None
        best = float('inf')
        for i in range(n):
            if not visited[i] and dist[i] < best:
                best = dist[i]
                u = i
        # Record current selection (could be None if unreachable)
        steps.append({
            'distances': list(dist),
            'visited': list(visited),
            'predecessors': list(prev),
            'current': u,
        })

        if u is None:
            break

        visited[u] = True

        # relax neighbors
        for v in range(n):
            w = adj_matrix[u][v]
            if w != float('inf') and not visited[v]:
                alt = dist[u] + w
                if alt < dist[v]:
                    dist[v] = alt
                    prev[v] = u

    # final state
    steps.append({
        'distances': list(dist),
        'visited': list(visited),
        'predecessors': list(prev),
        'current': None,
    })
    return steps

# UI Components
st.title("🌆 Smart City Navigator")
st.markdown("""
    Find the best route between any two locations with real-time traffic and multiple route options.
    Start by entering your locations below.
""")

# Main Layout
col1, col2 = st.columns(2)

with col1:
    # Source Location
    st.subheader("🚩 Starting Point")
    start_query = st.text_input("Enter starting location", 
                               help="Type to see suggestions. Supports partial matches.")
    
    start_suggestions = autocomplete(start_query) if len(start_query) >= 2 else []
    
    # Always show selectbox, but with appropriate options
    start_labels = [s["label"] for s in start_suggestions] if start_suggestions else ["Select starting point"]
    selected_start = st.selectbox(
        "Select starting point",
        options=start_labels,
        key="start_select",
        help="Select from the suggestions below"
    )
    
    # Store coordinates when a valid selection is made
    if start_suggestions and selected_start != "Select starting point":
        selected_start_place = next((s for s in start_suggestions if s["label"] == selected_start), None)
        if selected_start_place:
            st.session_state.start_coords = (selected_start_place["lat"], selected_start_place["lon"])
            st.session_state.start_place = selected_start_place["label"]

with col2:
    # Destination
    st.subheader("📍 Destination")
    end_query = st.text_input("Enter destination", 
                             help="Type to see suggestions. Supports partial matches.")
    
    end_suggestions = autocomplete(end_query) if len(end_query) >= 2 else []
    
    # Always show selectbox, but with appropriate options
    end_labels = [s["label"] for s in end_suggestions] if end_suggestions else ["Select destination"]
    selected_end = st.selectbox(
        "Select destination",
        options=end_labels,
        key="end_select",
        help="Select from the suggestions below"
    )
    
    # Store coordinates when a valid selection is made
    if end_suggestions and selected_end != "Select destination":
        selected_end_place = next((s for s in end_suggestions if s["label"] == selected_end), None)
        if selected_end_place:
            st.session_state.end_coords = (selected_end_place["lat"], selected_end_place["lon"])
            st.session_state.end_place = selected_end_place["label"]

# Route Options
st.subheader("🛣️ Route Options")
col3, col4, col5 = st.columns(3)

with col3:
    transport_mode = st.selectbox("Transportation Mode",
                                ["driving-car", "cycling-regular", "foot-walking"],
                                format_func=lambda x: {
                                    "driving-car": "🚗 Car",
                                    "cycling-regular": "🚲 Bicycle",
                                    "foot-walking": "🚶 Walking"
                                }[x])

with col4:
    show_alternatives = st.checkbox("Show alternative routes", value=True,
                                  help="Display multiple route options if available")

with col5:
    units = st.selectbox("Distance Units", ["km", "mi"])

# Calculate Route Button
if st.button("🔍 Find Best Route", type="primary"):
    if st.session_state.start_coords and st.session_state.end_coords:
        with st.spinner("Calculating the best route..."):
            routes = get_route(
                st.session_state.start_coords,
                st.session_state.end_coords,
                transport_mode,
                show_alternatives
            )
            
            if routes:
                st.session_state.routes = routes
                
                # Create map centered on start point
                m = folium.Map(
                    location=[st.session_state.start_coords[0], st.session_state.start_coords[1]],
                    zoom_start=12
                )
                
                # Add routes to map with different colors
                colors = ['blue', 'red', 'green']
                for idx, route in enumerate(routes):
                    coords = [(p[1], p[0]) for p in route['geometry']['coordinates']]
                    
                    # Main route info
                    distance = route['properties']['segments'][0]['distance']
                    duration = route['properties']['segments'][0]['duration']
                    
                    # Display route metrics
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric(
                            f"Route {idx + 1} Distance", 
                            format_distance(distance, units)
                        )
                    with col2:
                        st.metric(
                            f"Estimated Time", 
                            format_duration(duration)
                        )
                    
                    # Add route to map
                    folium.PolyLine(
                        coords,
                        weight=4,
                        color=colors[idx % len(colors)],
                        opacity=0.8
                    ).add_to(m)
                    
                    # Show turn-by-turn directions
                    with st.expander(f"📝 Turn-by-turn directions - Route {idx + 1}"):
                        steps = route['properties']['segments'][0]['steps']
                        for i, step in enumerate(steps, 1):
                            instruction = step['instruction']
                            distance = format_distance(step['distance'], units)
                            duration = format_duration(step['duration'])
                            
                            # Add appropriate emoji based on the maneuver
                            icon = "➡️"
                            if "turn right" in instruction.lower():
                                icon = "↪️"
                            elif "turn left" in instruction.lower():
                                icon = "↩️"
                            elif "continue" in instruction.lower():
                                icon = "⬆️"
                            
                            st.write(f"{icon} **Step {i}:** {instruction}")
                            st.caption(f"Distance: {distance} • Duration: {duration}")
                
                # Add markers for start and end points
                folium.Marker(
                    [st.session_state.start_coords[0], st.session_state.start_coords[1]],
                    popup="Start",
                    icon=folium.Icon(color='green', icon='info-sign')
                ).add_to(m)
                
                folium.Marker(
                    [st.session_state.end_coords[0], st.session_state.end_coords[1]],
                    popup="Destination",
                    icon=folium.Icon(color='red', icon='info-sign')
                ).add_to(m)
                
                # Display the map
                st.subheader("🗺️ Route Map")
                folium_static(m)
                
                # Add download option
                st.download_button(
                    label="📥 Download Route Data (GeoJSON)",
                    data=json.dumps(routes[0], indent=2),
                    file_name="route.geojson",
                    mime="application/geo+json",
                )
                # -------------------------
                # Build adjacency matrix and run Dijkstra trace for the primary route
                # Store trace in session state (UI for stepping rendered below)
                # -------------------------
                try:
                    primary = routes[0]
                    # Extract polyline coordinates in lat,lon
                    poly_coords = [(c[1], c[0]) for c in primary['geometry']['coordinates']]

                    nodes, adj = build_graph_from_coords(poly_coords)
                    trace = dijkstra_trace(adj, 0)  # start at node 0
                    # Store in session for stepping
                    st.session_state._algo_nodes = nodes
                    st.session_state._algo_adj = adj
                    st.session_state._algo_trace = trace
                    # only set step to 0 when freshly generating trace
                    st.session_state._algo_step = 0
                except Exception as e:
                    st.error(f"Error building algorithm trace: {e}")
            else:
                st.error("Could not find a route between these locations.")
    else:
        st.warning("Please select both starting point and destination.")

# Footer
st.markdown("---")
st.markdown("""
    💡 **Tips:**
    - Type at least 3 characters to see location suggestions
    - Compare different transport modes for the best route
    - Check alternative routes when available
    - Download route data for offline use
""")

# -------------------------
# Algorithm Trace UI (persistent)
# -------------------------
if '_algo_trace' in st.session_state and st.session_state.get('_algo_trace'):
    trace = st.session_state._algo_trace
    nodes = st.session_state._algo_nodes
    adj = st.session_state._algo_adj
    if '_algo_step' not in st.session_state:
        st.session_state._algo_step = 0

    total_steps = max(len(trace)-1, 0)

    tab1, tab2 = st.tabs(["Step-by-step", "Final path"])

    # callbacks
    def _next_step():
        st.session_state._algo_step = min(st.session_state._algo_step + 1, len(trace)-1)

    def _prev_step():
        st.session_state._algo_step = max(st.session_state._algo_step - 1, 0)

    with tab1:
        st.subheader("🔬 Algorithm Trace - Dijkstra (step-by-step)")
        col_a, col_b = st.columns([1,2])
        with col_a:
            st.write(f"Step {st.session_state._algo_step} of {total_steps}")
            st.button("Previous Step", on_click=_prev_step)
            st.button("Next Step", on_click=_next_step)
            step_idx = st.number_input("Jump to step", min_value=0, max_value=len(trace)-1, value=st.session_state._algo_step, step=1, key='trace_step_ctrl')
            # allow manual override of step index
            if step_idx != st.session_state._algo_step:
                st.session_state._algo_step = int(step_idx)

        with col_b:
            cur = trace[st.session_state._algo_step]
            # Build a simple table representation
            labels = [f"N{i}" for i in range(len(nodes))]
            table_rows = []
            for i, row in enumerate(adj):
                display_row = ["∞" if val==float('inf') else f"{val:.1f}" for val in row]
                table_rows.append(dict(zip(labels, display_row)))
            st.markdown("**Adjacency matrix (meters)**")
            st.table(table_rows)

            st.markdown("**Current step details**")
            st.write(f"Current node: {cur['current']}")
            st.write(f"Distances: {cur['distances']}")
            st.write(f"Visited: {cur['visited']}")
            st.write(f"Predecessors: {cur['predecessors']}")

            # Draw map for this step
            mm = folium.Map(location=[nodes[0][0], nodes[0][1]], zoom_start=13)
            # draw all nodes
            for i, (lat, lon) in enumerate(nodes):
                color = 'gray'
                if cur['visited'][i]:
                    color = 'blue'
                folium.CircleMarker([lat, lon], radius=4, color=color, fill=True).add_to(mm)

            # draw edges
            for i in range(len(nodes)-1):
                folium.PolyLine([nodes[i], nodes[i+1]], color='lightgray', weight=2).add_to(mm)

            # highlight current path from start to the current node using predecessors
            target = cur['current'] if cur['current'] is not None else None
            if target is not None:
                path = []
                u = target
                while u is not None:
                    path.append(nodes[u])
                    u = cur['predecessors'][u]
                path = list(reversed(path))
                if len(path) > 1:
                    folium.PolyLine(path, color='red', weight=4, opacity=0.8).add_to(mm)

            st.subheader("Algorithm visualization")
            folium_static(mm)

    with tab2:
        st.subheader("✅ Final path (reconstructed)")
        # Use the final step (last in trace) to reconstruct shortest paths
        final = trace[-1]
        # attempt to reconstruct path to the last node
        dest_idx = len(nodes) - 1
        path = []
        u = dest_idx
        if final['predecessors'][u] is None and final['distances'][u] == float('inf'):
            st.warning("Destination unreachable from start in the computed graph.")
        else:
            while u is not None:
                path.append(nodes[u])
                u = final['predecessors'][u]
            path = list(reversed(path))
            total_distance = final['distances'][dest_idx]
            st.markdown(f"**Path length:** {len(path)} nodes — **Distance:** {total_distance:.1f} meters")
            # show as a table with node index and coordinates
            path_rows = []
            for i, (lat, lon) in enumerate(path):
                path_rows.append({"order": i, "lat": lat, "lon": lon})
            st.table(path_rows)

            # map
            mm2 = folium.Map(location=[nodes[0][0], nodes[0][1]], zoom_start=13)
            # full polyline (all nodes)
            folium.PolyLine(nodes, color='lightgray', weight=2).add_to(mm2)
            # highlight final path
            if len(path) > 1:
                folium.PolyLine(path, color='green', weight=5, opacity=0.9).add_to(mm2)
            # markers
            folium.Marker(path[0], popup='Start', icon=folium.Icon(color='green')).add_to(mm2)
            folium.Marker(path[-1], popup='Destination', icon=folium.Icon(color='red')).add_to(mm2)
            st.subheader("Final path visualization")
            folium_static(mm2)
