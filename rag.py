# src/rag.py
import pandas as pd
import os
import logging
import pickle
from sqlalchemy import text
from .database import get_engine
from .utils import haversine_distance

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# --- Direktori untuk simpan FAISS & metadata ---
VECTORDIR = "vectorstores"
os.makedirs(VECTORDIR, exist_ok=True)

AIRBNB_INDEX_PATH = os.path.join(VECTORDIR, "airbnb_faiss")
PLACES_INDEX_PATH = os.path.join(VECTORDIR, "places_faiss")
AIRBNB_META_PATH = os.path.join(VECTORDIR, "airbnb_meta.pkl")
PLACES_META_PATH = os.path.join(VECTORDIR, "places_meta.pkl")

# --- Embeddings ---
def get_embeddings():
    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# ==========================================================
# Query Data (from DB)
# ==========================================================
def query_airbnb(city: str, day_type: str = None, limit: int = 5) -> pd.DataFrame:
    if not city:
        return pd.DataFrame()

    sql = "SELECT * FROM airbnb_listings WHERE LOWER(city) = LOWER(:city)"
    params = {"city": city}
    if day_type:
        sql += " AND day_type = :day_type"
        params["day_type"] = day_type
    sql += f" ORDER BY overall_rating DESC NULLS LAST LIMIT {int(limit)}"

    try:
        with get_engine().connect() as conn:
            df = pd.read_sql(text(sql), conn, params=params)
        return df
    except Exception as e:
        logger.error(f"Error in query_airbnb: {e}", exc_info=True)
        return pd.DataFrame()


def query_places(city: str, limit: int = 5) -> pd.DataFrame:
    if not city:
        return pd.DataFrame()
    sql = "SELECT * FROM places WHERE LOWER(city) = LOWER(:city) AND category='attraction' LIMIT :limit"
    try:
        with get_engine().connect() as conn:
            df = pd.read_sql(text(sql), conn, params={"city": city, "limit": limit})
        return df
    except Exception as e:
        logger.error(f"Error in query_places: {e}", exc_info=True)
        return pd.DataFrame()

# ==========================================================
# Build / Load FAISS Index
# ==========================================================
def build_index_from_df(df: pd.DataFrame, text_column: str, index_path: str, meta_path: str):
    if df.empty:
        logger.warning("No data to build index")
        return None

    embeddings = get_embeddings()
    texts = df[text_column].astype(str).tolist()
    metadatas = df.to_dict(orient="records")

    vectorstore = FAISS.from_texts(texts, embeddings, metadatas=metadatas)
    vectorstore.save_local(index_path)
    with open(meta_path, "wb") as f:
        pickle.dump(metadatas, f)
    logger.info(f"FAISS index saved to {index_path}, metadata saved to {meta_path}")
    return vectorstore

def load_index(index_path: str, meta_path: str):
    embeddings = get_embeddings()
    if not os.path.exists(index_path):
        logger.warning(f"{index_path} not found. Build index first.")
        return None, []

    vectorstore = FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)
    with open(meta_path, "rb") as f:
        metadatas = pickle.load(f)
    return vectorstore, metadatas

# ==========================================================
# Airbnb <-> Places Nearby
# ==========================================================
def query_airbnb_near_place(city: str, place_name: str = None, day_type: str = None,
                            limit: int = 5, max_distance_km: float = 2.0,
                            latitude: float = None, longitude: float = None) -> pd.DataFrame:
    df_airbnb = query_airbnb(city, day_type=day_type, limit=100)
    if df_airbnb.empty:
        return df_airbnb

    # Tentukan koordinat target
    if place_name:
        df_place = query_places(city, limit=100)
        target = df_place[df_place["name"].str.lower() == place_name.lower()]
        if target.empty:
            return pd.DataFrame()
        lat_target, lon_target = target.iloc[0]["latitude"], target.iloc[0]["longitude"]
    elif latitude is not None and longitude is not None:
        lat_target, lon_target = latitude, longitude
    else:
        return pd.DataFrame()

    df_airbnb["distance_km"] = df_airbnb.apply(
        lambda row: haversine_distance(row["latitude"], row["longitude"], lat_target, lon_target),
        axis=1
    )
    return df_airbnb[df_airbnb["distance_km"] <= max_distance_km].sort_values("distance_km").head(limit)

def query_places_near_airbnb(city: str, airbnb_id: int = None, latitude: float = None,
                             longitude: float = None, limit: int = 5, max_distance_km: float = 2.0) -> pd.DataFrame:
    df_places = query_places(city, limit=100)
    if df_places.empty:
        return df_places

    # Tentukan koordinat target
    if airbnb_id:
        df_airbnb = query_airbnb(city, limit=100)
        target = df_airbnb[df_airbnb.get("id") == airbnb_id]
        if target.empty:
            return pd.DataFrame()
        lat_target, lon_target = target.iloc[0]["latitude"], target.iloc[0]["longitude"]
    elif latitude is not None and longitude is not None:
        lat_target, lon_target = latitude, longitude
    else:
        return pd.DataFrame()

    df_places["distance_km"] = df_places.apply(
        lambda row: haversine_distance(row["latitude"], row["longitude"], lat_target, lon_target),
        axis=1
    )
    return df_places[df_places["distance_km"] <= max_distance_km].sort_values("distance_km").head(limit)

# ==========================================================
# Build Index CSV → FAISS
# ==========================================================
def build_airbnb_index_from_csv(csv_path: str):
    df = pd.read_csv(csv_path)
    return build_index_from_df(df, text_column="room_type", index_path=AIRBNB_INDEX_PATH, meta_path=AIRBNB_META_PATH)

def build_places_index_from_csv(csv_path: str):
    df = pd.read_csv(csv_path)
    return build_index_from_df(df, text_column="name", index_path=PLACES_INDEX_PATH, meta_path=PLACES_META_PATH)

# ==========================================================
# Search via FAISS
# ==========================================================
def search_faiss(vectorstore: FAISS, query: str, k: int = 5):
    if vectorstore is None:
        return []
    docs = vectorstore.similarity_search(query, k=k)
    return [doc.metadata for doc in docs]

