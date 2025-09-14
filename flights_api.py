# src/flights_api.py
import os
import requests
from dotenv import load_dotenv
from .utils import cached, retry_request, get_airport_code

load_dotenv()
AMADEUS_API_KEY = os.getenv("AMADEUS_API_KEY")
AMADEUS_API_SECRET = os.getenv("AMADEUS_API_SECRET")
AM_BASE = "https://test.api.amadeus.com"

@retry_request()
def _get_access_token():
    if not AMADEUS_API_KEY or not AMADEUS_API_SECRET:
        raise RuntimeError("Missing Amadeus API credentials")
    token_url = f"{AM_BASE}/v1/security/oauth2/token"
    data = {"grant_type": "client_credentials", "client_id": AMADEUS_API_KEY, "client_secret": AMADEUS_API_SECRET}
    r = requests.post(token_url, data=data, timeout=10)
    r.raise_for_status()
    return r.json().get("access_token")

@cached
@retry_request()
def search_flights(origin_city: str, destination_city: str, date: str):
    if not destination_city or not date:
        return {"error": "destination_city and date required"}
    origin_iata = get_airport_code(origin_city) if origin_city else None
    dest_iata = get_airport_code(destination_city)
    if not dest_iata or len(str(dest_iata)) != 3:
        return {"error": f"Failed to determine IATA for {destination_city}"}
    if not origin_iata:
        origin_iata = "CGK"  # default fallback

    token = _get_access_token()
    url = f"{AM_BASE}/v2/shopping/flight-offers"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"originLocationCode": origin_iata, "destinationLocationCode": dest_iata, "departureDate": date, "adults": 1, "max": 5}
    r = requests.get(url, headers=headers, params=params, timeout=15)
    r.raise_for_status()
    data = r.json().get("data", [])
    results = []
    for f in data:
        try:
            seg = f.get("itineraries", [])[0].get("segments", [])[0]
            results.append({
                "price_total": f.get("price", {}).get("total"),
                "currency": f.get("price", {}).get("currency"),
                "airlines": f.get("validatingAirlineCodes", []),
                "from": seg.get("departure", {}).get("iataCode"),
                "to": seg.get("arrival", {}).get("iataCode"),
                "departure_at": seg.get("departure", {}).get("at"),
                "arrival_at": seg.get("arrival", {}).get("at"),
            })
        except Exception:
            continue
    return {"origin": origin_iata, "destination": dest_iata, "date": date, "count": len(results), "items": results}

print("search_flights loaded:", 'search_flights' in globals())

