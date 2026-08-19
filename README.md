# 📦 Depo Stok Takip Sistemi (Yapay Zeka Destekli)

Bu proje, bir depo bandından (conveyor) veya kapısından geçen ürünleri **Kamera ve Yapay Zeka (YOLO)** kullanarak otomatik algılayan, sınıflandıran ve stokları güncelleyen bir otomasyon sistemidir.

## ✨ Özellikler
- **Çift Yapay Zeka Mimarisi:** YOLOv8n ile nesne tespiti (Tracking) yaparken, Kendi Eğittiğimiz Özel Model (box_classifier.pt) ile nesneleri %72 doğrulukla sınıflandırır (Gıda, Elektronik vs.).
- **Sarsılmaz Takip (Robust Centroid Tracking):** Kameradaki anlık bulanıklıklara veya ID düşmelerine karşı kendi geliştirdiğimiz özel takip algoritmasıyla koli çizgiden geçerken takip edilir. 
- **Akıllı SKT (Son Kullanım Tarihi) Uyarıları:** Web panelinde tarihi yaklaşan veya tarihi geçen ürünleri kırmızı alarm ile en tepede gösterir.
- **FEFO (İlk Giren İlk Çıkar) Algoritması:** Kamera depodan bir ürünün çıktığını gördüğünde stoktan rastgele eksiltmek yerine, veritabanını tarayarak SKT'si en yakın olan o eski kutuyu bulup sistemden düşer.
- **Gerçek Veritabanı:** SQLite & SQLAlchemy kullanılarak elektrik kesintilerine karşı kalıcı (Persistent) depolama sağlanır. Raporlar CSV formatında indirilebilir.
- **Canlı Web Paneli:** Kamerayı (MJPEG stream), hareket geçmişini ve güncel stok durumunu anlık olarak tarayıcı üzerinden izleyebilirsiniz.

## 🚀 Teknolojiler
- **Görüntü İşleme:** OpenCV, Ultralytics (YOLOv8 + Custom YOLO-cls)
- **Arka Uç & Veritabanı:** Python, FastAPI, Uvicorn, SQLite, SQLAlchemy
- **Ön Uç (Frontend):** HTML, Vanilla CSS, JavaScript (Fetch API)

## 🛠️ Nasıl Çalıştırılır?

1. **Backend'i Başlatın:**
```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```
2. **Kamera Sistemini (Yapay Zekayı) Başlatın:**
```bash
python cv/camera_feed.py
```
3. **Web Panelini Açın:**
Tarayıcınızda `frontend/index.html` dosyasını açarak sistemi kullanmaya başlayabilirsiniz.
