import logging
import sys
import os
import traceback
from functools import wraps
from pathlib import Path
from utils.modern_msgbox import ModernMessageBox as QMessageBox

import hashlib
import base64

LOG_DIR = Path(__file__).parent.parent / "data"
LOG_FILE = LOG_DIR / "error.log"

_logger = None


def _encrypt_text(plaintext: str) -> str:
    return base64.b64encode(plaintext.encode("utf-8")).decode("utf-8")


def _decrypt_logs() -> str:
    if not LOG_FILE.exists():
        return ""
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
    decrypted = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            decrypted.append(base64.b64decode(line.encode("utf-8")).decode("utf-8"))
        except Exception:
            decrypted.append(line)
    return "\n".join(decrypted)


class EncryptedFileHandler(logging.Handler):
    def __init__(self, filename, mode="a", encoding="utf-8"):
        super().__init__()
        self.filename = str(filename)
        self.mode = mode
        self.encoding = encoding
        LOG_DIR.mkdir(exist_ok=True)

    def emit(self, record):
        msg = self.format(record)
        encrypted = _encrypt_text(msg)
        try:
            with open(self.filename, self.mode, encoding=self.encoding) as f:
                f.write(encrypted + "\n")
        except Exception:
            pass


def get_logger():
    global _logger
    if _logger is not None:
        return _logger

    LOG_DIR.mkdir(exist_ok=True)

    _logger = logging.getLogger("RTX")
    _logger.setLevel(logging.ERROR)

    if _logger.handlers:
        return _logger

    handler = EncryptedFileHandler(LOG_FILE)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(module)s:%(lineno)d | %(message)s"
    )
    handler.setFormatter(formatter)
    _logger.addHandler(handler)
    return _logger


def log_error(module: str, message: str):
    logger = get_logger()
    logger.error(f"[{module}] {message}")


import inspect

def safe_operation(user_message: str = None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                sig = inspect.signature(func)
                has_var_args = any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in sig.parameters.values())
                if not has_var_args:
                    num_params = len(sig.parameters)
                    args = args[:num_params]
                return func(*args, **kwargs)
            except Exception as e:
                qualname = func.__qualname__
                tb = traceback.format_exc()
                log_error(
                    func.__module__,
                    f"Exception in {qualname}\nArgs: {args[1:] if args else None}\nTraceback:\n{tb}",
                )
                _try_show_error(args, user_message)
                return None
        return wrapper
    return decorator


def _try_show_error(args, user_message):
    try:
        from PyQt5.QtWidgets import QApplication, QMessageBox, QWidget
        app = QApplication.instance()
        if not app:
            return
        msg = user_message or "عذراً، حدث خطأ غير متوقع. يرجى المحاولة لاحقاً."
        parent = None
        if args and isinstance(args[0], QWidget):
            parent = args[0]
        QMessageBox.critical(parent, "خطأ غير متوقع", msg)
    except Exception:
        pass


def setup_global_hook():
    def global_excepthook(exc_type, exc_value, exc_traceback):
        tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        log_error("GLOBAL", f"Unhandled exception: {tb_str}")
        _try_show_error((), "عذراً، حدث خطأ غير متوقع. سيتم إغلاق التطبيق.")
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            app.quit()

    sys.excepthook = global_excepthook
