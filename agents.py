import os
import logging
from typing import Any, Dict
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import initialize_agent, AgentType, Tool, tool
from langchain_core.rate_limiters import InMemoryRateLimiter

from src.location_api import get_user_location
from src.weather_api import get_weather
from src.transportation_api import get_transportation
from src.events_api import get_events
from src.utils import map_to_day_type

load_dotenv()

# --- Logging setup ---
logger = logging.getLogger("travel_agent")
logging.basicConfig(level=logging.INFO)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))

rate_limiter = InMemoryRateLimiter(
    requests_per_second=1,
    check_every_n_seconds=1,
    max_bucket_size=1,
)

# --- LLM pilihan ---
# llm = ChatOpenAI(
#     model=OPENAI_MODEL,
#     temperature=LLM_TEMPERATURE,
#     api_key=OPENAI_API_KEY,
#     max_retries=3,
#     request_timeout=120,
#     rate_limiter=rate_limiter
# )
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    max_tokens=None,
    max_retries=2,
    timeout=120,
    rate_limiter=rate_limiter
)

# --- Helper default city ---
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

# --- Wrappers untuk Tools (langsung return teks rapi) ---
def _wrap_search_flights(origin_city: str, destination_city: str, date: str):
    """Cari penerbangan antar kota."""
    from .flights_api import search_flights
    origin = _default_city(origin_city)
    if not origin or not destination_city or not date:
        return "✈️ Flights\n• No flight data (missing parameters)."
    try:
        results = search_flights(origin, destination_city, date)
        if not results:
            return "✈️ Flights\n• No flights found."
        lines = [f"• {r['airline']} – {origin} → {destination_city} — ${r['price']}" for r in results]
        return "✈️ Flights\n" + "\n".join(lines)
    except Exception as e:
        return f"✈️ Flights\n• Error: {e}"

def _wrap_weather(city: str, date: str):
    """Lihat prakiraan cuaca."""
    city = _default_city(city)
    if not city:
        return "⛅ Weather\n• No city provided."
    try:
        data = get_weather(city)
        return f"⛅ Weather\n• {city} on {date}: {data['weather']}, {data['temp_c']}°C"
    except Exception as e:
        return f"⛅ Weather\n• Error: {e}"

def _wrap_transport(city: str, destination: str = None, mode: str = "transit"):
    """Cari transportasi lokal."""
    city = _default_city(city)
    if not city:
        return "🚖 Transport\n• No city provided."
    try:
        results = get_transportation(city)
        if not results:
            return "🚖 Transport\n• No transport data."
        lines = [f"• {r['name']}: {r['price']}" for r in results]
        return "🚖 Transport\n" + "\n".join(lines)
    except Exception as e:
        return f"🚖 Transport\n• Error: {e}"

def _wrap_events(city: str, date: str):
    """Cari acara lokal."""
    city = _default_city(city)
    if not city:
        return "🎭 Events\n• No city provided."
    try:
        results = get_events(city, date)
        if not results:
            return "🎭 Events\n• No events found."
        lines = [f"• {r['name']} — {r['venue']}, {r['date']} — {r['price']}" for r in results]
        return "🎭 Events\n" + "\n".join(lines)
    except Exception as e:
        return f"🎭 Events\n• Error: {e}"

@tool
def airbnb_search(city: str, day_name: str, limit: int = 5):
    """
    Search for available Airbnb listings in database.
    Example input: city="Jakarta", day="Sunday", limit=5
    """
    from src.rag import query_airbnb
    if not city:
        return "🏠 Airbnb\n• No city provided."
    try:
        day_type = map_to_day_type(day_name) if day_name else None
        df = query_airbnb(city, day_type=day_type, limit=limit)
        if df.empty:
            return "🏠 Airbnb\n• No listings found."
        lines = [
            f"• {row['room_type']} — ${round(row['price'])}/night — ⭐{row['overall_rating']}"
            for _, row in df.iterrows()
        ]
        return "🏠 Airbnb\n" + "\n".join(lines)
    except Exception as e:
        return f"🏠 Airbnb\n• Error: {e}"

def _wrap_places(city: str, limit: int = 5):
    """Cari tempat wisata populer dari database."""
    from src.rag import query_places
    city = _default_city(city)
    if not city:
        return "📍 Places\n• No city provided."
    try:
        df = query_places(city, limit=limit)
        if df.empty:
            return "📍 Places\n• No places found."
        lines = [f"• {row['name']}" for _, row in df.iterrows()]
        return "📍 Places\n" + "\n".join(lines)
    except Exception as e:
        return f"📍 Places\n• Error: {e}"

# --- Tools ---
tools = [
    Tool(name="Flight_Search", func=_wrap_search_flights, description="Cari penerbangan. Input: origin_city, destination_city, date."),
    Tool(name="Weather_Search", func=_wrap_weather, description="Lihat prakiraan cuaca. Input: city, date."),
    Tool(name="Transportation_Search", func=_wrap_transport, description="Cari transportasi lokal. Input: city, destination, mode."),
    Tool(name="Events_Search", func=_wrap_events, description="Cari acara lokal. Input: city, date."),
    airbnb_search,
    Tool(name="Place_Search", func=_wrap_places, description="Cari tempat wisata populer dari database. Input: city, limit."),
]

# --- Prompt bilingual ---
SYSTEM_PROMPT = (
    "You are a smart travel assistant.\n"
    "⚠️ Rules:\n"
    "1. ALWAYS use the tools (Flight_Search, Airbnb_Search, Weather_Search, "
    "Events_Search, Transportation_Search, Place_Search) before answering.\n"
    "2. STRICTLY return structured output with sections + emojis + bullet points.\n"
    "3. Do not give generic advice unless all tools return empty.\n"
    "4. Answer in the SAME language as the user's question.\n"
)

# --- Inisialisasi Agent ---
travel_agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.OPENAI_MULTI_FUNCTIONS,
    verbose=False,   # 🚀 tidak spam log
    handle_parsing_errors=True,
    max_iterations=6,
    agent_kwargs={"system_message": SYSTEM_PROMPT},
)

# --- Helper unwrap ---
def unwrap_output(result: dict) -> str:
    """Extract clean string output from agent result."""
    if not result:
        return ""
    if "output" in result and isinstance(result["output"], str):
        return result["output"].strip()
    if "output" in result:
        return str(result["output"])
    return str(result)

# --- Fungsi utama ---
def ask_travel_agent(query: str) -> str:
    """Ask the travel agent and get clean structured response."""
    try:
        result = travel_agent.invoke({"input": query})
        return unwrap_output(result)
    except Exception as e:
        return f"Error while processing query: {e}"

def generate_itinerary(destination: str, start_date: str, days: int = 3, preferences: str = "") -> Dict[str, Any]:
    """Generate structured travel itinerary."""
    try:
        pref_text = preferences or "No specific preferences."
        prompt = (
            f"Create a {days}-day itinerary for {destination} starting {start_date}.\n"
            f"User preferences: {pref_text}\n\n"
            f"Use available tools (Flight_Search, Airbnb_Search, Weather_Search, "
            f"Events_Search, Transportation_Search, Place_Search).\n"
            f"Format: Day X - Morning / Afternoon / Evening / Night.\n"
            f"Include estimated duration, cost, and one local tip per day.\n"
            f"Answer in the SAME language as the user's question.\n"
        )
        result = travel_agent.invoke({"input": prompt})
        itinerary_text = unwrap_output(result)
        return {
            "destination": destination,
            "start_date": start_date,
            "days": days,
            "preferences": preferences,
            "itinerary_text": itinerary_text,
        }
    except Exception as e:
        return {"error": str(e)}

