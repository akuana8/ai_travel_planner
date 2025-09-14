# src/database.py
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL tidak ditemukan. Pastikan sudah di .env")

engine = create_engine(DATABASE_URL, future=True)

def get_engine():
    return engine

# ======================
# Itinerary
# ======================
def save_itinerary(user_id: str, destination: str, itinerary_text: str):
    """Simpan itinerary ke Neon"""
    try:
        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO itineraries (user_id, destination, itinerary)
                    VALUES (:u, :d, :it)
                """),
                {"u": user_id, "d": destination, "it": itinerary_text}
            )
            res = conn.execute(text("SELECT MAX(id) FROM itineraries"))
            row = res.fetchone()
            return int(row[0]) if row and row[0] else None
    except SQLAlchemyError as e:
        print("[DB][Itinerary] ❌", e)
        raise

def get_itinerary(user_id: str):
    """Ambil itinerary terakhir berdasarkan user_id dari Neon"""
    try:
        with engine.connect() as conn:
            res = conn.execute(
                text("""
                    SELECT id, destination, itinerary, created_at
                    FROM itineraries
                    WHERE user_id = :u
                    ORDER BY id DESC
                    LIMIT 1
                """),
                {"u": user_id}
            )
            row = res.fetchone()
            if not row:
                return None
            return {"id": row[0], "destination": row[1], "itinerary": row[2], "created_at": str(row[3])}
    except SQLAlchemyError as e:
        print("[DB][Itinerary] ❌", e)
        raise

# ======================
# Airbnb
# ======================
def query_airbnb(city: str, limit: int = 10):
    """Ambil Airbnb listings dari Neon berdasarkan kota"""
    try:
        with engine.connect() as conn:
            res = conn.execute(
                text("""
                    SELECT *
                    FROM airbnb_listings
                    WHERE city = :city
                    ORDER BY rating DESC
                    LIMIT :limit
                """),
                {"city": city, "limit": limit}
            )
            rows = res.fetchall()
            return [dict(row._mapping) for row in rows]
    except SQLAlchemyError as e:
        print("[DB][Airbnb] ❌", e)
        return []

# ======================
# Places
# ======================
def query_places(city: str, limit: int = 10):
    """Ambil rekomendasi tempat wisata dari Neon berdasarkan kota"""
    try:
        with engine.connect() as conn:
            res = conn.execute(
                text("""
                    SELECT *
                    FROM places
                    WHERE city = :city
                    ORDER BY rating DESC
                    LIMIT :limit
                """),
                {"city": city, "limit": limit}
            )
            rows = res.fetchall()
            return [dict(row._mapping) for row in rows]
    except SQLAlchemyError as e:
        print("[DB][Places] ❌", e)
        return []

