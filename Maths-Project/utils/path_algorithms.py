# utils/path_algorithms.py
import networkx as nx

def shortest_path_dijkstra(G):
    """Find shortest path and distance using Dijkstra’s algorithm."""
    try:
        path = nx.dijkstra_path(G, "Start", "Destination", weight='weight')
        distance = nx.dijkstra_path_length(G, "Start", "Destination", weight='weight')
        return path, distance
    except Exception as e:
        print("Error in Dijkstra:", e)
        return None, None
def shortest_path_astar(G):
    """Find shortest path and distance using A* algorithm."""
    try:
        path = nx.astar_path(G, "Start", "Destination", heuristic=lambda u, v: 0, weight='weight')
        distance = nx.astar_path_length(G, "Start", "Destination", heuristic=lambda u, v: 0, weight='weight')
        return path, distance
    except Exception as e:
        print("Error in A*:", e)
        return None, None
