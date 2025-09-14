# src/events_api.py
import os
import requests
from dotenv import load_dotenv
from typing import Optional
from .utils import cached, retry_request

load_dotenv()
TICKETMASTER_API_KEY = os.getenv("TICKETMASTER_API_KEY")

@cached
@retry_request()
def get_events(city: str, date: Optional[str] = None):
    if not city:
        return {"error": "City required"}
    if not TICKETMASTER_API_KEY:
        return {"error": "TICKETMASTER_API_KEY missing in .env"}
    url = "https://app.ticketmaster.com/discovery/v2/events.json"
    params = {"apikey": TICKETMASTER_API_KEY, "city": city, "size": 10, "sort": "date,asc"}
    if date:
        params["startDateTime"] = f"{date}T00:00:00Z"
    r = requests.get(url, params=params, timeout=12)
    if r.status_code != 200:
        return {"error": f"Ticketmaster error for {city}", "status": r.status_code}
    data = r.json()
    events = []
    for e in data.get("_embedded", {}).get("events", [])[:10]:
        dates = e.get("dates", {}).get("start", {})
        venues = e.get("_embedded", {}).get("venues", [])
        events.append({
            "name": e.get("name"),
            "date": dates.get("localDate"),
            "time": dates.get("localTime"),
            "url": e.get("url"),
            "venue": venues[0].get("name") if venues else None
        })
    return events
