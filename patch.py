import re

with open('cv/camera_feed.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add debounce dictionary
content = content.replace('my_trackers = []', 'my_trackers = []\n    debounce_timers = {} # Titresim engelleme (cooldown) icin')

# 2. Add bytetrack.yaml to model.track
content = content.replace('model.track(detect_frame, persist=True, verbose=False, conf=0.15)', 'model.track(detect_frame, persist=True, tracker=\"bytetrack.yaml\", verbose=False, conf=0.15)')

# 3. Add debounce logic to IN
in_logic_old = '''                        if previous_state == 0 and current_state == 1:
                            product_id = classify_cache.get(my_id, 0)'''
in_logic_new = '''                        if previous_state == 0 and current_state == 1:
                            if time.time() - debounce_timers.get(my_id, 0) < 3.0:
                                pass # Cooldown suresi dolmadi (titresim engellendi)
                            else:
                                debounce_timers[my_id] = time.time()
                                product_id = classify_cache.get(my_id, 0)'''
content = content.replace(in_logic_old, in_logic_new)

# 4. Add debounce logic to OUT
out_logic_old = '''                        elif previous_state == 1 and current_state == 0:
                            product_id = classify_cache.get(my_id, 0)'''
out_logic_new = '''                        elif previous_state == 1 and current_state == 0:
                            if time.time() - debounce_timers.get(my_id, 0) < 3.0:
                                pass # Cooldown suresi dolmadi
                            else:
                                debounce_timers[my_id] = time.time()
                                product_id = classify_cache.get(my_id, 0)'''
content = content.replace(out_logic_old, out_logic_new)

# Ensure indentation is right
content = content.replace('                                product_id = classify_cache.get(my_id, 0)', '                                product_id = classify_cache.get(my_id, 0)')

with open('cv/camera_feed.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Patched camera_feed.py')
