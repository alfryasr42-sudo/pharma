import zipfile
import os
import shutil
from datetime import datetime
from pathlib import Path


class DatabaseBackup:
    def __init__(self, db_path: str, backup_dir: str = None, cloud_dir: str = None):
        self.db_path = db_path
        self.backup_dir = backup_dir or str(Path.home() / "PharmaSysBackups")
        self.cloud_dir = cloud_dir

    def create_backup(self) -> str:
        os.makedirs(self.backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"pharma_backup_{timestamp}.zip"
        local_path = os.path.join(self.backup_dir, backup_name)

        if not os.path.exists(self.db_path):
            return ""

        with zipfile.ZipFile(local_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(self.db_path, os.path.basename(self.db_path))

        if self.cloud_dir:
            try:
                os.makedirs(self.cloud_dir, exist_ok=True)
                shutil.copy2(local_path, os.path.join(self.cloud_dir, backup_name))
            except Exception:
                pass

        return local_path

    def cleanup_old_backups(self, keep_days: int = 30):
        for fname in os.listdir(self.backup_dir):
            if not fname.startswith("pharma_backup_") or not fname.endswith(".zip"):
                continue
            fpath = os.path.join(self.backup_dir, fname)
            try:
                mtime = os.path.getmtime(fpath)
                age = (datetime.now().timestamp() - mtime) / 86400
                if age > keep_days:
                    os.remove(fpath)
            except Exception:
                pass
