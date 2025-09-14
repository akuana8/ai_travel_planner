# src/location_api.py
import os
import time
import functools
import requests
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

IPINFO_API_KEY = os.getenv("IPINFO_API_KEY")


# --- Retry decorator (local copy, biar tidak circular import) ---
def retry_request(max_retries: int = 3, base_delay: float = 1.5, backoff: float = 2.0):
    def deco(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = base_delay
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except requests.exceptions.RequestException:
                    if attempt >= max_retries:
                        raise
                    time.sleep(delay)
                    delay *= backoff
        return wrapper
    return deco


@retry_request()
def get_user_location():
    """
    Ambil lokasi user berdasarkan IP (via ipinfo API).
    Return dict {city, region, country, latitude, longitude} atau None kalau gagal.
    """
    try:
        url = f"https://ipinfo.io/json?token={IPINFO_API_KEY}" if IPINFO_API_KEY else "https://ipinfo.io/json"
        resp = requests.get(url, timeout=8)
        resp.raise_for_status()
        data = resp.json()

        lat, lon = (None, None)
        if data.get("loc") and "," in data["loc"]:
            lat, lon = map(float, data["loc"].split(","))

        return {
            "city": data.get("city"),
            "region": data.get("region"),
            "country": data.get("country"),
            "latitude": lat,
            "longitude": lon,
        }
    except Exception as e:
        logger.warning(f"Gagal ambil lokasi user: {e}")
        return None





