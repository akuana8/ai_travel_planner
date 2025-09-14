import logging
import os
from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from src.agent_graph import ask_travel_agent, generate_itinerary
from src.weather_api import get_weather
from src.events_api import get_events
from src.flights_api import search_flights
from src.transportation_api import get_transportation
from src.location_api import get_user_location
from src.database import save_itinerary, get_itinerary
from src.pdf_generator import create_itinerary_pdf
from src.rag import query_airbnb, query_places

# --- Load environment variables ---
load_dotenv()

# --- Logging setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("travel_planner")

# --- FastAPI app setup ---
app = FastAPI(
    title="AI Travel Planner Assistant",
    version="3.1.1",
    description="Backend API untuk AI Travel Planner Assistant 🚀"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # sebaiknya nanti dibatasi ke domain frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Root Endpoint ---
@app.get("/")
def root():
    logger.info("Root endpoint accessed")
    return {"message": "AI Travel Planner API is running 🚀"}


# --- Agent Chat ---
@app.post("/ask")
def ask_agent(payload: dict = Body(..., example={"query": "Apa rekomendasi liburan ke Paris?"})):
    query = payload.get("query")
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")

    try:
        logger.info(f"User asked agent: {query}")
        answer = ask_travel_agent(query)
        return {"query": query, "answer": answer}
    except Exception as e:
        logger.exception("Error in /ask endpoint")
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")


# --- Weather ---
@app.get("/weather")
def weather(city: str = Query(..., description="Nama kota, contoh: Paris")):
    logger.info(f"Fetching weather for {city}")
    try:
        res = get_weather(city)
        if isinstance(res, dict) and res.get("error"):
            raise HTTPException(status_code=404, detail=res.get("error"))
        return res
    except Exception as e:
        logger.exception("Error fetching weather")
        raise HTTPException(status_code=500, detail=f"Weather error: {str(e)}")


# --- Events ---
@app.get("/events")
def events(city: str = Query(...), date: str = Query(None, description="Format YYYY-MM-DD")):
    logger.info(f"Fetching events for {city} on {date}")
    try:
        res = get_events(city, date)
        if isinstance(res, dict) and res.get("error"):
            raise HTTPException(status_code=404, detail=res.get("error"))
        return res
    except Exception as e:
        logger.exception("Error fetching events")
        raise HTTPException(status_code=500, detail=f"Events error: {str(e)}")


# --- Flights ---
@app.get("/flights")
def flights(
    origin: str = Query(None, description="Kode IATA asal, contoh: CGK"),
    destination: str = Query(..., description="Kode IATA tujuan, contoh: CDG"),
    date: str = Query(..., description="Format YYYY-MM-DD"),
):
    logger.info(f"Searching flights: {origin} -> {destination} on {date}")
    try:
        res = search_flights(origin, destination, date)
        if isinstance(res, dict) and res.get("error"):
            raise HTTPException(status_code=404, detail=res.get("error"))
        return res
    except Exception as e:
        logger.exception("Error fetching flights")
        raise HTTPException(status_code=500, detail=f"Flights error: {str(e)}")


# --- Transportation ---
@app.get("/transportation")
def transportation(city: str = Query(...)):
    logger.info(f"Fetching transportation for {city}")
    try:
        res = get_transportation(city)
        if isinstance(res, dict) and res.get("error"):
            raise HTTPException(status_code=404, detail=res.get("error"))
        return res
    except Exception as e:
        logger.exception("Error fetching transportation")
        raise HTTPException(status_code=500, detail=f"Transportation error: {str(e)}")


# --- User Location ---
@app.get("/location")
def location():
    logger.info("Detecting user location")
    try:
        loc = get_user_location()
        return loc or {"error": "Unable to detect location"}
    except Exception as e:
        logger.exception("Error detecting location")
        raise HTTPException(status_code=500, detail=f"Location error: {str(e)}")


# --- Airbnb ---
@app.get("/airbnb")
def airbnb(city: str = Query(...), day_type: str = Query(None), limit: int = Query(5)):
    logger.info(f"Querying Airbnb in {city} (day_type={day_type}, limit={limit})")
    try:
        df = query_airbnb(city, day_type=day_type, limit=limit)
        return df.to_dict(orient="records")
    except Exception as e:
        logger.exception("Error fetching Airbnb listings")
        raise HTTPException(status_code=500, detail=f"Airbnb error: {str(e)}")


# --- Places ---
@app.get("/places")
def places(city: str = Query(...), limit: int = Query(5)):
    logger.info(f"Querying Places in {city} (limit={limit})")
    try:
        df = query_places(city, limit=limit)
        return df.to_dict(orient="records")
    except Exception as e:
        logger.exception("Error fetching places")
        raise HTTPException(status_code=500, detail=f"Places error: {str(e)}")


# --- Itinerary Generate ---
@app.post("/itinerary/generate")
def api_generate_itinerary(payload: dict = Body(...)):
    destination = payload.get("destination")
    start_date = payload.get("start_date")
    days = payload.get("days", 3)
    preferences = payload.get("preferences", "")

    if not destination or not start_date:
        raise HTTPException(status_code=400, detail="destination and start_date required")

    logger.info(f"Generating itinerary for {destination}, {days} days, from {start_date}")
    try:
        res = generate_itinerary(destination, start_date, days, preferences)

        # 🔧 kalau string, bungkus jadi dict
        if isinstance(res, str):
            res = {"itinerary_text": res}

        if res.get("error"):
            raise HTTPException(status_code=500, detail=res.get("error"))

        return res
    except Exception as e:
        logger.exception("Error generating itinerary")
        raise HTTPException(status_code=500, detail=f"Itinerary error: {str(e)}")

# --- Itinerary Save ---
@app.post("/itinerary/save")
def api_save_itinerary(payload: dict = Body(...)):
    user_id = payload.get("user_id")
    destination = payload.get("destination")
    itinerary_text = payload.get("itinerary_text")

    if not all([user_id, destination, itinerary_text]):
        raise HTTPException(status_code=400, detail="Missing user_id, destination or itinerary_text")

    try:
        new_id = save_itinerary(user_id, destination, itinerary_text)
        logger.info(f"Itinerary saved for {user_id} to {destination} (id={new_id})")
        return {"status": "ok", "id": new_id}
    except Exception as e:
        logger.exception("Error saving itinerary")
        raise HTTPException(status_code=500, detail=f"Save itinerary error: {str(e)}")


# --- Itinerary Get ---
@app.get("/itinerary")
def api_get_itinerary(user_id: str = Query(...)):
    try:
        row = get_itinerary(user_id)
        if not row:
            logger.info(f"No itinerary found for {user_id}")
            return {"status": "empty"}
        return row
    except Exception as e:
        logger.exception("Error fetching itinerary")
        raise HTTPException(status_code=500, detail=f"Get itinerary error: {str(e)}")


# --- Itinerary PDF ---
@app.get("/itinerary/pdf")
def api_itinerary_pdf(
    destination: str = Query(...),
    start_date: str = Query(...),
    days: int = Query(3),
    preferences: str = Query(""),
):
    logger.info(f"Generating itinerary PDF for {destination} ({start_date})")
    try:
        res = generate_itinerary(destination, start_date, days, preferences)

        # 🔧 kalau string, bungkus jadi dict
        if isinstance(res, str):
            res = {"itinerary_text": res}

        if res.get("error"):
            raise HTTPException(status_code=500, detail=res.get("error"))

        title = f"Itinerary - {destination} ({start_date})"
        path = create_itinerary_pdf(title, res.get("itinerary_text", ""))
        return {"pdf_path": path}
    except Exception as e:
        logger.exception("Error generating itinerary PDF")
        raise HTTPException(status_code=500, detail=f"PDF error: {str(e)}")

