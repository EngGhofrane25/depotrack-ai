from fastapi import FastAPI, Response, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
import csv
import io
from datetime import datetime

# Import local SQLite models and database
from .database import engine, Base, get_db
from . import models, schemas

# Tabloları oluştur
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Depo Stok Backend API (SQLite)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Varsayılan başlangıç verileri (Seed Data)
INITIAL_PRODUCTS = [
    {"id": 1, "name": "elektronik", "items_per_box": 1, "critical_threshold": 5},
    {"id": 2, "name": "gida", "items_per_box": 1, "critical_threshold": 10},
    {"id": 3, "name": "tekstil", "items_per_box": 1, "critical_threshold": 5},
    {"id": 4, "name": "kirtasiye", "items_per_box": 1, "critical_threshold": 5},
    {"id": 5, "name": "temizlik", "items_per_box": 1, "critical_threshold": 5}
]

@app.on_event("startup")
def startup_event():
    # Sunucu açıldığında tabloları kontrol edip boşsa ürünleri ekler
    db = next(get_db())
    try:
        if db.query(models.Product).count() == 0:
            print("[INFO] Veritabanı boş, varsayılan ürünler ekleniyor...")
            for p_data in INITIAL_PRODUCTS:
                new_product = models.Product(**p_data)
                db.add(new_product)
                # Stok bilgisini de sıfır olarak oluştur
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

# ==========================================
# API UÇLARI
# ==========================================

@app.get("/")
def read_root():
    return {"message": "Depo Stok API'si SQLite Veritabanı ile Çalışıyor"}

@app.get("/stock")
def get_stock(db: Session = Depends(get_db)):
    stocks = db.query(models.Stock).all()
    # Frontend'in beklediği format: {"elektronik": 10, "gida": 5}
    result = {}
    for s in stocks:
        product = db.query(models.Product).filter(models.Product.id == s.product_id).first()
        if product:
            result[product.name] = s.warehouse_quantity
    return result

@app.post("/events")
def add_event(event: EventPayload, db: Session = Depends(get_db)):
    # Mükerrer kayıt kontrolü: Aynı tracking_id ve direction veritabanında var mı?
    existing_event = db.query(models.Event).filter(
        models.Event.tracking_id == event.tracking_id,
        models.Event.direction == event.direction
    ).first()
    
    if existing_event:
        return {"status": "ignored", "message": "Duplicate event"}
        
    # Olayı veritabanına kaydet
    new_event = models.Event(
        tracking_id=event.tracking_id,
        product_id=event.product_id,
        direction=event.direction
    )
    db.add(new_event)
    
    # Stoğu güncelle ve hareket kaydı oluştur
    stock = db.query(models.Stock).filter(models.Stock.product_id == event.product_id).first()
    
    if stock:
        if event.direction == "IN":
            stock.warehouse_quantity += 1
            new_movement = models.Movement(product_id=event.product_id, movement_type="IN", box_count=1)
            db.add(new_movement)
        elif event.direction == "OUT":
            if stock.warehouse_quantity > 0:
                stock.warehouse_quantity -= 1
                new_movement = models.Movement(product_id=event.product_id, movement_type="OUT", box_count=1)
                db.add(new_movement)
                
    db.commit()
    return {"status": "success"}

@app.get("/products")
def get_products(db: Session = Depends(get_db)):
    products = db.query(models.Product).all()
    return [{"id": p.id, "name": p.name} for p in products]

@app.post("/products")
def add_product(payload: ProductPayload, db: Session = Depends(get_db)):
    name_lower = payload.name.lower()
    existing = db.query(models.Product).filter(models.Product.name == name_lower).first()
    if existing:
        return {"status": "error", "message": "Product already exists"}
        
    new_product = models.Product(name=name_lower, items_per_box=1, critical_threshold=5)
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    
    new_stock = models.Stock(product_id=new_product.id, warehouse_quantity=0, shelf_quantity=0)
    db.add(new_stock)
    db.commit()
    
    return {"status": "success", "product_id": new_product.id}

@app.get("/movements")
def get_movements(db: Session = Depends(get_db)):
    movements = db.query(models.Movement).order_by(models.Movement.timestamp.desc()).all()
    return [{
        "id": m.id,
        "product_id": m.product_id,
        "direction": m.movement_type,
        "quantity": m.box_count,
        "timestamp": m.timestamp.isoformat() if m.timestamp else None
    } for m in movements]

@app.post("/stock/in")
def stock_in(payload: ManualStockPayload, db: Session = Depends(get_db)):
    stock = db.query(models.Stock).filter(models.Stock.product_id == payload.product_id).first()
    if stock:
        stock.warehouse_quantity += payload.quantity
        new_movement = models.Movement(product_id=payload.product_id, movement_type="IN", box_count=payload.quantity)
        db.add(new_movement)
        db.commit()
    return {"status": "success"}

@app.post("/stock/out")
def stock_out(payload: ManualStockPayload, db: Session = Depends(get_db)):
    stock = db.query(models.Stock).filter(models.Stock.product_id == payload.product_id).first()
    if stock and stock.warehouse_quantity >= payload.quantity:
        stock.warehouse_quantity -= payload.quantity
        new_movement = models.Movement(product_id=payload.product_id, movement_type="OUT", box_count=payload.quantity)
        db.add(new_movement)
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
        writer.writerow([
            m.id, 
            m.product_id, 
            product_name, 
            m.movement_type, 
            m.box_count, 
            m.timestamp.isoformat() if m.timestamp else ""
        ])
        
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="stok_hareket_raporu.csv"'}
    )
