import os
import requests
from dotenv import load_dotenv
from .utils import retry_request, cached

# Load API key dari .env
load_dotenv()
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

# Query transportasi yang akan dicoba
SEARCH_QUERIES = [
    "public transport",
    "bus station",
    "train station",
    "metro station",
    "airport"
]

@cached
@retry_request()
def get_transportation(city: str):
    """
    Ambil data transportasi publik dari Google Maps API.

    Args:
        city (str): Nama kota, misalnya "Paris"

    Returns:
        list[dict] | dict: List hasil transportasi publik, atau dict error
    """
    if not city:
        return {"error": "City required"}

    if not GOOGLE_MAPS_API_KEY:
        return {"error": "GOOGLE_MAPS_API_KEY missing in .env"}

    out = []
    for q in SEARCH_QUERIES:
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        params = {"query": f"{q} in {city}", "key": GOOGLE_MAPS_API_KEY}
        r = requests.get(url, params=params, timeout=12)
        r.raise_for_status()
        data = r.json()

        status = data.get("status")
        if status != "OK":
            return {
                "error": f"Google Maps API error: {status}",
                "message": data.get("error_message", "No details"),
                "raw": data
            }

        for p in data.get("results", []):
            out.append({
                "name": p.get("name"),
                "address": p.get("formatted_address"),
                "rating": p.get("rating"),
                "place_id": p.get("place_id"),
                "type": q
            })

    # Hapus duplikat berdasarkan place_id
    unique = {x["place_id"]: x for x in out}
    results = list(unique.values())

    if not results:
        return {"error": f"No transport results found for {city}"}

    return results[:15]  # batasin maksimal 15 hasil


@cached
@retry_request()
def get_transportation_detail(place_id: str):
    """
    Ambil detail tempat transportasi tertentu dari Google Maps API.
    Bisa ambil jam buka, foto, dsb.
    """
    if not GOOGLE_MAPS_API_KEY:
        return {"error": "GOOGLE_MAPS_API_KEY missing in .env"}

    url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "fields": "name,formatted_address,rating,opening_hours,photo,geometry",
        "key": GOOGLE_MAPS_API_KEY
    }
    r = requests.get(url, params=params, timeout=12)
    r.raise_for_status()
    data = r.json()

    status = data.get("status")
    if status != "OK":
        return {
            "error": f"Google Maps API error: {status}",
            "message": data.get("error_message", "No details"),
            "raw": data
        }

    return data.get("result", {})


