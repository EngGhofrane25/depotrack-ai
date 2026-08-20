import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 🚀 ENDÜSTRİYEL VERİTABANI ALTYAPISI
# Çevresel değişken (Environment Variable) olarak DATABASE_URL verilirse 
# sistem otomatik olarak PostgreSQL'e veya MySQL'e bağlanır. 
# Verilmezse, yerel testler için varsayılan olarak SQLite kullanmaya devam eder.
#
# PostgreSQL örnek formatı:
# DATABASE_URL = "postgresql://kullanici:sifre@localhost:5432/depo_db"

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./stock.db")

# Eğer SQLite kullanılıyorsa thread ayarı gerekir, PostgreSQL vb. için gerekmez.
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
