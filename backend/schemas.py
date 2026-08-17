from pydantic import BaseModel
from datetime import datetime


class ProductCreate(BaseModel):
    name: str
    items_per_box: int
    critical_threshold: int
    supplier_info: str = ""


class ProductOut(ProductCreate):
    id: int

    model_config = {"from_attributes": True}


class StockOut(BaseModel):
    product_id: int
    product_name: str
    warehouse_quantity: int
    shelf_quantity: int


class MovementOut(BaseModel):
    id: int
    product_id: int
    movement_type: str
    box_count: int
    timestamp: datetime

    model_config = {"from_attributes": True}


class StockMovement(BaseModel):
    product_id: int
    box_count: int


class EventCreate(BaseModel):
    tracking_id: int
    product_id: int
    direction: str


class EventOut(BaseModel):
    event_id: int
    tracking_id: int
    product_id: int
    direction: str
    timestamp: datetime

    model_config = {"from_attributes": True}
