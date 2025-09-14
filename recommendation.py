import os
import pandas as pd
import numpy as np
import logging
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Setup logger
logger = logging.getLogger(__name__)

load_dotenv()


# =========================
# Load Data
# =========================
def load_listings(source="db"):
    """Load Airbnb listings from Neon DB or CSV fallback"""
    try:
        if source == "csv":
            logger.info("Loading listings from CSV...")
            return pd.read_csv("data/airbnb_cleaned.csv")
        elif source == "db":
            logger.info("Loading listings from database...")
            engine = create_engine(os.getenv("DATABASE_URL"))
            query = "SELECT * FROM airbnb_listings"
            return pd.read_sql(query, engine)
    except Exception as e:
        logger.error(f"Error loading listings: {e}")
        return pd.DataFrame()


def load_places(source="db"):
    """Load places (tourist attractions)"""
    try:
        if source == "csv":
            logger.info("Loading places from CSV...")
            return pd.read_csv("data/places.csv")
        elif source == "db":
            logger.info("Loading places from database...")
            engine = create_engine(os.getenv("DATABASE_URL"))
            query = "SELECT * FROM places"
            return pd.read_sql(query, engine)
    except Exception as e:
        logger.error(f"Error loading places: {e}")
        return pd.DataFrame()


# =========================
# Default Recommendation
# =========================
def recommend_default(listings, city, top_n=5):
    """Recommend listings by default ranking rules per city"""
    logger.info(f"Running default recommendation for city: {city}, top_n={top_n}")
    city_listings = listings[listings["city"].str.lower() == city.lower()]

    if city_listings.empty:
        logger.warning(f"No listings found for city: {city}")
        return pd.DataFrame()

    ranked = city_listings.sort_values(
        by=[
            "overall_rating",
            "reputation_score",
            "cleanliness",
            "walk_score",
            "distance_to_city_center",
            "distance_to_metro",
            "nearby_attractions"
        ],
        ascending=[False, False, False, False, True, True, True]
    )
    logger.info(f"Default recommendation produced {len(ranked)} results for {city}")
    return ranked.head(top_n)


# =========================
# User Preference Recommendation
# =========================
def recommend_with_preferences(listings, city=None, filters=None, sort_by=None, top_n=5):
    """
    Recommend listings by applying user filters + custom sort.
    Bisa dipanggil langsung dengan city_listings (city=None).
    """
    logger.info(f"Running preference-based recommendation for city={city}, filters={filters}, sort_by={sort_by}")

    if city:
        city_listings = listings[listings["city"].str.lower() == city.lower()].copy()
    else:
        city_listings = listings.copy()

    if city_listings.empty:
        logger.warning(f"No listings found for city={city}")
        return pd.DataFrame()

    # Apply filters
    if filters:
        for key, value in filters.items():
            if key in city_listings.columns:
                if city_listings[key].dtype == "object":
                    # Case-insensitive & partial match
                    before_count = len(city_listings)
                    city_listings = city_listings[
                        city_listings[key].str.lower().str.contains(str(value).lower())
                    ]
                    logger.info(f"Filter applied: {key}={value}, reduced {before_count} → {len(city_listings)} rows")
                else:
                    before_count = len(city_listings)
                    city_listings = city_listings[city_listings[key] == value]
                    logger.info(f"Filter applied: {key}={value}, reduced {before_count} → {len(city_listings)} rows")

    # Sorting (harga ascending, rating/score descending)
    if sort_by and sort_by in city_listings.columns:
        ascending = True if sort_by in [
            "price", "distance_to_city_center", "distance_to_metro", "distance_to_place"
        ] else False
        logger.info(f"Sorting by {sort_by}, ascending={ascending}")
        city_listings = city_listings.sort_values(by=sort_by, ascending=ascending)

    logger.info(f"Returning {min(top_n, len(city_listings))} recommendations")
    return city_listings.head(top_n)


# =========================
# Recommendation Near a Place
# =========================
def recommend_near_place(listings, places, city, place_name, filters=None, sort_by=None, top_n=5):
    """Recommend listings near a given place, with optional filters and sort"""
    logger.info(f"Running near-place recommendation for city={city}, place={place_name}")

    city_places = places[places["city"].str.lower() == city.lower()]
    target_place = city_places[city_places["name"].str.lower() == place_name.lower()]

    if target_place.empty:
        logger.error(f"Place '{place_name}' not found in {city}")
        raise ValueError(f"Place '{place_name}' not found in {city}")

    place_lat, place_lng = target_place.iloc[0][["latitude", "longitude"]]

    city_listings = listings[listings["city"].str.lower() == city.lower()].copy()
    if city_listings.empty:
        logger.warning(f"No listings found for city={city}")
        return pd.DataFrame()

    # Hitung jarak euclidean sederhana
    city_listings["distance_to_place"] = np.sqrt(
        (city_listings["latitude"] - place_lat) ** 2 +
        (city_listings["longitude"] - place_lng) ** 2
    )
    logger.info(f"Calculated distance_to_place for {len(city_listings)} listings")

    # Apply user preferences + sort
    if filters or sort_by:
        return recommend_with_preferences(city_listings, city=None, filters=filters, sort_by=sort_by, top_n=top_n)
    else:
        ranked = city_listings.sort_values("distance_to_place", ascending=True)
        logger.info(f"Returning {min(top_n, len(ranked))} nearest listings")
        return ranked.head(top_n)





