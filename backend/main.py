import sys
import io
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
except AttributeError:
    pass

from fastapi import FastAPI, Response, Depends, HTTPException, BackgroundTasks, Security, WebSocket, WebSocketDisconnect
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
import csv
import os
from datetime import datetime, timedelta

# Import local SQLite models and database
from .database import engine, Base, get_db
from . import models, schemas
from . import email_service

# Tabloları oluştur
Base.metadata.create_all(bind=engine)


def _ensure_product_supplier_email_column():
    """Eski veritabanlarina supplier_email kolonunu ekler (create_all ALTER yapmaz)."""
    insp = inspect(engine)
    if "products" in insp.get_table_names():
        columns = [c["name"] for c in insp.get_columns("products")]
        if "supplier_email" not in columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE products ADD COLUMN supplier_email VARCHAR DEFAULT ''"))
            print("[INFO] 'products' tablosuna supplier_email kolonu eklendi.")


_ensure_product_supplier_email_column()


# ==========================================
# WEBSOCKET (CANLI YAYIN) YONETIMI
# ==========================================


app = FastAPI(title="Depo Stok Backend API (SQLite + FEFO)")

class ConnectionManager:
    def __init__(self):
        self.active_connections = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# ==========================================
# GÜVENLİK VE JWT YAPILANDIRMASI
# ==========================================
SECRET_KEY = "depo_stok_super_gizli_anahtari"
ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def create_access_token(data: dict):
    to_encode = data.copy()
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def _decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Yetkisiz erişim - Token Geçersiz")

def get_current_user(token: str = Depends(oauth2_scheme)):
    username: str = _decode_access_token(token).get("sub")
    if username is None:
        raise HTTPException(status_code=401, detail="Yetkisiz erişim")
    return username

def get_admin_user(token: str = Depends(oauth2_scheme)):
    payload = _decode_access_token(token)
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Bu işlem için yönetici (admin) yetkisi gereklidir")
    username = payload.get("sub")
    if username is None:
        raise HTTPException(status_code=401, detail="Yetkisiz erişim")
    return username



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class NoCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            response.headers["Pragma"] = "no-cache"
        return response

app.add_middleware(NoCacheMiddleware)

# Varsayılan başlangıç verileri (Seed Data)
INITIAL_PRODUCTS = [
    {"id": 1, "name": "elektronik", "items_per_box": 1, "critical_threshold": 3, "expiration_days": 1000},
    {"id": 2, "name": "gida", "items_per_box": 1, "critical_threshold": 3, "expiration_days": 15},
    {"id": 3, "name": "tekstil", "items_per_box": 1, "critical_threshold": 3, "expiration_days": 500},
    {"id": 4, "name": "kirtasiye", "items_per_box": 1, "critical_threshold": 3, "expiration_days": 700},
    {"id": 5, "name": "temizlik", "items_per_box": 1, "critical_threshold": 3, "expiration_days": 365}
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

class LoginPayload(BaseModel):
    username: str
    password: str



# ==========================================
# API UÇLARI
# ==========================================

@app.get("/")
def read_root():
    return {"message": "Depo Stok API'si SQLite Veritabanı ile Çalışıyor"}

@app.post("/login")
def login(payload: LoginPayload):
    if payload.username == "admin" and payload.password == "12345":
        token = create_access_token({"sub": payload.username, "role": "admin"})
        return {"status": "success", "token": token, "role": "admin"}
    elif payload.username == "gorevli" and payload.password == "12345":
        token = create_access_token({"sub": payload.username, "role": "worker"})
        return {"status": "success", "token": token, "role": "worker"}
    raise HTTPException(status_code=401, detail="Geçersiz kullanıcı adı veya şifre")

@app.get("/analytics")
def get_analytics(db: Session = Depends(get_db)):
    stocks = db.query(models.Stock).all()
    labels = []
    data = []
    for s in stocks:
        product = db.query(models.Product).filter(models.Product.id == s.product_id).first()
        if product:
            labels.append(product.name.capitalize())
            data.append(s.warehouse_quantity)
    return {"labels": labels, "data": data}

@app.get("/export/csv")
def export_csv(db: Session = Depends(get_db)):
    movements = db.query(models.Movement).order_by(models.Movement.timestamp.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Urun", "Islem Yonu", "Kutu Sayisi", "Tarih"])
    
    for mov in movements:
        product = db.query(models.Product).filter(models.Product.id == mov.product_id).first()
        p_name = product.name.capitalize() if product else "Bilinmiyor"
        writer.writerow([mov.id, p_name, mov.movement_type, mov.box_count, mov.timestamp.strftime("%Y-%m-%d %H:%M:%S")])
        
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=depo_rapor.csv"})

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
def add_event(event: EventPayload, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    print(f"[EVENT] POST /events received: tracking_id={event.tracking_id}, product_id={event.product_id}, direction={event.direction}")
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
            new_movement = models.Movement(product_id=event.product_id, movement_type="IN", box_count=1, timestamp=datetime.now())
            db.add(new_movement)
            
            # SKT: Varsayılan ömür (expiration_days)
            exp_date = datetime.now() + timedelta(days=product.expiration_days)
                
            new_batch = models.Batch(product_id=event.product_id, quantity=1, expiration_date=exp_date)
            db.add(new_batch)
            
        elif event.direction == "OUT":
            if stock.warehouse_quantity > 0:
                stock.warehouse_quantity -= 1
                new_movement = models.Movement(product_id=event.product_id, movement_type="OUT", box_count=1, timestamp=datetime.now())
                db.add(new_movement)
                
                # FEFO: En eski partiden düş (SKT'si en yakın olan)
                oldest_batch = db.query(models.Batch).filter(
                    models.Batch.product_id == event.product_id,
                    models.Batch.quantity > 0
                ).order_by(models.Batch.expiration_date.asc()).first()
                
                if oldest_batch:
                    oldest_batch.quantity -= 1
                    
            # 2 AŞAMALI ONAY: Kritik stok kontrolü (Çıkış yapıldıktan sonra)
            if stock.warehouse_quantity <= product.critical_threshold:
                check_and_send_approval_email(product.id, product.name, stock.warehouse_quantity, product.critical_threshold)
                    
    db.commit()
    background_tasks.add_task(manager.broadcast, "update")
    return {"status": "success"}

@app.get("/products")
def get_products(db: Session = Depends(get_db)):
    products = db.query(models.Product).all()
    return [{"id": p.id, "name": p.name, "supplier_email": p.supplier_email or ""} for p in products]


class SupplierEmailPayload(BaseModel):
    supplier_email: str = ""

@app.put("/products/{product_id}/supplier")
def set_supplier_email(product_id: int, payload: SupplierEmailPayload, db: Session = Depends(get_db), user: str = Depends(get_admin_user)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Ürün bulunamadı")

    product.supplier_email = payload.supplier_email.strip()
    new_audit = models.AuditLog(user_role=user, action="TOPTANCI GUNCELLEMESI", detail=f"'{product.name}' icin toptanci e-postasi '{product.supplier_email}' olarak ayarlandi.")
    db.add(new_audit)
    db.commit()
    return {"status": "success", "product_id": product.id, "supplier_email": product.supplier_email}

@app.post("/products")
def add_product(payload: ProductPayload, db: Session = Depends(get_db)):
    name_lower = payload.name.lower()
    existing = db.query(models.Product).filter(models.Product.name == name_lower).first()
    if existing:
        return {"status": "error", "message": "Product already exists"}
        
    new_product = models.Product(name=name_lower, items_per_box=1, critical_threshold=3, expiration_days=30)
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    
    new_stock = models.Stock(product_id=new_product.id, warehouse_quantity=0, shelf_quantity=0)
    db.add(new_stock)
    db.commit()
    
    background_tasks.add_task(manager.broadcast, "update")
    return {"status": "success", "product_id": new_product.id}

@app.post("/stock/in")
def stock_in(payload: ManualStockPayload, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    stock = db.query(models.Stock).filter(models.Stock.product_id == payload.product_id).first()
    product = db.query(models.Product).filter(models.Product.id == payload.product_id).first()
    if stock and product:
        stock.warehouse_quantity += payload.quantity
        new_movement = models.Movement(product_id=payload.product_id, movement_type="IN", box_count=payload.quantity)
        db.add(new_movement)
        
        # FEFO: Batch oluştur
        exp_date = datetime.now() + timedelta(days=product.expiration_days)
            
        new_batch = models.Batch(product_id=payload.product_id, quantity=payload.quantity, expiration_date=exp_date)
        db.add(new_batch)
        db.commit()
    background_tasks.add_task(manager.broadcast, "update")
    return {"status": "success"}

@app.post("/stock/out")
def stock_out(payload: ManualStockPayload, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    stock = db.query(models.Stock).filter(models.Stock.product_id == payload.product_id).first()
    if not stock:
        raise HTTPException(status_code=404, detail="Stok kaydı bulunamadı")

    if stock.warehouse_quantity < payload.quantity:
        raise HTTPException(status_code=400, detail=f"Yetersiz stok: mevcut {stock.warehouse_quantity}, istenen {payload.quantity}")

    stock.warehouse_quantity -= payload.quantity
    new_movement = models.Movement(product_id=payload.product_id, movement_type="OUT", box_count=payload.quantity)
    db.add(new_movement)

    # FEFO mantigi: once tum gecerli partileri hafizaya yukle, sonra memory uzerinden dus.
    # autoflush=False nedeniyle DB'deki stale verilerle while loopsonsuz dongu olusturur,
    # bu yuzden tek seferde yukleyip Python listesi uzerinden yuruyoruz.
    batches = db.query(models.Batch).filter(
        models.Batch.product_id == payload.product_id,
        models.Batch.quantity > 0
    ).order_by(models.Batch.expiration_date.asc()).all()

    remaining_to_deduct = payload.quantity
    max_iterations = len(batches) + 1  # her batch en fazla 1 kez ziyaret edilir
    for _ in range(max_iterations):
        if remaining_to_deduct <= 0:
            break
        found = False
        for batch in batches:
            if batch.quantity > 0:
                found = True
                if batch.quantity >= remaining_to_deduct:
                    batch.quantity -= remaining_to_deduct
                    remaining_to_deduct = 0
                    break
                else:
                    remaining_to_deduct -= batch.quantity
                    batch.quantity = 0
        if not found:
            break

    # 2 ASAMALI ONAY: Kritik stok kontrolu (Manuel cikis yapildiktan sonra)
    product = db.query(models.Product).filter(models.Product.id == payload.product_id).first()
    if product and stock.warehouse_quantity <= product.critical_threshold:
        check_and_send_approval_email(product.id, product.name, stock.warehouse_quantity, product.critical_threshold)

    db.commit()
    background_tasks.add_task(manager.broadcast, "update")
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
    background_tasks.add_task(manager.broadcast, "update")
    return {"status": "success"}

@app.get("/movements")
def get_movements(filter: str = "5", db: Session = Depends(get_db)):
    query = db.query(models.Movement)
    if filter != "5":
        now = datetime.now()
        if filter == "24h":
            query = query.filter(models.Movement.timestamp >= now - timedelta(hours=24))
        elif filter == "2d":
            query = query.filter(models.Movement.timestamp >= now - timedelta(days=2))
        elif filter == "1m":
            query = query.filter(models.Movement.timestamp >= now - timedelta(days=30))
        elif filter == "3m":
            query = query.filter(models.Movement.timestamp >= now - timedelta(days=90))
    movements = query.order_by(models.Movement.id.desc()).limit(1000).all()
    if filter == "5":
        movements = movements[:5]
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



class StockUpdatePayload(BaseModel):
    product_name: str
    new_quantity: int

@app.post("/stock/update")
def update_stock_manual(payload: StockUpdatePayload, background_tasks: BackgroundTasks, db: Session = Depends(get_db), user: str = Depends(get_current_user)):
    if payload.new_quantity < 0:
        payload.new_quantity = 0
        
    product = db.query(models.Product).filter(models.Product.name == payload.product_name).first()
    if not product:
        raise HTTPException(status_code=404, detail="Ürün bulunamadı")
    
    stock = db.query(models.Stock).filter(models.Stock.product_id == product.id).first()
    if stock:
        old_qty = stock.warehouse_quantity
        stock.warehouse_quantity = payload.new_quantity
        new_audit = models.AuditLog(user_role=user, action="MANUAL_UPDATE", detail=f"{product.name} stoku {old_qty}'den {payload.new_quantity}'e degistirildi.")
        db.add(new_audit)
        db.commit()
        background_tasks.add_task(manager.broadcast, "update")
    return {"status": "success", "new_quantity": stock.warehouse_quantity}
    raise HTTPException(status_code=404, detail="Stok kaydı bulunamadı")

@app.post("/batches/{batch_id}/waste")
def waste_batch(batch_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db), user: str = Depends(get_current_user)):
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
    background_tasks.add_task(manager.broadcast, "update")
    return {"status": "success"}

# ==========================================
# B2B E-POSTA / SİPARİŞ ENDPOINT'LERİ (2 AŞAMALI ONAY)
# ==========================================

WORKER_EMAIL = os.getenv("WORKER_EMAIL", "admin@sirket.com")
WHOLESALER_EMAIL = os.getenv("WHOLESALER_EMAIL", "toptanci@sirket.com")

# Spam engellemek için hangi ürün için ne zaman onay maili atıldığını takip ediyoruz
last_approval_email_sent = {} # { product_id: datetime }

def check_and_send_approval_email(product_id, product_name, current_qty, threshold):
    global last_approval_email_sent
    now = datetime.now()
    last_sent = last_approval_email_sent.get(product_id)
    
    # Eğer son 24 saat içinde zaten mail atıldıysa tekrar atma (spam engelleme)
    if last_sent and (now - last_sent).total_seconds() < 86400:
        return
        
    last_approval_email_sent[product_id] = now
    
    # Görevliye gidecek Onay Maili İçeriği (İçinde Tıklanabilir Buton Var)
    approval_link = f"http://127.0.0.1:8000/approve-order/{product_id}"
    subject = f"ONAY BEKLİYOR: {product_name.capitalize()} Stoğu Azaldı!"
    content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #ef6c00;">Kritik Stok Uyarısı!</h2>
            <p>Depodaki <strong>{product_name.capitalize()}</strong> stoğu kritik seviyeye ({current_qty} adet) düşmüştür. (Sınır: {threshold})</p>
            <p>Toptancıdan yeni bir parti (50 Koli) sipariş geçilmesini onaylıyor musunuz?</p>
            <br>
            <a href="{approval_link}" style="background-color: #2e7d32; color: white; padding: 15px 25px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">SİPARİŞİ ONAYLA VE TOPTANCIYA İLET</a>
            <br><br>
            <small>Bu otomatik bir sistem mesajıdır.</small>
        </body>
    </html>
    """
    
    success = email_service.send_email(WORKER_EMAIL, subject, content)
    if success:
        print(f"[BİLGİ] {product_name} için Görevliye Onay Maili Gönderildi.")
    else:
        print(f"[HATA] {product_name} için Görevliye Onay Maili Gönderilemedi.")

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

# Eskiden POST idi, şimdi görevli mailden linke tıklayacağı için GET oldu!
@app.get("/approve-order/{product_id}", response_class=HTMLResponse)
def approve_order(product_id: int, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        return HTMLResponse(content="<h1>Hata</h1><p>Ürün bulunamadı.</p>", status_code=404)
        
    stock = db.query(models.Stock).filter(models.Stock.product_id == product.id).first()
    qty = stock.warehouse_quantity if stock else 0
    
    # Alici onceligi: urune tanimli toptanci e-postasi > ortam degiskeni (WHOLESALER_EMAIL)
    recipient = (product.supplier_email or "").strip() or WHOLESALER_EMAIL

    # 2. AŞAMA: Toptancıya Giden Gerçek Sipariş Maili
    subject = f"ACİL SİPARİŞ: {product.name.capitalize()} (Otomatik Sistem Mesajı)"
    content = f"""
    <html>
        <body>
            <p>Sayın Tedarikçi,</p>
            <p>Depomuzda <strong>{product.name.capitalize()}</strong> ürünü stokları kritik seviyeye (Mevcut: {qty}) düşmüştür.</p>
            <p>Lütfen en kısa sürede adresimize <strong>50 koli</strong> gönderim sağlayınız.</p>
            <br><p>İyi çalışmalar,<br>Akıllı Depo Sistemi</p>
        </body>
    </html>
    """
    
    success = email_service.send_email(recipient, subject, content)
    
    if success:
        return f"""
        <html>
            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                <div style="max-width: 500px; margin: 0 auto; background-color: #e8f5e9; padding: 30px; border-radius: 10px; border: 1px solid #4caf50;">
                    <h1 style="color: #2e7d32;">✅ SİPARİŞ ONAYLANDI!</h1>
                    <p style="font-size: 18px;"><b>{product.name.capitalize()}</b> için toptancıya ({recipient}) resmi sipariş e-postası başarıyla iletildi.</p>
                    <p style="color: #666;">Bu pencereyi kapatabilirsiniz.</p>
                </div>
            </body>
        </html>
        """
    else:
        return "<h1>Hata Oluştu!</h1><p>Toptancıya e-posta iletilemedi. Konsol loglarını kontrol edin.</p>"

@app.get("/audit_logs")
def get_audit_logs(db: Session = Depends(get_db), user: str = Depends(get_current_user)):
    logs = db.query(models.AuditLog).order_by(models.AuditLog.timestamp.desc()).limit(50).all()
    return logs

@app.post("/movements/{movement_id}/undo")
def undo_movement(movement_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db), user: str = Depends(get_current_user)):
    movement = db.query(models.Movement).filter(models.Movement.id == movement_id).first()
    if not movement:
        raise HTTPException(status_code=404, detail="Hareket bulunamadi")
        
    stock = db.query(models.Stock).filter(models.Stock.product_id == movement.product_id).first()
    if not stock:
        raise HTTPException(status_code=404, detail="Stok bulunamadi")
        
    if movement.movement_type == "IN":
        stock.warehouse_quantity -= movement.box_count
    else:
        stock.warehouse_quantity += movement.box_count
        
    new_audit = models.AuditLog(user_role=user, action="UNDO_MOVEMENT", detail=f"Kamera hareketi (ID: {movement_id}, {movement.movement_type}) geri alindi.")
    db.add(new_audit)
    db.delete(movement)
    db.commit()
    background_tasks.add_task(manager.broadcast, "update")
    return {"status": "success"}

@app.post("/order/{product_id}")
def place_order_to_supplier(product_id: int, wholesale: str = None, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    stock = db.query(models.Stock).filter(models.Stock.product_id == product.id).first()
    qty = stock.warehouse_quantity if stock else 0

    # Alici onceligi: istekten gelen adres > urune tanimli toptanci > ortam degiskeni
    recipient = (wholesale or "").strip() or (product.supplier_email or "").strip() or WHOLESALER_EMAIL

    subject = f"ACIL SIPARIS: {product.name.capitalize()} talebi"
    content = f"""
    <html>
        <body>
            <p>Sayın Tedarikçi,</p>
            <p>Depomuzda <strong>{product.name.capitalize()}</strong> ürünü stokları kritik seviyeye (Mevcut: {qty}) düşmüştür.</p>
            <p>Lütfen en kısa sürede adresimize <strong>50 koli</strong> gönderim sağlayınız.</p>
            <br><p>İyi çalışmalar,<br>Akıllı Depo Sistemi</p>
        </body>
    </html>
    """

    sent = email_service.send_email(recipient, subject, content)
    mode = email_service.get_active_provider()

    new_audit = models.AuditLog(
        user_role="admin",
        action="SIPARIS GECILDI",
        detail=f"{product.name.capitalize()} icin {recipient} adresine siparis e-postasi {'gonderildi' if sent else 'GONDERILEMEDI'} ({mode})."
    )
    db.add(new_audit)
    db.commit()

    if not sent:
        return {"status": "error", "sent": False, "mode": mode, "recipient": recipient,
                "message": "E-posta gonderilemedi. Sunucu loglarini kontrol edin."}

    return {"status": "success", "sent": True, "mode": mode, "recipient": recipient,
            "subject": subject}

from pydantic import BaseModel
class BrandUpdate(BaseModel):
    brand_name: str

@app.post("/batches/{batch_id}/brand")
def update_batch_brand(batch_id: int, payload: BrandUpdate, db: Session = Depends(get_db)):
    batch = db.query(models.Batch).filter(models.Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    batch.brand_name = payload.brand_name
    db.commit()
    
    # Audit log
    product = db.query(models.Product).filter(models.Product.id == batch.product_id).first()
    new_audit = models.AuditLog(user_role="admin", action="MARKA GÜNCELLEMESİ", detail=f"#{batch_id} nolu koli için marka '{payload.brand_name}' olarak güncellendi.")
    db.add(new_audit)
    db.commit()
    
    background_tasks = BackgroundTasks()
    background_tasks.add_task(manager.broadcast, "update")
    
    return {"status": "success", "brand_name": batch.brand_name}
