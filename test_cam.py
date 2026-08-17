import cv2
import time

print("Kamera aciliyor (Kaynak: 0)...")
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("HATA: Kamera isOpened() False dondu. (Kamera bulunamadı veya başka uygulama kullanıyor)")
else:
    print("Kamera baglantisi basarili.")
    # Kameranın uyanması için 1 saniye bekle
    time.sleep(1)
    ret, frame = cap.read()
    print(f"Kare okunabiliyor mu?: {ret}")
    if ret:
        print(f"Kare boyutu: {frame.shape}")
    else:
        print("HATA: Kamera acildi ancak hicbir goruntu (kare) gelmiyor! (Windows Gizlilik ayarlari kamerayi engelliyor olabilir)")

cap.release()
