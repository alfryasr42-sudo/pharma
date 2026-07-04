import sys
import os
from version import VERSION
from utils.modern_msgbox import ModernMessageBox as QMessageBox

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from database.connection import DatabaseManager
from database.schema import migrate
from views.login_dialog import LoginDialog
from views.main_window import MainWindow
from utils.backup import DatabaseBackup
from utils.logger import setup_global_hook, get_logger


def initialize_database():
    db = DatabaseManager()
    migrate(db)
    return db


def load_stylesheet(app):
    style_path = os.path.join(BASE_DIR, "resources", "styles", "style.qss")
    if os.path.exists(style_path):
        with open(style_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())


def shutdown_backup():
    db = DatabaseManager()
    backup = DatabaseBackup(db.db_path)
    try:
        backup.create_backup()
        backup.cleanup_old_backups(keep_days=30)
    except Exception:
        pass


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("PharmaSys")
    app.setApplicationVersion(VERSION)

    font = QFont("Segoe UI", 10)
    app.setFont(font)

    load_stylesheet(app)
    setup_global_hook()
    get_logger()

    try:
        initialize_database()
    except Exception as e:
        QMessageBox.critical(None, "خطأ في قاعدة البيانات",
                             f"فشل في تهيئة قاعدة البيانات:\n{str(e)}")
        sys.exit(1)

    login = LoginDialog()
    if login.exec_() != LoginDialog.Accepted:
        sys.exit(0)

    user_data = login.user_data

    window = MainWindow(user_data)
    window.show()

    ret = app.exec_()

    shutdown_backup()

    sys.exit(ret)


if __name__ == "__main__":
    main()
