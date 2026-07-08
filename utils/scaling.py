import os
import ctypes


_SCALE = None


def get_scale_factor():
    global _SCALE
    if _SCALE is not None:
        return _SCALE
    try:
        user32 = ctypes.windll.user32
        screen_width = user32.GetSystemMetrics(0)
    except Exception:
        screen_width = 1920
    _SCALE = min(max(screen_width / 1920.0, 0.55), 1.0)
    return _SCALE


def apply_scaling():
    scale = get_scale_factor()
    if scale < 1.0:
        os.environ["QT_SCALE_FACTOR"] = str(scale)
