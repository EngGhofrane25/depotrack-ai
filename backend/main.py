from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Set
from datetime import datetime
import csv
import io

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

# GÜN 10 EKSİK UÇLARIN YÜKLENMESİ: Product ve Movement tabloları
fake_db_products = [
    {"id": 1, "name": "Elektronik"},
    {"id": 2, "name": "Gıda"},
    {"id": 3, "name": "Tekstil"},
    {"id": 4, "name": "Kırtasiye"},
    {"id": 5, "name": "Temizlik"}
]

fake_db_movements = []
next_movement_id = 1

def record_movement(product_id: int, direction: str, quantity: int):
    global next_movement_id
    fake_db_movements.append({
        "id": next_movement_id,
        "product_id": product_id,
        "direction": direction,
        "quantity": quantity,
        "timestamp": datetime.now().isoformat()
    })
    next_movement_id += 1

# GÜN 10 DÜZELTME: Mükerrer Kayıt (Çifte Sayım) Koruması için geçmiş olaylar
processed_events: Set[str] = set()

# İstek Modelleri
class EventPayload(BaseModel):
    tracking_id: int
    product_id: int # 1: Elektronik, 2: Gıda, 3: Tekstil, 4: Kırtasiye, 5: Temizlik
    direction: str  # "IN" veya "OUT"

class ProductPayload(BaseModel):
    name: str

class ManualStockPayload(BaseModel):
    product_id: int
    quantity: int

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
    
    # Çifte sayım koruması: Benzersiz bir işlem kodu oluştur (Örn: "5_IN")
    event_signature = f"{event.tracking_id}_{event.direction}"
    
    if event_signature in processed_events:
        return {"status": "ignored", "message": "Mükerrer kayıt engellendi.", "current_stock": fake_db_stock}
    
    # İşlemi geçmiş defterine kaydet
    processed_events.add(event_signature)
    
    if product_key in fake_db_stock:
        if event.direction == "IN":
            fake_db_stock[product_key] += 1
            record_movement(event.product_id, "IN", 1)
        elif event.direction == "OUT":
            # Eksiye düşmesini engelle
            if fake_db_stock[product_key] > 0:
                fake_db_stock[product_key] -= 1
                record_movement(event.product_id, "OUT", 1)
                
    return {"status": "success", "current_stock": fake_db_stock}

# ==========================================
# EKSİK UÇLAR (GÜN 10 İLAVESİ)
# ==========================================
@app.get("/products")
def get_products():
    return fake_db_products

@app.post("/products")
def add_product(payload: ProductPayload):
    new_id = len(fake_db_products) + 1
    fake_db_products.append({"id": new_id, "name": payload.name})
    
    product_key = payload.name.lower()
    PRODUCT_MAP[new_id] = product_key
    if product_key not in fake_db_stock:
        fake_db_stock[product_key] = 0
        
    return {"status": "success", "product_id": new_id}

@app.get("/movements")
def get_movements():
    return fake_db_movements

@app.post("/stock/in")
def stock_in(payload: ManualStockPayload):
    product_key = PRODUCT_MAP.get(payload.product_id, "bilinmeyen")
    if product_key in fake_db_stock:
        fake_db_stock[product_key] += payload.quantity
        record_movement(payload.product_id, "IN", payload.quantity)
    return {"status": "success", "current_stock": fake_db_stock}

@app.post("/stock/out")
def stock_out(payload: ManualStockPayload):
    product_key = PRODUCT_MAP.get(payload.product_id, "bilinmeyen")
    if product_key in fake_db_stock:
        if fake_db_stock[product_key] >= payload.quantity:
            fake_db_stock[product_key] -= payload.quantity
            record_movement(payload.product_id, "OUT", payload.quantity)
    return {"status": "success", "current_stock": fake_db_stock}

@app.get("/report")
def download_report():
    output = io.StringIO()
    writer = csv.writer(output)
    
    # CSV Başlık (Header)
    writer.writerow(["ID", "Urun_ID", "Urun_Adi", "Yon", "Miktar", "Zaman"])
    
    # Veriler
    for m in fake_db_movements:
        product_name = PRODUCT_MAP.get(m["product_id"], "Bilinmeyen")
        writer.writerow([m["id"], m["product_id"], product_name, m["direction"], m["quantity"], m["timestamp"]])
        
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="stok_hareket_raporu.csv"'}
    )

