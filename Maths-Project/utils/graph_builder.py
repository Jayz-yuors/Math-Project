# utils/graph_builder.py
import networkx as nx
import math

def build_graph(coord1, coord2, distance):
    """Build a simple weighted graph between two coordinates."""
    G = nx.Graph()
    G.add_node("Start", pos=coord1)
    G.add_node("Destination", pos=coord2)
    G.add_edge("Start", "Destination", weight=distance)
    return G

def euclidean_distance(coord1, coord2):
    """Compute straight-line (Euclidean) distance between two coordinates."""
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    return math.sqrt((lat2 - lat1)**2 + (lon2 - lon1)**2)
