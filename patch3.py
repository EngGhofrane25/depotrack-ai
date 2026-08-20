import time

with open('cv/camera_feed.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('my_trackers = []', 'my_trackers = []\n    debounce_timers = {}')
content = content.replace('results = model.track(detect_frame, persist=True, verbose=False, conf=0.15)', 'results = model.track(detect_frame, persist=True, tracker=\"bytetrack.yaml\", verbose=False, conf=0.15)')

in_old = '''                        if previous_state == 0 and current_state == 1:
                            product_id = classify_cache.get(my_id, 0)
                            product_name = config.PRODUCT_TYPES.get(product_id, "Bilinmeyen")
                            print(f"✅  [GİRDİ] {product_name} (Özel ID: {my_id}) DEPOYA EKLENDİ! (+1)")
                            try:
                                payload = {"tracking_id": my_id, "product_id": product_id, "direction": "IN"}
                                resp = requests.post(f"{config.BACKEND_API_URL}/events", json=payload, timeout=3)
                                print(f"[BACKEND] Status: {resp.status_code}, Response: {resp.text}")
                            except Exception as e:
                                print(f"[BACKEND HATASI - IN] {e}")'''

in_new = '''                        if previous_state == 0 and current_state == 1:
                            if time.time() - debounce_timers.get(my_id, 0) >= 3.0:
                                debounce_timers[my_id] = time.time()
                                product_id = classify_cache.get(my_id, 0)
                                product_name = config.PRODUCT_TYPES.get(product_id, "Bilinmeyen")
                                print(f"✅  [GİRDİ] {product_name} (Özel ID: {my_id}) DEPOYA EKLENDİ! (+1)")
                                try:
                                    payload = {"tracking_id": my_id, "product_id": product_id, "direction": "IN"}
                                    resp = requests.post(f"{config.BACKEND_API_URL}/events", json=payload, timeout=3)
                                    print(f"[BACKEND] Status: {resp.status_code}, Response: {resp.text}")
                                except Exception as e:
                                    print(f"[BACKEND HATASI - IN] {e}")'''

content = content.replace(in_old, in_new)

out_old = '''                        elif previous_state == 1 and current_state == 0:
                            product_id = classify_cache.get(my_id, 0)
                            product_name = config.PRODUCT_TYPES.get(product_id, "Bilinmeyen")
                            print(f"❌ [ÇIKTI] {product_name} (Özel ID: {my_id}) DEPODAN ÇIKARILDI! (-1)")
                            try:
                                payload = {"tracking_id": my_id, "product_id": product_id, "direction": "OUT"}
                                resp = requests.post(f"{config.BACKEND_API_URL}/events", json=payload, timeout=3)
                                print(f"[BACKEND] Status: {resp.status_code}, Response: {resp.text}")
                            except Exception as e:
                                print(f"[BACKEND HATASI - OUT] {e}")'''

out_new = '''                        elif previous_state == 1 and current_state == 0:
                            if time.time() - debounce_timers.get(my_id, 0) >= 3.0:
                                debounce_timers[my_id] = time.time()
                                product_id = classify_cache.get(my_id, 0)
                                product_name = config.PRODUCT_TYPES.get(product_id, "Bilinmeyen")
                                print(f"❌ [ÇIKTI] {product_name} (Özel ID: {my_id}) DEPODAN ÇIKARILDI! (-1)")
                                try:
                                    payload = {"tracking_id": my_id, "product_id": product_id, "direction": "OUT"}
                                    resp = requests.post(f"{config.BACKEND_API_URL}/events", json=payload, timeout=3)
                                    print(f"[BACKEND] Status: {resp.status_code}, Response: {resp.text}")
                                except Exception as e:
                                    print(f"[BACKEND HATASI - OUT] {e}")'''

content = content.replace(out_old, out_new)

with open('cv/camera_feed.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Patch applied successfully.")
