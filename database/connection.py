import sqlite3
import os
import threading
import traceback
from pathlib import Path

from utils.logger import log_error


class DatabaseManager:
    _instance = None
    _lock = threading.Lock()

    def __init__(self, db_path=None):
        if db_path is None:
            db_dir = Path(__file__).parent.parent / "data"
            db_dir.mkdir(exist_ok=True)
            db_path = str(db_dir / "pharma.db")
        self.db_path = db_path
        self._local = threading.local()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def get_connection(self):
        if not hasattr(self._local, "connection") or self._local.connection is None:
            try:
                self._local.connection = sqlite3.connect(self.db_path)
                self._local.connection.execute("PRAGMA journal_mode=WAL")
                self._local.connection.execute("PRAGMA synchronous=NORMAL")
                self._local.connection.execute("PRAGMA foreign_keys=ON")
                self._local.connection.execute("PRAGMA busy_timeout=5000")
                self._local.connection.row_factory = sqlite3.Row
            except Exception as e:
                log_error("DB", f"Connection failed: {e}\n{traceback.format_exc()}")
                raise
        return self._local.connection

    def execute(self, query, params=None):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            conn.commit()
            return cursor
        except Exception as e:
            log_error("DB", f"Execute failed: {query[:100]}...\nParams: {params}\n{traceback.format_exc()}")
            raise

    def fetchone(self, query, params=None):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchone()
        except Exception as e:
            log_error("DB", f"fetchone failed: {query[:100]}...\nParams: {params}\n{traceback.format_exc()}")
            raise

    def fetchall(self, query, params=None):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchall()
        except Exception as e:
            log_error("DB", f"fetchall failed: {query[:100]}...\nParams: {params}\n{traceback.format_exc()}")
            raise

    def close(self):
        if hasattr(self._local, "connection") and self._local.connection:
            try:
                self._local.connection.close()
            except Exception as e:
                log_error("DB", f"Close failed: {e}")
            self._local.connection = None
