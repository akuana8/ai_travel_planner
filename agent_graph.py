# src/agent_graph.py
import os
import logging
import datetime as dt
from typing import Any
from dotenv import load_dotenv
import re
import json
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_core.tools import StructuredTool
from langgraph.prebuilt import create_react_agent
from langchain.schema import AIMessage
from src.location_api import get_user_location
from src.weather_api import get_weather, get_weather_forecast
from src.transportation_api import get_transportation
from src.events_api import get_events
from src.utils import map_to_day_type, find_nearby_places
from src.rag import (
    query_airbnb,
    query_places,
    query_airbnb_near_place,
    query_places_near_airbnb,
    load_index,
    AIRBNB_INDEX_PATH,
    PLACES_INDEX_PATH,
    AIRBNB_META_PATH,
    PLACES_META_PATH,
)

# Setup
load_dotenv()
logger = logging.getLogger("travel_agent")
logging.basicConfig(level=logging.INFO)

# LLM setup (Gemini)
rate_limiter = InMemoryRateLimiter()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise EnvironmentError("❌ No GOOGLE_API_KEY found. Please set it in .env")

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    api_key=GOOGLE_API_KEY,
    max_retries=2,
    timeout=120,
    rate_limiter=rate_limiter,
)

# Load FAISS indexes + metadata 
airbnb_index, airbnb_meta = load_index(AIRBNB_INDEX_PATH, AIRBNB_META_PATH)
places_index, places_meta = load_index(PLACES_INDEX_PATH, PLACES_META_PATH)

# Helper: default city detection 
def _default_city(city: str | None) -> str | None:
    if city:
        return city
    try:
        loc = get_user_location()
        if isinstance(loc, dict):
            return loc.get("city")
    except Exception as e:
        logger.warning(f"Could not detect city automatically: {e}")
    return None

# Tools
def tool_search_flights(origin_city: str, destination_city: str, date: str):
    origin = _default_city(origin_city)
    if not origin or not destination_city or not date:
        return {"error": "origin_city, destination_city, and date are required"}
    return search_flights(origin, destination_city, date)


def tool_weather_forecast(city: str, date: str):
    city = _default_city(city)
    if not city:
        return {"error": "City not provided"}
    return get_weather_forecast(city, date=date, lang="id")

def tool_transport(city: str, mode: str = "metro"):
    city = _default_city(city)
    if not city:
        return {"error": "City not provided"}
    return get_transportation(city)

def tool_events(city: str, date: str):
    city = _default_city(city)
    if not city:
        return {"error": "City not provided"}
    return get_events(city, date)

def tool_airbnb(city: str, day_name: str = None, limit: int = 5):
    if not city:
        return []
    day_type = map_to_day_type(day_name) if day_name else None
    df = query_airbnb(city, day_type=day_type, limit=limit)
    if df.empty:
        return []

    cols = [
        "capacity", "bedrooms", "room_type", "price", "rating",
        "latitude", "longitude", "city"
    ]
    df = df[[c for c in cols if c in df.columns]]

    return df.to_dict(orient="records")

def tool_places(city: str, limit: int = 5):
    if not city:
        return []
    df = query_places(city, limit=limit)
    return df.to_dict(orient="records") if not df.empty else []

def tool_nearby_places_from_airbnb(city: str, airbnb_lat: float, airbnb_lon: float, max_distance_km: float = 2.0):
    places = query_places_near_airbnb(city, latitude=airbnb_lat, longitude=airbnb_lon, limit=50).to_dict(orient="records")
    if not places:
        return "📍 No nearby attractions found"

    out = "📍 Nearby Places\n"
    for p in places:
        name = p.get("name", "Unknown place")
        distance = p.get("distance_km", "?")
        out += f"• Name: {name}, Distance: {distance} km\n"
    return out.strip()

# Register tools
tools = [
    StructuredTool.from_function(tool_search_flights, name="Flight_Search", description="Search flights."),
    StructuredTool.from_function(tool_airbnb, name="Airbnb_Search", description="Search Airbnb listings."),
    StructuredTool.from_function(tool_weather_forecast, name="Weather_Search", description="Get weather forecast."),
    StructuredTool.from_function(tool_events, name="Events_Search", description="Search events in city."),
    StructuredTool.from_function(tool_transport, name="Transportation_Search", description="Search transport options."),
    StructuredTool.from_function(tool_places, name="Place_Search", description="Search places/attractions."),
    StructuredTool.from_function(tool_nearby_places_from_airbnb, name="Nearby_Places_From_Airbnb", description="Find nearby attractions from Airbnb location."),
]

# System prompt
SYSTEM_PROMPT = f"""
You are a smart travel assistant.

⚠️ Rules:
1. ALWAYS use the available tools (Flight_Search, Airbnb_Search, Weather_Search, Events_Search, Transportation_Search, Place_Search, Nearby_Places_From_Airbnb) before answering.
2. STRICTLY follow this output format:

   ✈️ Flights
   🚖 Transportation
   🏨 Airbnb (up to 5 results)
   📍 Nearby Places (up to 5 results)
   ⛅ Weather
   🎭 Events

3. Keep section order even if empty. Skip empty sections.
4. Bullet points (•) for multiple items, no extra prose.
5. When user asks about Airbnb, ALSO call Nearby_Places_From_Airbnb using Airbnb’s latitude/longitude.
6. Answer in the SAME language as user input.
7. Today’s reference date: {dt.datetime.now().strftime("%Y-%m-%d %H:%M %B")}
"""

# Create agent
travel_agent = create_react_agent(
    model=llm,
    tools=tools,
    prompt=SYSTEM_PROMPT,
)

# Language detector
def detect_lang(text: str) -> str:
    if any(word in text.lower() for word in ["apa", "kapan", "bagaimana", "cuaca", "hujan", "awan", "suhu", "kelembapan"]):
        return "id"
    return "en"

# Ask agent
def ask_travel_agent(query: str) -> str:
    try:
        lang = detect_lang(query)
        response = travel_agent.invoke({"messages": [{"role": "user", "content": query}]})

        if hasattr(response, "content"):
            raw = response.content
        elif isinstance(response, dict) and "messages" in response:
            raw = response["messages"][-1].content
        else:
            raw = str(response)

        sections = ["✈️ Flights", "🚖 Transportation", "🏨 Airbnb", "📍 Nearby Places", "⛅ Weather", "🎭 Events"]
        out = ""
        for sec in sections:
            pattern = re.compile(rf"{re.escape(sec)}.*?(?=✈️|🚖|🏨|📍|⛅|🎭|$)", re.S)
            match = pattern.search(raw)
            if match:
                out += match.group().strip() + "\n\n"
            else:
                out += f"{sec}\n• -\n\n"

        if "🏨 Airbnb" in raw and ("latitude" in raw or "longitude" in raw):
            try:
                import json
                listings = re.findall(r"\{.*?\}", raw, re.S)
                for item in listings:
                    data = json.loads(item)
                    if "latitude" in data and "longitude" in data:
                        city = data.get("city")
                        lat, lon = data["latitude"], data["longitude"]
                        nearby = tool_nearby_places_from_airbnb(city, lat, lon)
                        out = out.replace("📍 Nearby Places\n• -", nearby)
                        break
            except Exception as e:
                logger.warning(f"Nearby places parse failed: {e}")

        out = re.sub(r"additional_kwargs.*", "", out)
        out = re.sub(r"response_metadata.*", "", out)
        out = re.sub(r"usage_metadata.*", "", out)

        return out.strip()

    except Exception as e:
        return f"❌ Error: {e}"

# Generate Itinerary
def generate_itinerary(destination: str, start_date: str, days: int = 3, preferences: str = "", lang: str = "en") -> dict:
    try:
        prompt = (
            f"Create a {days}-day itinerary for {destination} starting {start_date}.\n"
            f"Preferences: {preferences or 'No specific preferences'}.\n"
            "Use available tools (Flight_Search, Airbnb_Search, Weather_Search, "
            "Events_Search, Transportation_Search, Place_Search).\n"
            "Format: Day X - Morning / Afternoon / Evening / Night.\n"
            "Include estimated cost, duration, and 1 local tip per day.\n"
            f"Output the response in {'Indonesian' if lang == 'id' else 'English'}.\n"
        )

        response = travel_agent.invoke({"messages": [{"role": "user", "content": prompt}]})

        last_ai = None
        if isinstance(response, dict) and "messages" in response:
            for m in response["messages"]:
                if isinstance(m, AIMessage):
                    last_ai = m
        elif hasattr(response, "messages"):
            for m in response.messages:
                if isinstance(m, AIMessage):
                    last_ai = m

        raw = last_ai.content if last_ai else getattr(response, "content", str(response))

        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = {"itinerary_text": raw}

        return parsed

    except Exception as e:
        return {"error": str(e)}


