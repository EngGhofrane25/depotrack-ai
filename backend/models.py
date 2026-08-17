from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from .database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    items_per_box = Column(Integer, nullable=False)
    critical_threshold = Column(Integer, nullable=False)
    supplier_info = Column(String, default="")


class Stock(Base):
    __tablename__ = "stocks"

    product_id = Column(Integer, ForeignKey("products.id"), primary_key=True)
    warehouse_quantity = Column(Integer, default=0, nullable=False)
    shelf_quantity = Column(Integer, default=0, nullable=False)


class Movement(Base):
    __tablename__ = "movements"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    movement_type = Column(String, nullable=False)  # "IN" or "OUT"
    box_count = Column(Integer, nullable=False)
    timestamp = Column(DateTime, server_default=func.now())


class Event(Base):
    __tablename__ = "events"

    event_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tracking_id = Column(Integer, nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    direction = Column(String, nullable=False)  # "IN" or "OUT"
    timestamp = Column(DateTime, server_default=func.now())
