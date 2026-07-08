import os
import sys
import json
import shutil
import tempfile
import threading
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError
from version import VERSION

UPDATE_URL = "https://raw.githubusercontent.com/alfryasr42-sudo/pharma/main/update_manifest.json"


def check_for_update():
    """Return (latest_version, download_url, notes) or None if error/up-to-date."""
    try:
        req = Request(UPDATE_URL, headers={"User-Agent": "RTX-Pharma/1.0"})
        with urlopen(req, timeout=10) as resp:
            manifest = json.loads(resp.read().decode("utf-8"))
        latest = manifest.get("version", "")
        if not latest or latest == VERSION:
            return None
        return (
            latest,
            manifest.get("download_url", ""),
            manifest.get("release_notes", ""),
        )
    except Exception:
        return None


def _get_app_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def download_update(url, on_progress=None):
    """Download update to temp dir. Return path to downloaded file."""
    resp = urlopen(Request(url, headers={"User-Agent": "RTX-Pharma/1.0"}), timeout=120)
    total = int(resp.headers.get("Content-Length", 0))
    chunk_size = 8192
    tmp = tempfile.mkdtemp()
    dest = Path(tmp) / "RTX_Update.exe"
    downloaded = 0
    with open(dest, "wb") as f:
        while True:
            chunk = resp.read(chunk_size)
            if not chunk:
                break
            f.write(chunk)
            downloaded += len(chunk)
            if on_progress and total:
                on_progress(downloaded / total)
    return str(dest)


def apply_update(downloaded_path):
    """Replace current exe with downloaded one and restart."""
    import subprocess
    import time

    app_dir = _get_app_dir()
    current_exe = app_dir / "PharmaSys.exe"
    new_exe = Path(downloaded_path)
    batch = app_dir / "_restart.bat"

    batch.write_text(
        f'@echo off\r\n'
        f'chcp 65001 >nul\r\n'
        f'timeout /t 2 /nobreak >nul\r\n'
        f':retry\r\n'
        f'del /f /q "{current_exe}"\r\n'
        f'if exist "{current_exe}" goto retry\r\n'
        f'copy /y "{new_exe}" "{current_exe}" >nul\r\n'
        f'start "" "{current_exe}"\r\n'
        f'del /f /q "{new_exe}"\r\n'
        f'del /f /q "%~f0"\r\n',
        encoding="ascii"
    )

    subprocess.Popen([str(batch)], shell=True)
