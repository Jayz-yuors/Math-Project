# utils/geocode.py
import openrouteservice
from config.api_keys import OPENROUTESERVICE_API_KEY

client = openrouteservice.Client(key=OPENROUTESERVICE_API_KEY)

def get_coordinates(address):
    try:
        geocode = client.pelias_search(text=address)
        if geocode and geocode['features']:
            coords = geocode['features'][0]['geometry']['coordinates']
            lon, lat = coords
            return (lat, lon)
    except Exception as e:
        print("Error in geocoding:", e)
    return None
