import os
import requests
import logging
from fastapi import FastAPI
from dotenv import load_dotenv
from sqlalchemy import create_engine, Table, Column, Integer, String, Float, MetaData
from sqlalchemy.dialects.postgresql import insert

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Load .env
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Koneksi ke Neon
engine = create_engine(DATABASE_URL)
metadata = MetaData()

# Definisi tabel places (harus sama seperti di Neon)
places = Table(
    "places",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(255)),
    Column("category", String(100)),
    Column("city", String(100)),
    Column("latitude", Float),
    Column("longitude", Float),
    Column("ticket_price", Float, nullable=True),
)

# Normalisasi nama kota → supaya seragam
CITY_NORMALIZATION = {
    "lisboa": "lisbon",
    "lisbon": "lisbon",
    "roma": "rome",
    "rome": "rome",
    "athína": "athens",
    "athens": "athens",
    "wien": "vienna",
    "vienna": "vienna",
    "amsterdam": "amsterdam",
    "barcelona": "barcelona",
    "berlin": "berlin",
    "budapest": "budapest",
    "paris": "paris",
    "london": "london",
}

# Query Overpass per kota
city_queries = {
    "amsterdam": """
    [out:json][timeout:60];
    area["name"="Amsterdam"]["boundary"="administrative"]->.searchArea;
    (node(area.searchArea)["tourism"="attraction"];
     way(area.searchArea)["tourism"="attraction"];
     relation(area.searchArea)["tourism"="attraction"];);
    out center;
    """,
    "athens": """
    [out:json][timeout:60];
    (node(around:30000,37.9838,23.7275)["tourism"="attraction"];
     way(around:30000,37.9838,23.7275)["tourism"="attraction"];
     relation(around:30000,37.9838,23.7275)["tourism"="attraction"];);
    out center;
    """,
    "barcelona": """
    [out:json][timeout:60];
    area["name"="Barcelona"]["boundary"="administrative"]->.searchArea;
    (node(area.searchArea)["tourism"="attraction"];
     way(area.searchArea)["tourism"="attraction"];
     relation(area.searchArea)["tourism"="attraction"];);
    out center;
    """,
    "berlin": """
    [out:json][timeout:60];
    area["name"="Berlin"]["boundary"="administrative"]->.searchArea;
    (node(area.searchArea)["tourism"="attraction"];
     way(area.searchArea)["tourism"="attraction"];
     relation(area.searchArea)["tourism"="attraction"];);
    out center;
    """,
    "budapest": """
    [out:json][timeout:60];
    area["name"="Budapest"]["boundary"="administrative"]->.searchArea;
    (node(area.searchArea)["tourism"="attraction"];
     way(area.searchArea)["tourism"="attraction"];
     relation(area.searchArea)["tourism"="attraction"];);
    out center;
    """,
    "lisboa": """
    [out:json][timeout:60];
    area["name"="Lisboa"]["boundary"="administrative"]->.searchArea;
    (node(area.searchArea)["tourism"="attraction"];
     way(area.searchArea)["tourism"="attraction"];
     relation(area.searchArea)["tourism"="attraction"];);
    out center;
    """,
    "london": """
    [out:json][timeout:60];
    area["name"="London"]["boundary"="administrative"]->.searchArea;
    (node(area.searchArea)["tourism"="attraction"];
     way(area.searchArea)["tourism"="attraction"];
     relation(area.searchArea)["tourism"="attraction"];);
    out center;
    """,
    "paris": """
    [out:json][timeout:60];
    area["name"="Paris"]["boundary"="administrative"]->.searchArea;
    (node(area.searchArea)["tourism"="attraction"];
     way(area.searchArea)["tourism"="attraction"];
     relation(area.searchArea)["tourism"="attraction"];);
    out center;
    """,
    "rome": """
    [out:json][timeout:60];
    area["name"="Rome"]["boundary"="administrative"]->.searchArea;
    (node(area.searchArea)["tourism"="attraction"];
     way(area.searchArea)["tourism"="attraction"];
     relation(area.searchArea)["tourism"="attraction"];);
    out center;
    """,
    "vienna": """
    [out:json][timeout:60];
    area["name"="Vienna"]["boundary"="administrative"]->.searchArea;
    (node(area.searchArea)["tourism"="attraction"];
     way(area.searchArea)["tourism"="attraction"];
     relation(area.searchArea)["tourism"="attraction"];);
    out center;
    """,
}

# FastAPI app
app = FastAPI()

@app.get("/")
def root():
    return {"message": "Places API is running 🚀"}

@app.post("/import_places/{city}")
def import_places(city: str):
    city = city.lower()
    if city not in city_queries:
        return {"error": f"Kota {city} tidak tersedia."}

    normalized_city = CITY_NORMALIZATION.get(city, city)
    overpass_url = "http://overpass-api.de/api/interpreter"
    query = city_queries[city]

    response = requests.get(overpass_url, params={"data": query}, timeout=90)
    data = response.json()

    inserted = 0
    with engine.begin() as conn:
        for element in data.get("elements", []):
            name = element.get("tags", {}).get("name")
            if not name:
                name = f"Unknown-{element.get('id')}"

            category = element.get("tags", {}).get("tourism", "attraction")
            lat = element.get("lat") or element.get("center", {}).get("lat")
            lon = element.get("lon") or element.get("center", {}).get("lon")

            stmt = insert(places).values(
                name=name,
                category=category,
                city=normalized_city,
                latitude=lat,
                longitude=lon,
                ticket_price=None,
            )

            # Update jika duplikat
            do_update_stmt = stmt.on_conflict_do_update(
                index_elements=["city", "name"],
                set_={
                    "category": category,
                    "latitude": lat,
                    "longitude": lon,
                    "ticket_price": None,
                }
            )
            conn.execute(do_update_stmt)
            inserted += 1

    return {
        "city": normalized_city,
        "inserted": inserted,
        "debug_count": len(data.get("elements", [])),
    }

@app.post("/import_all")
def import_all():
    results = {}
    overpass_url = "http://overpass-api.de/api/interpreter"

    for city, query in city_queries.items():
        normalized_city = CITY_NORMALIZATION.get(city, city)
        try:
            response = requests.get(overpass_url, params={"data": query}, timeout=90)
            data = response.json()
            inserted = 0

            with engine.begin() as conn:
                for element in data.get("elements", []):
                    name = element.get("tags", {}).get("name")
                    if not name:
                        name = f"Unknown-{element.get('id')}"

                    category = element.get("tags", {}).get("tourism", "attraction")
                    lat = element.get("lat") or element.get("center", {}).get("lat")
                    lon = element.get("lon") or element.get("center", {}).get("lon")

                    stmt = insert(places).values(
                        name=name,
                        category=category,
                        city=normalized_city,
                        latitude=lat,
                        longitude=lon,
                        ticket_price=None,
                    )

                    do_update_stmt = stmt.on_conflict_do_update(
                        index_elements=["city", "name"],
                        set_={
                            "category": category,
                            "latitude": lat,
                            "longitude": lon,
                            "ticket_price": None,
                        }
                    )
                    conn.execute(do_update_stmt)
                    inserted += 1

            results[normalized_city] = {
                "inserted": inserted,
                "debug_count": len(data.get("elements", [])),
            }
        except Exception as e:
            results[normalized_city] = {"error": str(e)}

    return {"imported": results}

