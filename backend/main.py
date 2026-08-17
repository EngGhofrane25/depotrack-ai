"""
Gün 2 görevi (Kişi B): FastAPI iskeleti + ilk API'ler.

Bu dosya sadece başlangıç noktası — gerçek veritabanı bağlantısı ve
iş mantığı models.py / database.py içine taşınacak.
"""

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Depo Stok Takip API")


class UrunGiris(BaseModel):
    urun_adi: str
    koli_icerigi: int
    kritik_stok: int


class StokHareketi(BaseModel):
    urun_id: int
    adet: int  # koli sayısı değil, ürün adedi


@app.get("/products")
def urunleri_listele():
    # TODO: veritabanından çek
    return []


@app.post("/products")
def urun_ekle(urun: UrunGiris):
    # TODO: veritabanına kaydet
    return {"status": "ok", "urun": urun}


@app.get("/stock")
def stok_durumu():
    # TODO: depo + raf stoğunu döndür
    return {"depo": {}, "raf": {}}


@app.get("/movements")
def hareketleri_listele():
    # TODO: stock_movements tablosundan çek
    return []


@app.post("/stock/in")
def stok_giris(hareket: StokHareketi):
    # TODO: depo stoğunu artır, movement kaydet
    return {"status": "ok", "hareket": hareket}


@app.post("/stock/out")
def stok_cikis(hareket: StokHareketi):
    # TODO: depo stoğunu azalt, raf stoğunu artır, movement kaydet
    return {"status": "ok", "hareket": hareket}
