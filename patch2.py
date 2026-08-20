import time

with open('cv/camera_feed.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if "my_trackers = []" in line:
        new_lines.append(line)
        new_lines.append("    debounce_timers = {} # Titresim engelleme\n")
    elif 'results = model.track(detect_frame, persist=True, verbose=False, conf=0.15)' in line:
        new_lines.append('            results = model.track(detect_frame, persist=True, tracker="bytetrack.yaml", verbose=False, conf=0.15)\n')
    elif 'if previous_state == 0 and current_state == 1:' in line:
        new_lines.append(line)
        new_lines.append('                            if time.time() - debounce_timers.get(my_id, 0) < 3.0:\n')
        new_lines.append('                                continue\n')
        new_lines.append('                            debounce_timers[my_id] = time.time()\n')
    elif 'elif previous_state == 1 and current_state == 0:' in line:
        new_lines.append(line)
        new_lines.append('                            if time.time() - debounce_timers.get(my_id, 0) < 3.0:\n')
        new_lines.append('                                continue\n')
        new_lines.append('                            debounce_timers[my_id] = time.time()\n')
    else:
        new_lines.append(line)

with open('cv/camera_feed.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

