# ==========================================
# GÖRÜNTÜ İŞLEME (CV) YAPILANDIRMA DOSYASI
# ==========================================

# 1. KAMERA AYARLARI
# Bilgisayarın kendi kamerasını kullanmak için 0 yazın.
# Eğer ağ üzerinden bir IP kamera kullanacaksanız URL girin (Örn: "rtsp://192.168.1.100/stream")
# Canlı kamera (0) kullanıyoruz.
CAMERA_SOURCE = 0

# 2. YAPAY ZEKA MODELİ AYARLARI
# Obje tespiti için YOLOv8'in en hızlı ve hafif modeli olan nano ('n') versiyonunu seçiyoruz.
# İlk çalıştırmada internetten otomatik olarak indirilecektir.
YOLO_MODEL_PATH = "yolov8n.pt"

# 3. KUTU/ÜRÜN TİPLERİ (Kişi B'nin veritabanı ile eşleşecek)
# Şimdilik 5 örnek koli tipi belirledik. Arkadaşınız backend'i kurduğunda
# buradaki numaralar onun veritabanındaki ID'ler ile aynı olmalı.
PRODUCT_TYPES = {
    1: "Elektronik",
    2: "Gıda",
    3: "Tekstil",
    4: "Kırtasiye",
    5: "Temizlik"
}

# 4. BACKEND API AYARLARI
# Arkadaşınız API'yi yazıp çalıştırdığında genelde localhost:8000 adresinde olur.
BACKEND_API_URL = "http://localhost:8000"
