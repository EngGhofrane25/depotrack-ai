import cv2
import numpy as np
from ultralytics import YOLO
import requests
import config
from flask import Flask, Response
import threading
import time

# ==========================================
# GÜN 11: FLASK SUNUCUSU (CANLI YAYIN İÇİN)
# ==========================================
app = Flask(__name__)
output_frame = None
lock = threading.Lock()

def generate():
    global output_frame, lock
    while True:
        if output_frame is None:
            time.sleep(0.1)
            continue
            
        with lock:
            # Kareyi JPEG formatına çevir
            (flag, encodedImage) = cv2.imencode(".jpg", output_frame)
            
        if not flag:
            continue
            
        # Tarayıcıya gönder (MJPEG formatı)
        yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + bytearray(encodedImage) + b'\r\n')
        time.sleep(0.03) # ~30 FPS

@app.route("/video_feed")
def video_feed():
    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")

# Flask sunucusunu arka planda başlat (Port 5000)
threading.Thread(target=app.run, kwargs={"host": "0.0.0.0", "port": 5000, "debug": False, "use_reloader": False}, daemon=True).start()

# ==========================================
# GÜN 6: KUTU TİPİ TANIMA (MOCK Sınıflandırma)
# ==========================================

def classify_box(box_img):
    """
    Şimdilik (Geçici) Sınıflandırma Fonksiyonu.
    Kutunun ortalama rengine bakarak 5 üründen birini tahmin eder.
    Gerçek model geldiğinde bu fonksiyonun içi değiştirilecektir.
    """
    # Görüntünün ortalama BGR (Mavi, Yeşil, Kırmızı) renklerini alıyoruz
    avg_color_per_row = np.average(box_img, axis=0)
    avg_color = np.average(avg_color_per_row, axis=0)
    
    b, g, r = avg_color
    
    # Renge göre çok basit bir mantıkla ürün uyduruyoruz
    if r > b and r > g:
        return 2  # Gıda (Kırmızı ağırlıklıysa)
    elif b > r and b > g:
        return 1  # Elektronik (Mavi ağırlıklıysa)
    elif g > r and g > b:
        return 5  # Temizlik (Yeşil ağırlıklıysa)
    elif r > 150 and g > 150 and b < 100:
        return 4  # Kırtasiye (Sarı/Turuncu ağırlıklıysa)
    else:
        return 3  # Tekstil (Diğer renkler)


def main():
    print("[BİLGİ] YOLO modeli yükleniyor...")
    model = YOLO(config.YOLO_MODEL_PATH)

    print(f"[BİLGİ] Kamera başlatılıyor (Kaynak: {config.CAMERA_SOURCE})...")
    cap = cv2.VideoCapture(config.CAMERA_SOURCE)

    if not cap.isOpened():
        print("[HATA] Kamera açılamadı!")
        return

    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    LINE_Y = h // 2 

    # Videoyu kaydetmek için VideoWriter
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter('output.mp4', fourcc, fps, (w, h))

    # KENDİ TAKİP ALGORİTMAMIZ İÇİN DEĞİŞKENLER
    my_trackers = [] 
    next_id = 1

    print("[BİLGİ] Görüntü akışı ve kayıt başladı (output.mp4).")
    print(f"[BİLGİ] Backend adresi: {config.BACKEND_API_URL}")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        cv2.line(frame, (0, LINE_Y), (w, LINE_Y), (255, 0, 0), 2)
        cv2.putText(frame, "REFERANS CIZGISI", (10, LINE_Y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

        results = model.track(frame, persist=True, verbose=False)

        current_trackers = []
        for r in results:
            boxes = r.boxes
                
            for i, box in enumerate(boxes):
                x1, y1, x2, y2 = box.xyxy[0]
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2
                
                cv2.circle(frame, (center_x, center_y), 5, (0, 0, 255), -1)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                
                # ==========================================
                # GÜN 6: KIRPMA VE SINIFLANDIRMA (YENİ EKLENDİ)
                # ==========================================
                # Hata vermemesi için koordinatları ekran sınırlarında tutuyoruz
                crop_y1 = max(0, y1)
                crop_y2 = min(h, y2)
                crop_x1 = max(0, x1)
                crop_x2 = min(w, x2)
                
                # Kutuyu orijinal çerçeveden kırpıyoruz (Crop)
                box_img = frame[crop_y1:crop_y2, crop_x1:crop_x2]
                
                # Çok küçük veya geçersiz kırpmaları yoksay
                if box_img.size > 0:
                    product_id = classify_box(box_img)
                    product_name = config.PRODUCT_TYPES.get(product_id, "Bilinmeyen")
                else:
                    product_id = 0
                    product_name = "Bilinmeyen"
                
                # ==========================================
                # SARSILMAZ GİRİŞ/ÇIKIŞ ALGORİTMAMIZ
                # ==========================================
                current_state = 0 if center_y < LINE_Y else 1
                
                best_match = None
                best_dist = 150 * 150 # Maksimum 150 piksel mesafe zıplaması
                
                for t in my_trackers:
                    dist = (center_x - t['center'][0])**2 + (center_y - t['center'][1])**2
                    if dist < best_dist:
                        best_dist = dist
                        best_match = t
                
                if best_match is not None:
                    # Mevcut objeyi bulduk
                    my_id = best_match['id']
                    previous_state = best_match['state']
                    
                    if previous_state == 0 and current_state == 1:
                        print(f"✅ [GİRDİ] {product_name} (Özel ID: {my_id}) DEPOYA EKLENDİ! (+1)")
                        try:
                            payload = {"tracking_id": my_id, "product_id": product_id, "direction": "IN"}
                            resp = requests.post(f"{config.BACKEND_API_URL}/events", json=payload, timeout=3)
                            print(f"[BACKEND] Status: {resp.status_code}, Response: {resp.text}")
                        except Exception as e:
                            print(f"[BACKEND HATASI - IN] {e}")
                        
                    elif previous_state == 1 and current_state == 0:
                        print(f"❌ [ÇIKTI] {product_name} (Özel ID: {my_id}) DEPODAN ÇIKARILDI! (-1)")
                        try:
                            payload = {"tracking_id": my_id, "product_id": product_id, "direction": "OUT"}
                            resp = requests.post(f"{config.BACKEND_API_URL}/events", json=payload, timeout=3)
                            print(f"[BACKEND] Status: {resp.status_code}, Response: {resp.text}")
                        except Exception as e:
                            print(f"[BACKEND HATASI - OUT] {e}")

                    # Objeyi güncelleyip yeni listeye ekle, eskisinden çıkar
                    best_match['center'] = (center_x, center_y)
                    best_match['state'] = current_state
                    current_trackers.append(best_match)
                    my_trackers.remove(best_match)
                else:
                    # Tamamen yeni bir obje
                    my_id = next_id
                    next_id += 1
                    current_trackers.append({'center': (center_x, center_y), 'state': current_state, 'id': my_id})
                
                # Kendi ID'mizi Ekrana Yazdır
                text = f"ID:{my_id} - {product_name}"
                cv2.putText(frame, text, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # Bu karedeki objeleri, bir sonraki karenin "Geçmişi" olarak ayarla
        my_trackers = current_trackers

        # GÜN 11: Kareyi Canlı Yayın İçin Kaydet
        global output_frame, lock
        with lock:
            output_frame = frame.copy()

        cv2.imshow("Depo Stok Takip - Tracking & Classification", frame)
        out.write(frame) # İşlenmiş kareyi videoya kaydet

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    out.release() # Video dosyasını kapat
    cv2.destroyAllWindows()
    print("[BİLGİ] Program sonlandırıldı. Çıktı 'output.mp4' olarak kaydedildi.")

if __name__ == "__main__":
    main()