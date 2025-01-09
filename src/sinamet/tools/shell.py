import time

info_timer = time.time()


def info(string):
    global info_timer
    delta_time = time.time() - info_timer
    print(f"/\\/\\/\\/ {string} ({delta_time:.3f} s)")
    info_timer += delta_time
