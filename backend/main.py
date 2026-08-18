from fastapi import FastAPI, Response, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
import csv
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText

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

class PalletPayload(BaseModel):
    expiration_date: datetime

# Global State for Active Pallet Entry Mode
active_pallet_date = None

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
            
            # FEFO: Otomatik SKT Atama (Aktif palet tarihi varsa onu kullan, yoksa varsayılan)
            global active_pallet_date
            if active_pallet_date:
                exp_date = active_pallet_date
            else:
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
        
    new_product = models.Product(name=name_lower, items_per_box=1, critical_threshold=5, expiration_days=30)
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    
    new_stock = models.Stock(product_id=new_product.id, warehouse_quantity=0, shelf_quantity=0)
    db.add(new_stock)
    db.commit()
    
    return {"status": "success", "product_id": new_product.id}

@app.post("/stock/in")
def stock_in(payload: ManualStockPayload, db: Session = Depends(get_db)):
    stock = db.query(models.Stock).filter(models.Stock.product_id == payload.product_id).first()
    product = db.query(models.Product).filter(models.Product.id == payload.product_id).first()
    if stock and product:
        stock.warehouse_quantity += payload.quantity
        new_movement = models.Movement(product_id=payload.product_id, movement_type="IN", box_count=payload.quantity)
        db.add(new_movement)
        
        # FEFO: Batch oluştur
        global active_pallet_date
        if active_pallet_date:
            exp_date = active_pallet_date
        else:
            exp_date = datetime.now() + timedelta(days=product.expiration_days)
            
        new_batch = models.Batch(product_id=payload.product_id, quantity=payload.quantity, expiration_date=exp_date)
        db.add(new_batch)
        db.commit()
    return {"status": "success"}

@app.post("/stock/out")
def stock_out(payload: ManualStockPayload, db: Session = Depends(get_db)):
    stock = db.query(models.Stock).filter(models.Stock.product_id == payload.product_id).first()
    if stock and stock.warehouse_quantity >= payload.quantity:
        stock.warehouse_quantity -= payload.quantity
        new_movement = models.Movement(product_id=payload.product_id, movement_type="OUT", box_count=payload.quantity)
        db.add(new_movement)
        
        # FEFO mantığı (Quantity kadar düş)
        remaining_to_deduct = payload.quantity
        while remaining_to_deduct > 0:
            oldest_batch = db.query(models.Batch).filter(
                models.Batch.product_id == payload.product_id,
                models.Batch.quantity > 0
            ).order_by(models.Batch.expiration_date.asc()).first()
            
            if not oldest_batch:
                break
                
            if oldest_batch.quantity >= remaining_to_deduct:
                oldest_batch.quantity -= remaining_to_deduct
                remaining_to_deduct = 0
            else:
                remaining_to_deduct -= oldest_batch.quantity
                oldest_batch.quantity = 0
                
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

@app.get("/movements")
def get_movements(db: Session = Depends(get_db)):
    movements = db.query(models.Movement).order_by(models.Movement.id.desc()).limit(50).all()
    return [{
        "id": m.id,
        "product_id": m.product_id,
        "direction": m.movement_type,
        "quantity": m.box_count,
        "timestamp": m.timestamp.isoformat() if m.timestamp else None
    } for m in movements]

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

# ==========================================
# PALET VE İMHA (WASTE) ENDPOINT'LERİ
# ==========================================

@app.post("/pallet/start")
def start_pallet(payload: PalletPayload):
    global active_pallet_date
    active_pallet_date = payload.expiration_date
    return {"status": "success", "active_date": active_pallet_date.isoformat()}

@app.post("/pallet/stop")
def stop_pallet():
    global active_pallet_date
    active_pallet_date = None
    return {"status": "success"}

@app.get("/pallet/status")
def get_pallet_status():
    global active_pallet_date
    if active_pallet_date:
        return {"status": "active", "expiration_date": active_pallet_date.isoformat()}
    return {"status": "inactive"}

@app.post("/batches/{batch_id}/waste")
def waste_batch(batch_id: int, db: Session = Depends(get_db)):
    batch = db.query(models.Batch).filter(models.Batch.id == batch_id).first()
    if not batch or batch.quantity <= 0:
        raise HTTPException(status_code=404, detail="Batch not found or empty")
        
    stock = db.query(models.Stock).filter(models.Stock.product_id == batch.product_id).first()
    if stock:
        stock.warehouse_quantity -= batch.quantity
        new_movement = models.Movement(product_id=batch.product_id, movement_type="WASTE", box_count=batch.quantity)
        db.add(new_movement)
    batch.quantity = 0
    db.commit()
    return {"status": "success"}

# ==========================================
# B2B E-POSTA / SİPARİŞ ENDPOINT'LERİ
# ==========================================

# TODO: Staj sunumu için buraya kendi bilgilerinizi giriniz.
# Gmail kullanıyorsanız, Google Hesabı ayarlarından "Uygulama Şifreleri (App Passwords)" almalısınız.
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "SİZİN_MAİL_ADRESİNİZ@gmail.com"
SENDER_PASSWORD = "GOOGLE_UYGULAMA_ŞİFRENİZ_BURAYA"
WHOLESALER_EMAIL = "toptanci_sirket@example.com" # Mailin kime gideceğini buraya yazın

@app.get("/alerts/low-stock")
def get_low_stock_alerts(db: Session = Depends(get_db)):
    products = db.query(models.Product).all()
    alerts = []
    
    for p in products:
        stock = db.query(models.Stock).filter(models.Stock.product_id == p.id).first()
        qty = stock.warehouse_quantity if stock else 0
        if qty <= p.critical_threshold:
            alerts.append({
                "product_id": p.id,
                "product_name": p.name.capitalize(),
                "current_quantity": qty,
                "critical_threshold": p.critical_threshold
            })
            
    return alerts

@app.post("/order/{product_id}")
def place_order(product_id: int, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    stock = db.query(models.Stock).filter(models.Stock.product_id == product.id).first()
    qty = stock.warehouse_quantity if stock else 0
    
    # Gerçek E-posta Gönderimi
    try:
        if SENDER_EMAIL != "SİZİN_MAİL_ADRESİNİZ@gmail.com" and SENDER_PASSWORD != "GOOGLE_UYGULAMA_ŞİFRENİZ_BURAYA":
            msg = MIMEText(f"Sayın Tedarikçi,\n\nDepomuzda {product.name.capitalize()} ürünü stokları kritik seviyeye (Mevcut: {qty}) düşmüştür. Lütfen en kısa sürede 50 koli gönderim sağlayınız.\n\nİyi çalışmalar,\nAkıllı Depo Sistemi")
            msg["Subject"] = f"ACİL SİPARİŞ: {product.name.capitalize()} (Otomatik Sistem Mesajı)"
            msg["From"] = SENDER_EMAIL
            msg["To"] = WHOLESALER_EMAIL
            
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SENDER_EMAIL, SENDER_PASSWORD)
                server.send_message(msg)
                print(f"[MAIL BASARILI] {product.name} siparişi iletildi.")
            return {"status": "success", "simulated": False}
        else:
            print(f"[MAIL SIMULASYONU] E-posta ayarları yapılmadığı için simüle edildi: {product.name} Siparişi")
            return {"status": "success", "simulated": True, "message": "Email ayarları (SENDER_EMAIL) yapılmadığı için başarıyla simüle edildi."}
            
    except Exception as e:
        print(f"[MAIL HATASI] E-posta gönderilemedi: {e}")
        # Hata durumunda frontend'i uyarmak için hata dönüyoruz
        return {"status": "error", "message": str(e)}
