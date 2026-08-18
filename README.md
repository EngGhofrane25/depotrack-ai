# 📦 Depo Stok Takip Sistemi (Yapay Zeka Destekli)

Bu proje, bir depo bandından (conveyor) veya kapısından geçen ürünleri **Kamera ve Yapay Zeka (YOLO)** kullanarak otomatik algılayan, sınıflandıran ve stokları güncelleyen bir otomasyon sistemidir.

## ✨ Özellikler
- **Gerçek Zamanlı Nesne Tespiti (YOLOv8):** Ekrana giren kolileri anında tespit eder.
- **Sarsılmaz Takip (Robust Centroid Tracking):** Kameradaki anlık bulanıklıklara veya ID düşmelerine karşı kendi geliştirdiğimiz mesafe-bazlı özel takip algoritmasıyla koli çizgiden geçerken takip edilir. İçeri girenlere (+1), depodan çıkanlara (-1) yazılır.
- **Sınıflandırma:** Ürünleri kategorilerine ayırır (Elektronik, Gıda, Temizlik, Tekstil, Kırtasiye).
- **Canlı Web Paneli:** Kamerayı (MJPEG stream) ve güncel stok durumunu anlık olarak tarayıcı üzerinden izleyebilirsiniz.
- **REST API:** FastAPI ile yazılmış arka uç sistemi ve "Mükerrer Kayıt (Çifte Sayım) Koruması" sayesinde çok kararlı çalışır.

## 🚀 Teknolojiler
- **Görüntü İşleme:** OpenCV, Ultralytics (YOLOv8)
- **Arka Uç (Backend):** Python, FastAPI, Uvicorn
- **Ön Uç (Frontend):** HTML, CSS, JavaScript (Fetch API)

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
