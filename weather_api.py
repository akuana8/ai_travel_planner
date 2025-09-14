import os
import requests
import datetime as dt
from dotenv import load_dotenv
from .utils import cached, retry_request

load_dotenv()
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

@cached
@retry_request()
def get_weather_forecast(city: str, date: str, lang: str = "id"):
    """
    Ambil ramalan cuaca untuk kota tertentu di tanggal tertentu (YYYY-MM-DD).
    OpenWeather API memberikan data per 3 jam, jadi kita ambil rata-rata suhu
    dan kondisi yang paling sering muncul di hari itu.
    """
    try:
        if not city:
            return {"error": "City required"}
        if not OPENWEATHER_API_KEY:
            return {"error": "OPENWEATHER_API_KEY missing in .env"}
        
        url = "https://api.openweathermap.org/data/2.5/forecast"
        params = {"q": city, "appid": OPENWEATHER_API_KEY, "units": "metric", "lang": "en"}
        r = requests.get(url, params=params, timeout=10)
        if r.status_code != 200:
            return {"error": f"Failed to fetch forecast for {city}", "status": r.status_code}
        
        data = r.json()
        forecast_list = data.get("list", [])

        # Filter sesuai tanggal
        target_date = dt.datetime.strptime(date, "%Y-%m-%d").date()
        filtered = [f for f in forecast_list if dt.datetime.fromtimestamp(f["dt"]).date() == target_date]

        if not filtered:
            return {"error": f"No forecast data available for {city} on {date}"}

        # Hitung rata-rata suhu
        temps = [f["main"]["temp"] for f in filtered]
        feels = [f["main"]["feels_like"] for f in filtered]
        hums = [f["main"]["humidity"] for f in filtered]
        winds = [f["wind"]["speed"] for f in filtered]
        weathers = [f["weather"][0]["description"] for f in filtered]

        avg_temp = sum(temps) / len(temps)
        avg_feels = sum(feels) / len(feels)
        avg_hum = sum(hums) / len(hums)
        avg_wind = sum(winds) / len(winds)
        
        # Ambil kondisi cuaca yang paling sering muncul
        from collections import Counter
        common_weather = Counter(weathers).most_common(1)[0][0]

        return {
            "city": data.get("city", {}).get("name", city),
            "date": str(target_date),
            "avg_temp_c": round(avg_temp, 1),
            "avg_feels_like": round(avg_feels, 1),
            "weather": common_weather,
            "humidity": round(avg_hum, 1),
            "wind": round(avg_wind, 1),
        }

    except Exception as e:
        print(f"[ERROR get_weather_forecast] {e}")
        return {"error": str(e)}


@cached
@retry_request()
def get_weather(city: str, lang: str = "id"):
    """
    Ambil kondisi cuaca saat ini untuk kota tertentu.
    """
    try:
        if not city:
            return {"error": "City required"}
        if not OPENWEATHER_API_KEY:
            return {"error": "OPENWEATHER_API_KEY missing in .env"}

        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {"q": city, "appid": OPENWEATHER_API_KEY, "units": "metric", "lang": "en"}
        r = requests.get(url, params=params, timeout=10)
        if r.status_code != 200:
            return {"error": f"Failed to fetch current weather for {city}", "status": r.status_code}

        data = r.json()
        weather_desc = data.get("weather", [{}])[0].get("description", "")

        return {
            "city": data.get("name", city),
            "date": str(dt.datetime.now().date()),
            "temp_c": data.get("main", {}).get("temp"),
            "feels_like": data.get("main", {}).get("feels_like"),
            "weather": weather_desc,
            "humidity": data.get("main", {}).get("humidity"),
            "wind": data.get("wind", {}).get("speed"),
        }
    except Exception as e:
        print(f"[ERROR get_weather] {e}")
        return {"error": str(e)}
