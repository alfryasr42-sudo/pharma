import re
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


def sc(value):
    return int(value * get_scale_factor())


def scale_stylesheet(qss_text):
    scale = get_scale_factor()
    if scale >= 1.0:
        return qss_text

    def _scale_px(m):
        num = int(m.group(1))
        return f"{sc(num)}px"

    return re.sub(r"(\d+)px", _scale_px, qss_text)
