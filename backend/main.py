from fastapi import FastAPI, Response, Depends, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
import csv
import io
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
def add_event(event: EventPayload, db: Session = Depends(get_db)):
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
                
        # 2 AŞAMALI ONAY: Kritik stok kontrolü (Manuel çıkış yapıldıktan sonra)
        product = db.query(models.Product).filter(models.Product.id == payload.product_id).first()
        if product and stock.warehouse_quantity <= product.critical_threshold:
            check_and_send_approval_email(product.id, product.name, stock.warehouse_quantity, product.critical_threshold)
                
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
    print(f"[POLL] GET /movements called — returning {len(movements)} rows, newest timestamp: {movements[0].timestamp if movements else 'N/A'}")
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
def update_stock_manual(payload: StockUpdatePayload, db: Session = Depends(get_db)):
    if payload.new_quantity < 0:
        payload.new_quantity = 0
        
    product = db.query(models.Product).filter(models.Product.name == payload.product_name).first()
    if not product:
        raise HTTPException(status_code=404, detail="Ürün bulunamadı")
    
    stock = db.query(models.Stock).filter(models.Stock.product_id == product.id).first()
    if stock:
        stock.warehouse_quantity = payload.new_quantity
        db.commit()
        return {"status": "success", "new_quantity": stock.warehouse_quantity}
    raise HTTPException(status_code=404, detail="Stok kaydı bulunamadı")

@app.post("/batches/{batch_id}/waste")
def waste_batch(batch_id: int, db: Session = Depends(get_db), user: str = Depends(get_current_user)):
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
# B2B E-POSTA / SİPARİŞ ENDPOINT'LERİ (2 AŞAMALI ONAY)
# ==========================================

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "SİZİN_MAİL_ADRESİNİZ@gmail.com"
SENDER_PASSWORD = "GOOGLE_UYGULAMA_ŞİFRENİZ_BURAYA"

WORKER_EMAIL = "depo_gorevlisi_mailiniz@gmail.com" # Görevlinin (Sizin) onay mailini alacağınız adres
WHOLESALER_EMAIL = "toptanci_sirket@example.com" # Mailin kime gideceğini buraya yazın

# Spam engellemek için hangi ürün için ne zaman onay maili atıldığını takip ediyoruz
last_approval_email_sent = {} # { product_id: datetime }

def send_email_helper(to_email, subject, content):
    if SENDER_EMAIL == "SİZİN_MAİL_ADRESİNİZ@gmail.com":
        print(f"[MAIL SIMULASYONU] Kime: {to_email} | Konu: {subject}")
        return True
        
    try:
        msg = MIMEText(content, 'html')
        msg["Subject"] = subject
        msg["From"] = SENDER_EMAIL
        msg["To"] = to_email
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"[MAIL HATASI] E-posta gönderilemedi: {e}")
        return False

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
    
    send_email_helper(WORKER_EMAIL, subject, content)
    print(f"[BİLGİ] {product_name} için Görevliye Onay Maili Gönderildi.")

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
    
    success = send_email_helper(WHOLESALER_EMAIL, subject, content)
    
    if success:
        return f"""
        <html>
            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                <div style="max-width: 500px; margin: 0 auto; background-color: #e8f5e9; padding: 30px; border-radius: 10px; border: 1px solid #4caf50;">
                    <h1 style="color: #2e7d32;">✅ SİPARİŞ ONAYLANDI!</h1>
                    <p style="font-size: 18px;"><b>{product.name.capitalize()}</b> için toptancıya ({WHOLESALER_EMAIL}) resmi sipariş e-postası başarıyla iletildi.</p>
                    <p style="color: #666;">Bu pencereyi kapatabilirsiniz.</p>
                </div>
            </body>
        </html>
        """
    else:
        return "<h1>Hata Oluştu!</h1><p>Toptancıya e-posta iletilemedi. Konsol loglarını kontrol edin.</p>"
