"""
Gün 3 görevi: YOLO ile koli tespiti.

Gün 2'de sadece kamera bağlantısını test ettik. Bu dosya kamera akışını
YOLO'ya bağlar ve tespit edilen kutuları (bounding box) ekranda gösterir.

Not: Başlangıçta hazır COCO modeli kullanıyoruz. COCO'da tam olarak "box/koli"
sınıfı yok ama en yakın sınıflar tespit denemesi için başlangıç noktası olur.
Sonuç yetersizse Gün 6'da kendi verinizle fine-tune edeceğiz.
"""

from ultralytics import YOLO
import cv2
import config
import camera


def model_yukle():
    return YOLO(config.YOLO_MODEL_YOLU)


def canli_tespit(kaynak=config.GIRIS_KAMERA_KAYNAGI):
    """
    Kameradan gelen her frame'de YOLO tespiti yapar, kutuları çizip gösterir.
    Çıkmak için 'q' tuşuna basın.
    """
    model = model_yukle()
    print("Model yüklendi. Kamera açılıyor...")

    for frame in camera.frame_uret(kaynak):
        sonuclar = model(frame, conf=config.GUVEN_ESIGI, verbose=False)[0]

        for kutu in sonuclar.boxes:
            x1, y1, x2, y2 = map(int, kutu.xyxy[0])
            guven = float(kutu.conf[0])
            sinif_id = int(kutu.cls[0])
            sinif_adi = model.names[sinif_id]

            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            etiket = f"{sinif_adi} {guven:.2f}"
            cv2.putText(
                frame, etiket, (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2
            )

        cv2.imshow("Koli Tespiti", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    canli_tespit()
