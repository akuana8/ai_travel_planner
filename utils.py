# src/utils.py
import os
import time
import functools
import datetime
from datetime import datetime
import requests
from dotenv import load_dotenv
from cachetools import TTLCache
import dateparser

load_dotenv()

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

# Cache: TTL 10 menit
cache = TTLCache(maxsize=200, ttl=600)

def retry_request(max_retries: int = 3, base_delay: float = 1.5, backoff: float = 2.0):
    def deco(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = base_delay
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except requests.exceptions.RequestException as e:
                    if attempt >= max_retries:
                        raise
                    time.sleep(delay)
                    delay *= backoff
        return wrapper
    return deco

def cached(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        key = f"{func.__name__}:{args}:{tuple(sorted(kwargs.items()))}"
        if key in cache:
            return cache[key]
        result = func(*args, **kwargs)
        cache[key] = result
        return result
    return wrapper

def parse_date(date_str: str):
    """
    Normalisasi berbagai format tanggal ke string 'YYYY-MM-DD'.
    Contoh:
      - "05-12-2025"  -> "2025-12-05"
      - "5/12/2025"   -> "2025-12-05"
      - "5 Dec 2025"  -> "2025-12-05"
      - "5 Desember 2025" -> "2025-12-05"
    """
    if not date_str:
        return None
    parsed = dateparser.parse(date_str, languages=["en", "id"])
    if not parsed:
        raise ValueError(f"Invalid date format: {date_str}")
    return parsed.strftime("%Y-%m-%d")

def map_to_day_type(user_input: str):
    """
    Mengembalikan 'weekdays' atau 'weekends' berdasarkan nama hari atau tanggal.
    Support bahasa Inggris dan Indonesia.
    """
    if not user_input:
        return None

    user_input = user_input.strip().lower()
    weekdays_en = ["monday", "tuesday", "wednesday", "thursday", "friday"]
    weekends_en = ["saturday", "sunday"]
    weekdays_id = ["senin", "selasa", "rabu", "kamis", "jumat"]
    weekends_id = ["sabtu", "minggu"]

    if user_input in weekdays_en or user_input in weekdays_id:
        return "weekdays"
    if user_input in weekends_en or user_input in weekends_id:
        return "weekends"

    try:
        normalized_date = parse_date(user_input)
        d = datetime.strptime(normalized_date, "%Y-%m-%d")
        return "weekdays" if d.weekday() < 5 else "weekends"
    except Exception:
        return None

@cached
@retry_request()
def convert_currency(amount: float, to_currency: str = "USD", from_currency: str = "EUR"):
    url = f"https://api.exchangerate.host/convert?from={from_currency}&to={to_currency}&amount={amount}"
    r = requests.get(url, timeout=8)
    r.raise_for_status()
    data = r.json()
    return round(data.get("result", 0.0), 2)

def format_price(amount, currency="EUR"):
    symbols = {"EUR": "€", "USD": "$", "IDR": "Rp", "GBP": "£"}
    symbol = symbols.get(currency.upper(), currency.upper())
    try:
        return f"{symbol}{float(amount):,.2f}"
    except Exception:
        return f"{symbol}{amount}"

AIRPORT_CODES = {
    "jakarta": "CGK", "paris": "CDG", "amsterdam": "AMS", "berlin": "BER", "rome": "FCO",
    "vienna": "VIE", "budapest": "BUD", "athens": "ATH", "barcelona": "BCN", "lisbon": "LIS",
    "london": "LHR", "madrid": "MAD", "zurich": "ZRH", "brussels": "BRU", "oslo": "OSL",
    "stockholm": "ARN", "helsinki": "HEL", "new york": "JFK", "los angeles": "LAX",
    "chicago": "ORD", "san francisco": "SFO", "miami": "MIA", "toronto": "YYZ", "vancouver": "YVR",
    "singapore": "SIN", "kuala lumpur": "KUL", "bangkok": "BKK", "hong kong": "HKG",
    "tokyo": "HND", "seoul": "ICN", "beijing": "PEK", "shanghai": "PVG", "delhi": "DEL", "mumbai": "BOM",
    "cairo": "CAI", "johannesburg": "JNB", "nairobi": "NBO", "lagos": "LOS", "cape town": "CPT",
}

@cached
@retry_request()
def get_airport_code(city: str):
    if not city:
        return None
    code = AIRPORT_CODES.get(city.lower())
    if code:
        return code
    if not GOOGLE_MAPS_API_KEY:
        return "Unknown"
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {"query": f"airport in {city}", "key": GOOGLE_MAPS_API_KEY, "type": "airport"}
    r = requests.get(url, params=params, timeout=8)
    r.raise_for_status()
    data = r.json()
    if data.get("results"):
        name = data["results"][0].get("name", "")
        import re
        m = re.search(r"\b([A-Z]{3})\b", name)
        if m:
            return m.group(1)
        return name
    return "Unknown"

# ==========================================================
# Landmark Mapping
# ==========================================================

LANDMARK_TO_CITY = {
    # Paris
    "eiffel": "paris",
    "louvre": "paris",
    "notre dame": "paris",
    "arc de triomphe": "paris",
    # London
    "big ben": "london",
    "tower bridge": "london",
    "buckingham": "london",
    # Rome
    "colosseum": "rome",
    "vatican": "rome",
    "pantheon": "rome",
    # Berlin
    "brandenburg": "berlin",
    "berlin wall": "berlin",
    # Barcelona
    "sagrada familia": "barcelona",
    "park guell": "barcelona",
}


def map_landmark_to_city(text: str):
    """
    Pemetaan nama landmark terkenal ke nama kota.
    Return nama kota dalam lowercase jika ditemukan, else None.
    """
    if not text:
        return None
    text = text.lower()
    for landmark, city in LANDMARK_TO_CITY.items():
        if landmark in text:
            return city
    return None

# ==========================================================
# Guest & Nights Extraction
# ==========================================================

def extract_guests_and_nights(text: str):
    """
    Ekstrak jumlah tamu dan jumlah malam dari teks user.
    Contoh:
      - "3 orang 2 malam" -> (3, 2)
      - "2 malam untuk 5 orang" -> (5, 2)
      - default (jika tidak ada angka) -> (1, 1)
    """
    import re
    guests, nights = 1, 1  # default value

    if not text:
        return guests, nights

    g = re.search(r"(\d+)\s*orang", text.lower())
    n = re.search(r"(\d+)\s*malam", text.lower())

    if g:
        guests = int(g.group(1))
    if n:
        nights = int(n.group(1))

    return guests, nights

# ==========================================================
# Distance & Coordinates
# ==========================================================

def haversine_distance(lat1, lon1, lat2, lon2):
    """Hitung jarak dalam km antara dua koordinat"""
    import math
    R = 6371  # radius bumi (km)
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = math.sin(d_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c


def get_user_coordinates():
    """
    Ambil koordinat (latitude, longitude) dari lokasi user.
    Menggunakan location_api.get_user_location().
    """
    try:
        from src.location_api import get_user_location  # lazy import supaya tidak circular import

        loc = get_user_location()
        if loc and loc.get("latitude") and loc.get("longitude"):
            return loc["latitude"], loc["longitude"]
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"User coordinates detection failed: {e}")
    return None, None

def find_nearby_places(airbnb_lat, airbnb_lon, places, max_distance_km=2.0):
    """
    Cari tempat wisata (dari tabel places) yang dekat dengan koordinat Airbnb.
    
    Args:
        airbnb_lat (float): latitude airbnb
        airbnb_lon (float): longitude airbnb
        places (list[dict]): hasil query_places, masing-masing dict minimal ada lat & lon
        max_distance_km (float): batas jarak (default 2 km)
    
    Returns:
        list[dict]: tempat wisata terdekat
    """
    results = []
    for p in places:
        plat, plon = p.get("latitude"), p.get("longitude")
        if plat is None or plon is None:
            continue
        dist = haversine_distance(airbnb_lat, airbnb_lon, plat, plon)
        if dist <= max_distance_km:
            p["distance_km"] = round(dist, 2)
            results.append(p)
    
    # urutkan dari yang paling dekat
    results.sort(key=lambda x: x["distance_km"])
    return results














