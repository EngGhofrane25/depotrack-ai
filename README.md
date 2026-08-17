# Depo Stok Takip Sistemi

Kamera + görüntü işleme ile koli giriş/çıkışını algılayıp depo ve raf stoğunu
otomatik güncelleyen, kritik stokta toptancıya mesaj taslağı hazırlayan sistem.

## Klasör Yapısı

```
depo-stok-projesi/
├── cv/                     # Kişi A — kamera, YOLO, tracking, sınıflandırma
│   ├── camera.py           # Kameradan canlı görüntü alma
│   ├── detector.py         # YOLO ile koli tespiti
│   ├── config.py           # Ortak ayarlar (kamera kaynağı, model yolu vb.)
│   └── requirements.txt
├── backend/                # Kişi B — FastAPI, veritabanı, API'ler
│   ├── main.py
│   ├── models.py
│   ├── database.py
│   └── requirements.txt
├── data/
│   └── kutu_gorselleri/    # Gün 3+ toplanacak koli fotoğrafları (ürün başına klasör)
└── notebooks/               # Deneme/test için (model eğitimi vb.)
```

## Kurulum (Kişi A — CV tarafı)

```bash
cd cv
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Kurulum (Kişi B — Backend tarafı)

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

## Gün 1-2 Durumu

- [x] Repo ve klasör yapısı
- [x] Kamera görüntü alma iskeleti (`cv/camera.py`)
- [x] YOLO tespit iskeleti (`cv/detector.py`)
- [x] Backend API iskeleti (`backend/main.py`)
- [ ] Kamera kaynağının gerçek RTSP/USB adresiyle test edilmesi
- [ ] İlk 5 ürün/koli tipinin `config.py` içine girilmesi
