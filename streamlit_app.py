import os
import streamlit as st
import requests
import datetime as dt
import pandas as pd

# Backend URL
BACKEND = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="AI Travel Planner", layout="wide")
st.title("🌍 AI Travel Planner")

# Pilihan Bahasa
lang = st.sidebar.radio("🌐 Language / Bahasa", ["English", "Indonesia"], index=1)

# Dictionary teks berdasarkan bahasa
TEXTS = {
    "English": {
        "backend_ok": "✅ Backend Connected",
        "backend_warn": "⚠️ Backend Not Responding",
        "backend_err": "❌ Backend Down",
        "menu": [
            "🏠 Home",
            "🤖 Chat Agent",
            "🗺️ AI Itinerary",
            "⛅ Weather",
            "🎭 Events",
            "✈️ Flights",
            "🚖 Transport",
            "🏠 Airbnb",
            "📍 Places",
            "🧳 My Itinerary"
        ],
        "home_title": "👋 Welcome to AI Travel Planner",
        "home_desc": """
        **AI Travel Planner** helps you plan trips easily! ✈️  
        Main features:
        - 🤖 Chat with AI Travel Agent
        - 🗺️ Auto-generate Itinerary
        - ⛅ Check Weather
        - 🎭 See Events
        - ✈️ Find Flights
        - 🚖 Local Transport Info
        - 🏠 Find Best Airbnb
        - 📍 Tourist Attractions
        - 🧳 Save & Download Itinerary

        Select menu from the sidebar to start! 🚀
        """,
        "chat_input": "💬 Ask something to AI Travel Agent",
        "chat_btn": "Send Question",
        "chat_warn": "Please enter a question first.",
        "chat_loading": "AI is generating an answer...",
        "chat_answer": "AI Answer:",
        "chat_noanswer": "No answer available",
    },
    "Indonesia": {
        "backend_ok": "✅ Backend Tersambung",
        "backend_warn": "⚠️ Backend Tidak Merespons",
        "backend_err": "❌ Backend Mati",
        "menu": [
            "🏠 Home",
            "🤖 Chat Agent",
            "🗺️ AI Itinerary",
            "⛅ Cuaca",
            "🎭 Acara",
            "✈️ Penerbangan",
            "🚖 Transportasi",
            "🏠 Airbnb",
            "📍 Tempat Wisata",
            "🧳 Rencana Perjalanan"
        ],
        "home_title": "👋 Selamat Datang di AI Travel Planner",
        "home_desc": """
        **AI Travel Planner** membantumu merencanakan perjalanan dengan mudah! ✈️  
        Fitur-fitur utama:
        - 🤖 Chat dengan AI Travel Agent
        - 🗺️ Buat Itinerary Otomatis
        - ⛅ Cek Cuaca
        - 🎭 Lihat Event di Kota Tujuan
        - ✈️ Cari Tiket Pesawat
        - 🚖 Info Transportasi Lokal
        - 🏠 Cari Airbnb Terbaik
        - 📍 Rekomendasi Tempat Wisata
        - 🧳 Simpan & Download Itinerary

        Pilih menu di sebelah kiri untuk mulai! 🚀
        """,
        "chat_input": "💬 Tanya sesuatu ke AI Travel Agent",
        "chat_btn": "Kirim Pertanyaan",
        "chat_warn": "Masukkan pertanyaan dulu.",
        "chat_loading": "AI sedang memproses jawaban...",
        "chat_answer": "Jawaban AI:",
        "chat_noanswer": "Tidak ada jawaban",
    }
}

T = TEXTS[lang]

# Backend status
try:
    r = requests.get(f"{BACKEND}/", timeout=5)
    if r.ok:
        st.sidebar.success(T["backend_ok"])
    else:
        st.sidebar.error(T["backend_warn"])
except:
    st.sidebar.error(T["backend_err"])


# ---------------- Helper untuk Chat Agent ---------------- #
def render_chat_response(data: dict, lang: str = "id"):
    """
    Render jawaban dari Chat Agent.
    - lang: "id" untuk Bahasa Indonesia, "en" untuk English
    """
    LABELS = {
        "id": {
            "airbnb": "🏠 Pilihan Airbnb",
            "events": "🎭 Acara / Event",
            "transport": "🚖 Transportasi Lokal",
            "flights": "✈️ Penerbangan",
            "weather": "⛅ Cuaca",
            "price": "💶 Harga",
            "rating": "⭐ Rating",
            "capacity": "👥 Kapasitas",
            "distance": "📍 Jarak",
            "date": "📅 Tanggal",
            "location": "📍 Lokasi",
            "duration": "🕑 Durasi",
            "departure": "🛫 Keberangkatan",
            "arrival": "🛬 Kedatangan",
            "airline": "✈️ Maskapai",
        },
        "en": {
            "airbnb": "🏠 Airbnb Options",
            "events": "🎭 Events",
            "transport": "🚖 Local Transportation",
            "flights": "✈️ Flights",
            "weather": "⛅ Weather",
            "price": "💶 Price",
            "rating": "⭐ Rating",
            "capacity": "👥 Capacity",
            "distance": "📍 Distance",
            "date": "📅 Date",
            "location": "📍 Location",
            "duration": "🕑 Duration",
            "departure": "🛫 Departure",
            "arrival": "🛬 Arrival",
            "airline": "✈️ Airline",
        },
    }
    L = LABELS.get(lang, LABELS["id"])

    # ---------- Plain answer ----------
    if "answer" in data:
        formatted_answer = data["answer"].replace("\n", "  \n")
        st.markdown(formatted_answer)

    # ---------- Airbnb ----------
    if "airbnb" in data and data["airbnb"]:
        st.markdown(f"## {L['airbnb']}")
        for idx, ab in enumerate(data["airbnb"], 1):
            st.markdown(f"""
            **{idx}. {ab.get('name', 'Entire Home/Apt')}**  
            - {L['capacity']}: {ab.get('capacity', '?')}  
            - {L['price']}: €{ab.get('price_total', '?')} / night  
            - {L['distance']}: {ab.get('distance_center', '?')} km  
            - {L['rating']}: {ab.get('rating', 'N/A')}
            """)

    # ---------- Events ----------
    if "events" in data and data["events"]:
        st.markdown(f"## {L['events']}")
        for ev in data["events"]:
            st.markdown(f"""
            - **{ev.get('title', 'Event')}**  
              {L['date']}: {ev.get('date', '?')}  
              {L['location']}: {ev.get('location', '?')}  
              {L['price']}: {ev.get('price', 'Free')}
            """)

    # ---------- Transport ----------
    if "transport" in data and data["transport"]:
        st.markdown(f"## {L['transport']}")
        for tr in data["transport"]:
            st.markdown(f"""
            - **{tr.get('type', 'Transport')}**  
              {tr.get('duration', '')}  
              {L['price']}: {tr.get('price', 'N/A')}
            """)

    # ---------- Flights ----------
    if "flights" in data and data["flights"]:
        st.markdown(f"## {L['flights']}")
        for fl in data["flights"]:
            st.markdown(f"""
            - **{fl.get('airline', 'Airline')}**  
              {fl.get('origin', '')} → {fl.get('destination', '')}  
              {L['departure']}: {fl.get('departure', '')}  
              {L['arrival']}: {fl.get('arrival', '')}  
              {L['price']}: {fl.get('price', 'N/A')}
            """)

    # ---------- Weather ----------
    if "weather" in data and data["weather"]:
        st.markdown(f"## {L['weather']}")
        for w in data["weather"]:
            st.markdown(f"""
            - {w.get('city', '')} ({w.get('date', '')})  
              🌡️ {w.get('temp', '')}°C (feels {w.get('feels_like', '')}°C)  
              💧 {w.get('humidity', '')}%  
              🌬️ {w.get('wind', '')} m/s  
              ☁️ {w.get('description', '')}
            """)


# ---------------- Menu ---------------- #
menu = st.sidebar.selectbox("📌 Menu", T["menu"], index=0)

# Home
if menu == "🏠 Home":
    st.header(T["home_title"])
    st.markdown(T["home_desc"])

# Chat Agent
elif menu == "🤖 Chat Agent":
    q = st.text_area(T["chat_input"], "")
    if st.button(T["chat_btn"]):
        if q.strip() == "":
            st.warning(T["chat_warn"])
        else:
            with st.spinner(T["chat_loading"]):
                payload = {
                    "query": q,
                    "lang": "en" if lang == "English" else "id"
                }
                r = requests.post(f"{BACKEND}/ask", json=payload, timeout=180)
            if r.ok:
                st.success(T["chat_answer"])
                render_chat_response(r.json(), lang=payload["lang"])
            else:
                st.error(r.text)

# AI Itinerary
elif menu == "🗺️ AI Itinerary":
    st.subheader("🗓️ Buat Itinerary Perjalanan" if lang == "Indonesia" else "🗓️ Create Travel Itinerary")
    city = st.text_input("Kota / Tujuan" if lang == "Indonesia" else "City / Destination", "Paris")
    start = st.date_input("Tanggal Mulai" if lang == "Indonesia" else "Start Date", value=dt.date.today() + dt.timedelta(days=7))
    days = st.number_input("Lama Perjalanan (hari)" if lang == "Indonesia" else "Trip Duration (days)", min_value=1, max_value=21, value=3)
    prefs = st.text_area("Preferensi Khusus (opsional)" if lang == "Indonesia" else "Special Preferences (optional)", "")
    uid = st.text_input("User ID", value="user_demo")

    if st.button("🚀 Buat Itinerary" if lang == "Indonesia" else "🚀 Generate Itinerary"):
        params = {
            "destination": city,
            "start_date": str(start),
            "days": days,
            "preferences": prefs
        }
        with st.spinner("Membuat itinerary..." if lang == "Indonesia" else "Generating itinerary..."):
            r = requests.post(f"{BACKEND}/itinerary/generate", json=params, timeout=180)
        if r.ok:
            data = r.json()
            st.subheader("📌 Hasil Itinerary" if lang == "Indonesia" else "📌 Itinerary Result")
            st.text(data.get("itinerary_text") or ("Tidak ada itinerary" if lang == "Indonesia" else "No itinerary generated"))
            st.session_state["latest_itinerary"] = data.get("itinerary_text")
        else:
            st.error(r.text)

    if st.button("💾 Simpan Itinerary" if lang == "Indonesia" else "💾 Save Itinerary"):
        if "latest_itinerary" not in st.session_state:
            st.warning("Buat itinerary terlebih dahulu." if lang == "Indonesia" else "Please generate an itinerary first.")
        else:
            payload = {
                "user_id": uid,
                "destination": city,
                "itinerary_text": st.session_state["latest_itinerary"]
            }
            r = requests.post(f"{BACKEND}/itinerary/save", json=payload, timeout=30)
            if r.ok:
                st.success("Itinerary berhasil disimpan!" if lang == "Indonesia" else "Itinerary saved successfully!")
            else:
                st.error(r.text)

    if st.button("📥 Download PDF"):
        if "latest_itinerary" not in st.session_state:
            st.warning("Buat itinerary terlebih dahulu." if lang == "Indonesia" else "Please generate an itinerary first.")
        else:
            payload = {
                "destination": city,
                "start_date": str(start),
                "days": days,
                "preferences": prefs
            }
            r = requests.post(f"{BACKEND}/itinerary/pdf", json=payload, timeout=180)
            if r.ok:
                st.download_button(
                    "📄 Download Itinerary PDF",
                    r.content,
                    file_name="itinerary.pdf",
                    mime="application/pdf"
                )
            else:
                st.error(r.text)

# Weather
elif menu == "⛅ Weather" or menu == "⛅ Cuaca":
    city = st.text_input("Kota" if lang == "Indonesia" else "City", "Paris")
    if st.button("🌤️ Cek Cuaca" if lang == "Indonesia" else "🌤️ Check Weather"):
        r = requests.get(f"{BACKEND}/weather", params={"city": city}, timeout=20)
        if r.ok:
            st.json(r.json())
        else:
            st.error(r.text)

# Events
elif menu == "🎭 Events" or menu == "🎭 Acara":
    city = st.text_input("Kota" if lang == "Indonesia" else "City", "Paris")
    if st.button("🎟️ Lihat Event" if lang == "Indonesia" else "🎟️ Show Events"):
        r = requests.get(f"{BACKEND}/events", params={"city": city}, timeout=20)
        if r.ok:
            st.dataframe(pd.DataFrame(r.json()))
        else:
            st.error(r.text)

# Flights
elif menu == "✈️ Flights" or menu == "✈️ Penerbangan":
    origin = st.text_input("Asal (City/IATA)" if lang == "Indonesia" else "Origin (City/IATA)", "")
    dest = st.text_input("Tujuan (City/IATA)" if lang == "Indonesia" else "Destination (City/IATA)", "Paris")
    date = st.date_input("Tanggal Keberangkatan" if lang == "Indonesia" else "Departure Date", value=dt.date.today() + dt.timedelta(days=30))
    if st.button("🔍 Cari Tiket Pesawat" if lang == "Indonesia" else "🔍 Search Flights"):
        r = requests.get(
            f"{BACKEND}/flights",
            params={"origin": origin, "destination": dest, "date": str(date)},
            timeout=30
        )
        if r.ok:
            st.dataframe(pd.DataFrame(r.json().get("items", [])))
        else:
            st.error(r.text)

# Transport
elif menu == "🚖 Transport" or menu == "🚖 Transportasi":
    city = st.text_input("Kota" if lang == "Indonesia" else "City", "Paris")
    if st.button("🚕 Info Transportasi" if lang == "Indonesia" else "🚕 Transport Info"):
        r = requests.get(f"{BACKEND}/transportation", params={"city": city}, timeout=20)
        if r.ok:
            st.dataframe(pd.DataFrame(r.json()))
        else:
            st.error(r.text)

# Airbnb
elif menu == "🏠 Airbnb":
    city = st.text_input("Kota" if lang == "Indonesia" else "City", "Paris")
    if st.button("🏘️ Cari Airbnb" if lang == "Indonesia" else "🏘️ Search Airbnb"):
        r = requests.get(f"{BACKEND}/airbnb", params={"city": city}, timeout=20)
        if r.ok:
            st.dataframe(pd.DataFrame(r.json()))
        else:
            st.error(r.text)

# Places
elif menu == "📍 Places" or menu == "📍 Tempat Wisata":
    city = st.text_input("Kota" if lang == "Indonesia" else "City", "Paris")
    if st.button("🏞️ Cari Tempat Wisata" if lang == "Indonesia" else "🏞️ Search Attractions"):
        r = requests.get(f"{BACKEND}/places", params={"city": city}, timeout=20)
        if r.ok:
            st.dataframe(pd.DataFrame(r.json()))
        else:
            st.error(r.text)

# My Itinerary
elif menu == "🧳 My Itinerary" or menu == "🧳 Rencana Perjalanan":
    uid = st.text_input("User ID", value="user_demo")
    if st.button("📂 Ambil Itinerary" if lang == "Indonesia" else "📂 Load Itinerary"):
        r = requests.get(f"{BACKEND}/itinerary", params={"user_id": uid}, timeout=10)
        if r.ok:
            st.json(r.json())
        else:
            st.error(r.text)



