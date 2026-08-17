from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from .database import engine, get_db, Base
from .models import Product, Stock, Movement, Event
from .schemas import (
    ProductCreate,
    ProductOut,
    StockOut,
    MovementOut,
    StockMovement,
    EventCreate,
    EventOut,
)

app = FastAPI(title="Depo Stok Takip API")

# Seed data matching cv/config.py PRODUCT_TYPES
SEED_PRODUCTS = [
    {"name": "Elektronik", "items_per_box": 10, "critical_threshold": 5, "supplier_info": "Tekno Tedarik A.S."},
    {"name": "Gida",       "items_per_box": 20, "critical_threshold": 8, "supplier_info": "Taze Gida Ltd."},
    {"name": "Tekstil",    "items_per_box": 30, "critical_threshold": 4, "supplier_info": "Moda Tekstil A.S."},
    {"name": "Kirtasiye",  "items_per_box": 50, "critical_threshold": 6, "supplier_info": "Bilgi Kirtasiye Ltd."},
    {"name": "Temizlik",   "items_per_box": 15, "critical_threshold": 10, "supplier_info": "Hijyen Dunyasi A.S."},
]


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    if db.query(Product).count() == 0:
        for p in SEED_PRODUCTS:
            product = Product(**p)
            db.add(product)
            db.flush()
            db.add(Stock(product_id=product.id, warehouse_quantity=0, shelf_quantity=0))
        db.commit()
    db.close()


@app.get("/products", response_model=list[ProductOut])
def list_products(db: Session = Depends(get_db)):
    return db.query(Product).all()


@app.post("/products", response_model=ProductOut, status_code=201)
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    db_product = Product(**product.model_dump())
    db.add(db_product)
    db.flush()
    db.add(Stock(product_id=db_product.id, warehouse_quantity=0, shelf_quantity=0))
    db.commit()
    db.refresh(db_product)
    return db_product


@app.get("/stock", response_model=list[StockOut])
def get_stock(db: Session = Depends(get_db)):
    rows = (
        db.query(Stock, Product.name)
        .join(Product, Stock.product_id == Product.id)
        .all()
    )
    return [
        StockOut(
            product_id=s.product_id,
            product_name=name,
            warehouse_quantity=s.warehouse_quantity,
            shelf_quantity=s.shelf_quantity,
        )
        for s, name in rows
    ]


@app.get("/movements", response_model=list[MovementOut])
def list_movements(db: Session = Depends(get_db)):
    return db.query(Movement).order_by(Movement.timestamp.desc()).all()


@app.post("/stock/in", response_model=MovementOut, status_code=201)
def stock_in(payload: StockMovement, db: Session = Depends(get_db)):
    stock = db.query(Stock).filter(Stock.product_id == payload.product_id).first()
    if not stock:
        raise HTTPException(status_code=404, detail="Product not found")
    stock.warehouse_quantity += payload.box_count
    movement = Movement(
        product_id=payload.product_id,
        movement_type="IN",
        box_count=payload.box_count,
    )
    db.add(movement)
    db.commit()
    db.refresh(movement)
    return movement


@app.post("/stock/out", response_model=MovementOut, status_code=201)
def stock_out(payload: StockMovement, db: Session = Depends(get_db)):
    stock = db.query(Stock).filter(Stock.product_id == payload.product_id).first()
    if not stock:
        raise HTTPException(status_code=404, detail="Product not found")
    if stock.warehouse_quantity < payload.box_count:
        raise HTTPException(status_code=400, detail="Insufficient warehouse stock")
    stock.warehouse_quantity -= payload.box_count
    movement = Movement(
        product_id=payload.product_id,
        movement_type="OUT",
        box_count=payload.box_count,
    )
    db.add(movement)
    db.commit()
    db.refresh(movement)
    return movement


@app.get("/events", response_model=list[EventOut])
def list_events(db: Session = Depends(get_db)):
    return db.query(Event).order_by(Event.timestamp.desc()).all()


@app.post("/events", status_code=201)
def create_event(payload: EventCreate, db: Session = Depends(get_db)):
    existing = (
        db.query(Event)
        .filter(
            Event.tracking_id == payload.tracking_id,
            Event.direction == payload.direction,
        )
        .first()
    )
    if existing:
        return {"status": "ignored", "detail": "Duplicate event — already recorded"}

    stock = db.query(Stock).filter(Stock.product_id == payload.product_id).first()
    if not stock:
        raise HTTPException(status_code=404, detail="Product not found")

    if payload.direction == "OUT" and stock.warehouse_quantity < 1:
        raise HTTPException(status_code=400, detail="Insufficient warehouse stock")

    event = Event(
        tracking_id=payload.tracking_id,
        product_id=payload.product_id,
        direction=payload.direction,
    )
    db.add(event)

    if payload.direction == "IN":
        stock.warehouse_quantity += 1
    else:
        stock.warehouse_quantity -= 1

    movement = Movement(
        product_id=payload.product_id,
        movement_type=payload.direction,
        box_count=1,
    )
    db.add(movement)
    db.commit()
    db.refresh(event)
    return {"status": "recorded", "event_id": event.event_id}
