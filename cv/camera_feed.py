import cv2
import numpy as np
from ultralytics import YOLO
import requests
import config
from flask import Flask, Response
import threading
import time
import torch

HAS_CUDA = torch.cuda.is_available()

# ==========================================
# GÜN 11: FLASK SUNUCUSU (CANLI YAYIN İÇİN)
# ==========================================
app = Flask(__name__)
output_jpeg = None
lock = threading.Lock()

def generate():
    global output_jpeg, lock
    while True:
        with lock:
            frame_data = output_jpeg
        if frame_data is None:
            time.sleep(0.05)
            continue
        yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame_data + b'\r\n')

@app.route("/video_feed")
def video_feed():
    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")

# Flask sunucusunu arka planda başlat (Port 5000)
threading.Thread(target=app.run, kwargs={"host": "0.0.0.0", "port": 5000, "debug": False, "use_reloader": False}, daemon=True).start()

# ==========================================
# GÜN 6: KUTU TİPİ TANIMA (YAPAY ZEKA ENTEGRE EDİLDİ)
# ==========================================
print("[BİLGİ] Özel Sınıflandırma Modeli yükleniyor...")
classifier_model = YOLO(config.CLASSIFIER_MODEL_PATH)

def classify_box(box_img):
    """
    Kutuyu kırpılmış görüntü üzerinden özel YoloV8-cls modeli ile sınıflandırır.
    """
    if box_img.size == 0:
        return 0
        
    results = classifier_model(box_img, verbose=False)
    
    # Güven skorunu kontrol et (Düşükse Bilinmeyen de)
    conf = float(results[0].probs.top1conf)
    if conf < 0.40:
        return 0 # Güven düşükse bilinmeyen kabul et
        
    top1_id = int(results[0].probs.top1)
    class_name = results[0].names[top1_id].lower()
    
    if "gida" in class_name: return 2
    elif "elektronik" in class_name: return 1
    elif "temizlik" in class_name: return 5
    elif "kirtasiye" in class_name: return 4
    elif "tekstil" in class_name: return 3
    
    return 0

# ==========================================
# PERFORMANS AYARLARI
# ==========================================
DETECT_WIDTH = 640       # YOLO'ya giden genişlik (orijinal kareden küçültülür → daha hızlı)
DETECT_EVERY_N = 2       # Her N karede bir algılama çalıştır (atlanan karelerde son sonuç kullanılır)


def main():
    print("[BİLGİ] YOLO modeli yükleniyor...")
    model = YOLO(config.YOLO_MODEL_PATH)
    device = 0 if HAS_CUDA else 'cpu'
    print(f"[BİLGİ] Cihaz: {'CUDA GPU' if HAS_CUDA else 'CPU'}")

    print(f"[BİLGİ] Kamera başlatılıyor (Kaynak: {config.CAMERA_SOURCE})...")
    cap = cv2.VideoCapture(config.CAMERA_SOURCE)

    if not cap.isOpened():
        print("[HATA] Kamera açılamadı!")
        return

    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cam_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    LINE_Y = h // 2

    # Koordinat ölçeklendirme faktörü (algılama çerçevesi → orijinal çerçeve)
    scale = DETECT_WIDTH / w
    detect_h = int(h * scale)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter('output.mp4', fourcc, cam_fps, (w, h))

    my_trackers = []
    debounce_timers = {}
    next_id = int(time.time()) # Zaman bazlı ID: her başlatmada eşsiz, backend duplicate kontrolüyle uyumlu
    last_results = None
    frame_count = 0
    classify_cache = {}   # tracking_id → product_id (sınıflandırma sonucu önbellek)

    # FPS ölçümü
    fps_start = time.time()
    fps_frame_count = 0
    current_fps = 0.0

    print("[BİLGİ] Görüntü akışı ve kayıt başladı (output.mp4).")
    print(f"[BİLGİ] Backend adresi: {config.BACKEND_API_URL}")
    print(f"[PERF] Algılama: {DETECT_WIDTH}x{detect_h}px | Her {DETECT_EVERY_N} karede algılama | Cihaz: {'GPU' if HAS_CUDA else 'CPU'} | Sınıflandırma önbellekli")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        fps_frame_count += 1

        # FPS hesaplama (her saniye güncelle)
        elapsed = time.time() - fps_start
        if elapsed >= 1.0:
            current_fps = fps_frame_count / elapsed
            fps_frame_count = 0
            fps_start = time.time()
            print(f"[FPS] {current_fps:.1f} FPS | Aktif takipçi: {len(my_trackers)} | Frame #{frame_count}")

        # === ALGILAMA (her N karede bir, kucuk cercevede) ===
        run_detection = (frame_count % DETECT_EVERY_N == 0)

        if run_detection:
            detect_frame = cv2.resize(frame, (DETECT_WIDTH, detect_h))
            results = model.track(detect_frame, persist=True, tracker="bytetrack.yaml", verbose=False, conf=0.35, device=device)
            last_results = results
        else:
            results = last_results  # Atlanan karelerde son algilama sonuclarini kullan

        current_trackers = []
        box_annotations = []

        if results:
            for r in results:
                boxes = r.boxes

                for i, box in enumerate(boxes):
                    if int(box.cls[0]) == 0:
                        continue

                    x1, y1, x2, y2 = box.xyxy[0]

                    # Koordinatları orijinal çerçeve boyutuna ölçekle
                    x1 = int(x1 / scale)
                    y1 = int(y1 / scale)
                    x2 = int(x2 / scale)
                    y2 = int(y2 / scale)

                    center_x = (x1 + x2) // 2
                    center_y = (y1 + y2) // 2

                    # === GİRİŞ/ÇIKIŞ DURUMU ===
                    current_state = 0 if center_y < LINE_Y else 1

                    best_match = None
                    best_dist = 150 * 150

                    for t in my_trackers:
                        dist = (center_x - t['center'][0])**2 + (center_y - t['center'][1])**2
                        if dist < best_dist:
                            best_dist = dist
                            best_match = t

                    if best_match is not None:
                        my_id = best_match['id']
                        previous_state = best_match['state']

                        if previous_state == 0 and current_state == 1:
                            product_id = classify_cache.get(my_id, 0)
                            product_name = config.PRODUCT_TYPES.get(product_id, "Bilinmeyen")
                            print(f"✅ [GİRDİ] {product_name} (Özel ID: {my_id}) DEPOYA EKLENDİ! (+1)")
                            def send_in_event(payload):
                                try:
                                    resp = requests.post(f"{config.BACKEND_API_URL}/events", json=payload, timeout=3)
                                    print(f"[BACKEND] Status: {resp.status_code}")
                                except Exception as e:
                                    print(f"[BACKEND HATASI - IN] {e}")

                            payload = {"tracking_id": my_id, "product_id": product_id, "direction": "IN"}
                            threading.Thread(target=send_in_event, args=(payload,), daemon=True).start()

                        elif previous_state == 1 and current_state == 0:
                            if time.time() - debounce_timers.get(my_id, 0) >= 3.0:
                                debounce_timers[my_id] = time.time()
                                product_id = classify_cache.get(my_id, 0)
                                product_name = config.PRODUCT_TYPES.get(product_id, "Bilinmeyen")
                                print(f"❌ [ÇIKTI] {product_name} (Özel ID: {my_id}) DEPODAN ÇIKARILDI! (-1)")
                                def send_out_event(payload):
                                    try:
                                        resp = requests.post(f"{config.BACKEND_API_URL}/events", json=payload, timeout=3)
                                        print(f"[BACKEND] Status: {resp.status_code}")
                                    except Exception as e:
                                        print(f"[BACKEND HATASI - OUT] {e}")

                                payload = {"tracking_id": my_id, "product_id": product_id, "direction": "OUT"}
                                threading.Thread(target=send_out_event, args=(payload,), daemon=True).start()

                        best_match['center'] = (center_x, center_y)
                        best_match['state'] = current_state
                        current_trackers.append(best_match)
                        my_trackers.remove(best_match)
                    else:
                        my_id = next_id
                        next_id += 1

                        # Yeni obje: sadece bir kez sınıflandır ve önbelleğe kaydet
                        crop_y1 = max(0, y1)
                        crop_y2 = min(h, y2)
                        crop_x1 = max(0, x1)
                        crop_x2 = min(w, x2)
                        box_img = frame[crop_y1:crop_y2, crop_x1:crop_x2]

                        if box_img.size > 0:
                            product_id = classify_box(box_img)
                        else:
                            product_id = 0
                        classify_cache[my_id] = product_id

                        current_trackers.append({'center': (center_x, center_y), 'state': current_state, 'id': my_id})

                    product_id = classify_cache.get(my_id, 0)
                    product_name = config.PRODUCT_TYPES.get(product_id, "Bilinmeyen")
                    box_annotations.append((x1, y1, x2, y2, center_x, center_y, my_id, product_name))

        my_trackers = current_trackers

        # === GÖRÜNTÜLEME (yatay aynalanmış kare, normal metin) ===
        display_frame = cv2.flip(frame, 1)

        # Referans çizgisi (yatay çizgi — yatay aynalamadan etkilenmez)
        cv2.line(display_frame, (0, LINE_Y), (w, LINE_Y), (255, 0, 0), 2)
        ref_text = "REFERANS CIZGISI"
        (ref_tw, _), _ = cv2.getTextSize(ref_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
        cv2.putText(display_frame, ref_text, (w - 10 - ref_tw, LINE_Y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

        # Kutular, merkezler ve etiketler (x koordinatları aynalanmış)
        for (x1, y1, x2, y2, cx, cy, my_id, product_name) in box_annotations:
            dx1, dx2 = w - x2, w - x1
            dcx = w - cx
            cv2.circle(display_frame, (dcx, cy), 5, (0, 0, 255), -1)
            cv2.rectangle(display_frame, (dx1, y1), (dx2, y2), (0, 255, 0), 2)
            label = f"ID:{my_id} - {product_name}"
            cv2.putText(display_frame, label, (dx1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # FPS ve durum bilgisi ekranda
        cv2.putText(display_frame, f"FPS: {current_fps:.1f}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        status_text = f"Algılama: her {DETECT_EVERY_N} kare | {DETECT_WIDTH}px"
        (stw, _), _ = cv2.getTextSize(status_text, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
        cv2.putText(display_frame, status_text, (w - 10 - stw, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)

        # Canlı yayın karesi (önceden JPEG kodlanmış - kopya ve yeniden kodlama gereksiz)
        global output_jpeg, lock
        _, jpeg_buf = cv2.imencode(".jpg", display_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        with lock:
            output_jpeg = jpeg_buf.tobytes()

        cv2.imshow("Depo Stok Takip - Tracking & Classification", display_frame)
        out.write(display_frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    out.release()
    cv2.destroyAllWindows()
    print("[BİLGİ] Program sonlandırıldı. Çıktı 'output.mp4' olarak kaydedildi.")

if __name__ == "__main__":
    main()