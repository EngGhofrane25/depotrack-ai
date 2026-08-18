from fastapi import FastAPI, Response, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
import csv
import io
from datetime import datetime, timedelta

# Import local SQLite models and database
from .database import engine, Base, get_db
from . import models, schemas

# Tabloları oluştur
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Depo Stok Backend API (SQLite + FEFO)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Varsayılan başlangıç verileri (Seed Data)
INITIAL_PRODUCTS = [
    {"id": 1, "name": "elektronik", "items_per_box": 1, "critical_threshold": 5, "expiration_days": 1000},
    {"id": 2, "name": "gida", "items_per_box": 1, "critical_threshold": 10, "expiration_days": 15},
    {"id": 3, "name": "tekstil", "items_per_box": 1, "critical_threshold": 5, "expiration_days": 500},
    {"id": 4, "name": "kirtasiye", "items_per_box": 1, "critical_threshold": 5, "expiration_days": 700},
    {"id": 5, "name": "temizlik", "items_per_box": 1, "critical_threshold": 5, "expiration_days": 365}
]

@app.on_event("startup")
def startup_event():
    db = next(get_db())
    try:
        if db.query(models.Product).count() == 0:
            print("[INFO] Veritabanı boş, varsayılan ürünler ekleniyor...")
            for p_data in INITIAL_PRODUCTS:
                new_product = models.Product(**p_data)
                db.add(new_product)
                new_stock = models.Stock(product_id=p_data["id"], warehouse_quantity=0, shelf_quantity=0)
                db.add(new_stock)
            db.commit()
    finally:
        db.close()

# ==========================================
# İSTEK MODELLERİ (PYDANTIC)
# ==========================================
class EventPayload(BaseModel):
    tracking_id: int
    product_id: int
    direction: str

class ProductPayload(BaseModel):
    name: str

class ManualStockPayload(BaseModel):
    product_id: int
    quantity: int

class UpdateBatchPayload(BaseModel):
    expiration_date: datetime

# ==========================================
# API UÇLARI
# ==========================================

@app.get("/")
def read_root():
    return {"message": "Depo Stok API'si SQLite Veritabanı ile Çalışıyor"}

@app.get("/stock")
def get_stock(db: Session = Depends(get_db)):
    stocks = db.query(models.Stock).all()
    result = {}
    for s in stocks:
        product = db.query(models.Product).filter(models.Product.id == s.product_id).first()
        if product:
            result[product.name] = s.warehouse_quantity
    return result

@app.post("/events")
def add_event(event: EventPayload, db: Session = Depends(get_db)):
    existing_event = db.query(models.Event).filter(
        models.Event.tracking_id == event.tracking_id,
        models.Event.direction == event.direction
    ).first()
    
    if existing_event:
        return {"status": "ignored", "message": "Duplicate event"}
        
    new_event = models.Event(tracking_id=event.tracking_id, product_id=event.product_id, direction=event.direction)
    db.add(new_event)
    
    stock = db.query(models.Stock).filter(models.Stock.product_id == event.product_id).first()
    product = db.query(models.Product).filter(models.Product.id == event.product_id).first()
    
    if stock and product:
        if event.direction == "IN":
            stock.warehouse_quantity += 1
            new_movement = models.Movement(product_id=event.product_id, movement_type="IN", box_count=1)
            db.add(new_movement)
            
            # FEFO: Otomatik SKT Atama (Varsayılan gün kadar sonrası)
            exp_date = datetime.now() + timedelta(days=product.expiration_days)
            new_batch = models.Batch(product_id=event.product_id, quantity=1, expiration_date=exp_date)
            db.add(new_batch)
            
        elif event.direction == "OUT":
            if stock.warehouse_quantity > 0:
                stock.warehouse_quantity -= 1
                new_movement = models.Movement(product_id=event.product_id, movement_type="OUT", box_count=1)
                db.add(new_movement)
                
                # FEFO: En eski partiden düş (SKT'si en yakın olan)
                oldest_batch = db.query(models.Batch).filter(
                    models.Batch.product_id == event.product_id,
                    models.Batch.quantity > 0
                ).order_by(models.Batch.expiration_date.asc()).first()
                
                if oldest_batch:
                    oldest_batch.quantity -= 1
                    
    db.commit()
    return {"status": "success"}

@app.get("/expirations")
def get_expirations(db: Session = Depends(get_db)):
    # Sadece içinde ürün olan (quantity > 0) partileri getir
    batches = db.query(models.Batch).filter(models.Batch.quantity > 0).all()
    results = []
    now = datetime.now()
    
    for b in batches:
        product = db.query(models.Product).filter(models.Product.id == b.product_id).first()
        if product:
            days_left = (b.expiration_date - now).days
            
            # Tehlike durumunu hesapla
            if days_left < 0:
                status = "expired"
            elif days_left <= 7:
                status = "danger"
            elif days_left <= 30:
                status = "warning"
            else:
                status = "safe"
                
            results.append({
                "batch_id": b.id,
                "product_name": product.name.capitalize(),
                "quantity": b.quantity,
                "expiration_date": b.expiration_date.strftime("%d.%m.%Y"),
                "days_left": days_left,
                "status": status
            })
            
    # SKT'si en yakın olanları en üste sırala
    results.sort(key=lambda x: x["days_left"])
    return results

@app.put("/batches/{batch_id}")
def update_batch_expiration(batch_id: int, payload: UpdateBatchPayload, db: Session = Depends(get_db)):
    batch = db.query(models.Batch).filter(models.Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    batch.expiration_date = payload.expiration_date
    db.commit()
    return {"status": "success"}

@app.get("/report")
def download_report(db: Session = Depends(get_db)):
    movements = db.query(models.Movement).order_by(models.Movement.id.asc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Urun_ID", "Urun_Adi", "Yon", "Miktar", "Zaman"])
    for m in movements:
        product = db.query(models.Product).filter(models.Product.id == m.product_id).first()
        product_name = product.name if product else "Bilinmeyen"
        writer.writerow([m.id, m.product_id, product_name, m.movement_type, m.box_count, m.timestamp.isoformat() if m.timestamp else ""])
    return Response(content=output.getvalue(), media_type="text/csv", headers={"Content-Disposition": 'attachment; filename="stok_hareket_raporu.csv"'})
