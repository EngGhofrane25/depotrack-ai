from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Depo Stok Backend API")

# Arayüzün (Frontend) bu API'ye erişebilmesi için CORS izinleri
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Her yerden gelen isteklere izin ver
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Geçici (In-Memory) Veritabanı
# Gerçekte bu veriler SQLite'da durmalı, ancak hızlı test için bellekte tutuyoruz.
fake_db_stock = {
    "elektronik": 0,
    "gida": 0,
    "temizlik": 0,
    "kirtasiye": 0,
    "tekstil": 0
}

# Kamera Sisteminden Gelen İstek Modeli
class EventPayload(BaseModel):
    tracking_id: int
    product_id: int # 1: Elektronik, 2: Gıda, 3: Tekstil, 4: Kırtasiye, 5: Temizlik
    direction: str  # "IN" veya "OUT"

PRODUCT_MAP = {
    1: "elektronik",
    2: "gida",
    3: "tekstil",
    4: "kirtasiye",
    5: "temizlik"
}

@app.get("/")
def read_root():
    return {"message": "Depo Stok API Çalışıyor!"}

@app.get("/stock")
def get_stock():
    """
    Web arayüzü (Frontend) stokları okumak için bu adrese istek atar.
    """
    return fake_db_stock

@app.post("/events")
def add_event(event: EventPayload):
    """
    Kamera Sistemi (camera_feed.py) kutu algıladığında bu adrese istek atar.
    """
    product_key = PRODUCT_MAP.get(event.product_id, "bilinmeyen")
    
    if product_key in fake_db_stock:
        if event.direction == "IN":
            fake_db_stock[product_key] += 1
        elif event.direction == "OUT":
            # Eksiye düşmesini engelle
            if fake_db_stock[product_key] > 0:
                fake_db_stock[product_key] -= 1
                
    return {"status": "success", "current_stock": fake_db_stock}

