"""
Gün 2 görevi: Kameradan canlı görüntü akışı.

Bu dosya sadece kamera bağlantısını test etmek ve frame üretmek içindir.
Tespit (detection) mantığı detector.py içinde.
"""

import cv2
import config


def kamera_ac(kaynak):
    """Kamerayı açar, başarısızsa açıklayıcı hata fırlatır."""
    cap = cv2.VideoCapture(kaynak)
    if not cap.isOpened():
        raise RuntimeError(
            f"Kamera açılamadı: {kaynak}. "
            "USB kamera indeksini (0, 1, 2...) veya RTSP adresini kontrol edin."
        )
    return cap


def canli_goruntu_test(kaynak=config.GIRIS_KAMERA_KAYNAGI):
    """
    Basit test: kamerayı açar, görüntüyü ekranda gösterir.
    Çıkmak için 'q' tuşuna basın.
    """
    cap = kamera_ac(kaynak)
    print("Kamera açıldı. Çıkmak için 'q' tuşuna basın.")

    while True:
        basarili, frame = cap.read()
        if not basarili:
            print("Frame okunamadı, bağlantı kopmuş olabilir.")
            break

        cv2.imshow("Kamera Testi", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


def frame_uret(kaynak):
    """
    Generator: sürekli frame üretir. detector.py bunu kullanacak.
    Kullanım: for frame in frame_uret(kaynak): ...
    """
    cap = kamera_ac(kaynak)
    try:
        while True:
            basarili, frame = cap.read()
            if not basarili:
                print("Frame okunamadı, akış sonlandırılıyor.")
                break
            yield frame
    finally:
        cap.release()


if __name__ == "__main__":
    # Doğrudan çalıştırınca kamerayı test eder.
    canli_goruntu_test()
