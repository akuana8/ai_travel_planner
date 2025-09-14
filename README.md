# 🧳 AI Travel Planner

## 🎯 Tujuan Proyek
AI Agent yang membantu pengguna membuat **itinerary perjalanan otomatis, personal, dan interaktif**.  
Fitur utama:  

- 🌐 **Multibahasa** → Output itinerary bisa dalam Bahasa Indonesia atau Bahasa Inggris.  
- 🏠 **Menu Navigasi Lengkap**:
  - **Home** → Halaman utama aplikasi.  
  - **AI Itinerary** → Pembuatan itinerary otomatis dengan AI (LangGraph + LLM).  
  - **Chat Agent** → Chat interaktif dengan AI untuk tanya seputar destinasi.  
  - **Airbnb** → Rekomendasi penginapan sesuai lokasi & kapasitas.  
  - **Weather** → Prediksi cuaca harian di destinasi.  
  - **Transportation** → Alternatif transportasi di kota tujuan.  
  - **Events** → Informasi acara & festival lokal.  
  - **Flights** → Rekomendasi tiket pesawat.  
  - **Places** → Destinasi menarik di sekitar area penginapan.  
  - **My Itinerary** → Menyimpan & mengakses itinerary yang sudah dibuat.  

---

## ⚙️ Lingkungan & Teknologi
- **Python**: 3.10  
- **Framework**: FastAPI, LangChain, LangGraph, FAISS  
- **Database**: Neon (PostgreSQL)  
- **LLM**: OpenAI (model `gpt-4o-mini`) / Gemini (opsional)  

---

## 📦 Setup

1. **Clone repo**
   ```bash
   git clone https://github.com/username/ai-travel-planner.git
   cd ai-travel-planner
````

2. **Buat virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate   # Mac/Linux
   venv\Scripts\activate      # Windows
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Buat file `.env`** di root folder dengan isi:

   ```env
   GOOGLE_API_KEY=your_google_api_key
   OPENAI_MODEL=gpt-4o-mini
   LLM_TEMPERATURE=0.2

   OPENWEATHER_API_KEY=your_weather_key
   TICKETMASTER_API_KEY=your_ticketmaster_key
   IPINFO_API_KEY=your_ipinfo_key
   GOOGLE_MAPS_API_KEY=your_gmaps_key

   AMADEUS_API_KEY=your_amadeus_key
   AMADEUS_API_SECRET=your_amadeus_secret

   DATABASE_URL=postgresql+psycopg2://user:pass@host:port/dbname
   BACKEND_URL=http://127.0.0.1:8000
   ```

---

## ▶️ Menjalankan Backend

```bash
uvicorn src.app:app --reload
```

Backend tersedia di:
👉 `http://127.0.0.1:8000`

---

## 🔗 Endpoint Utama

* `/chat` → Chat Agent (tanya seputar destinasi, flight, Airbnb, dll)
* `/weather` → Prediksi cuaca
* `/events` → Event & festival lokal
* `/flights` → Tiket pesawat
* `/transportation` → Transportasi di kota tujuan
* `/itinerary` → Generate AI itinerary otomatis
* `/my-itinerary` → Simpan & akses itinerary

---

## 🧪 Contoh Query

```text
I want to go to Paris on September 16, 2025. 
Find flights from Jakarta to Paris on September 16, 2025, 
Airbnb accommodations for 2 people, the weather, and events happening there.
```

```text
Saya mau ke Paris tanggal 16 September 2025, 
cari penerbangan dari Jakarta ke Paris tanggal 16 September 2025, 
penginapan Airbnb untuk 2 orang, cuaca, dan event yang ada.
```

---

## 🛠️ Catatan Development

* Tools terdefinisi di `src/agent_graph.py`.
* RAG (retrieval) pakai **FAISS** (`src/rag.py`), saat ini **per row = 1 vector** (belum ada chunking).
* Semua tool harus return JSON-serializable.
* Kalau parsing output LLM error → cek log di `ask_travel_agent`.

---

## 📌 TODO (Next Steps)

* [ ] Tambah chunking untuk teks panjang di FAISS.
* [ ] Perbaiki JSON parser hasil LLM.
* [ ] Tambah unit test untuk tiap tool.
* [ ] Integrasi ke frontend (Streamlit/React).

```

---