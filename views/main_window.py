import os
import sys
import shutil
import threading
import datetime
from pathlib import Path
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QMessageBox,
    QStackedWidget, QStatusBar, QApplication,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QShortcut
from version import VERSION
from utils.modern_msgbox import ModernMessageBox as QMessageBox

from database.connection import DatabaseManager
from views.dashboard_widget import DashboardWidget
from views.pos_widget import POSWidget
from views.inventory_widget import InventoryWidget
from views.debts_widget import DebtsWidget
from views.doctors_widget import DoctorsWidget
from views.settings_widget import SettingsWidget
from views.reports_widget import ReportsWidget
from views.top_bar import TopBar
from controllers.expiry_controller import ExpiryController
from controllers.product_controller import ProductController
from utils.toast import ToastNotification


class MainWindow(QMainWindow):
    def __init__(self, user_data: dict):
        super().__init__()
        self.user_data = user_data
        self.is_admin = self.user_data.get("role") == "admin"
        self.db = DatabaseManager()
        self.expiry_ctrl = ExpiryController()
        self.product_ctrl = ProductController()
        self.setWindowTitle(f"RTX v{VERSION} - {user_data['full_name']}")
        self.setMinimumSize(1200, 750)
        # نافذة ملء الشاشة وبدون إطار
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.showFullScreen()
        self._setup_ui()
        self._setup_hotkeys()
        QTimer.singleShot(500, self._check_alerts)
        QTimer.singleShot(2000, self.top_bar.check_startup)
        QTimer.singleShot(3000, self._check_for_update)

    def closeEvent(self, event):
        """منع الإغلاق العرضي - الإغلاق فقط عبر زر الخروج الداخلي"""
        event.ignore()


    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.top_bar = TopBar()
        self.top_bar.navigate.connect(self._on_navigate)
        main_layout.addWidget(self.top_bar)
        self.top_bar.home_btn.setVisible(False)

        self.stack = QStackedWidget()

        self.dashboard = DashboardWidget(self.user_data)
        self.dashboard.navigate.connect(self._on_navigate)

        self.pos_widget = POSWidget(self.user_data)
        self.pos_widget.sale_completed.connect(self._on_sale_completed)

        self.inventory_widget = InventoryWidget()
        self.debts_widget = DebtsWidget()
        self.doctors_widget = DoctorsWidget()
        self.settings_widget = SettingsWidget(self.user_data)
        self.settings_widget.users_changed.connect(self._on_users_changed)
        self.reports_widget = ReportsWidget(self.user_data)

        self.stack.addWidget(self.dashboard)     # 0
        self.stack.addWidget(self.pos_widget)     # 1
        self.stack.addWidget(self.inventory_widget)  # 2
        self.stack.addWidget(self.debts_widget)   # 3
        self.stack.addWidget(self.doctors_widget) # 4
        self.stack.addWidget(self.settings_widget)  # 5
        self.stack.addWidget(self.reports_widget)   # 6

        main_layout.addWidget(self.stack)
        central.setLayout(main_layout)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.setStyleSheet("background: #1a1a2e; color: rgba(255,255,255,150); padding: 4px;")
        self.status_bar.showMessage(f"📦 RTX v{VERSION} — {self.user_data['full_name']}", 5000)

    def _setup_hotkeys(self):
        QShortcut(QKeySequence("F1"), self, lambda: self._switch_view("debts"))
        QShortcut(QKeySequence("F2"), self, lambda: self._switch_view("pos"))
        QShortcut(QKeySequence("F3"), self, lambda: self._switch_view("inventory"))
        QShortcut(QKeySequence("F4"), self, lambda: self._switch_view("doctors"))
        if self.is_admin:
            QShortcut(QKeySequence("F5"), self, lambda: self._switch_view("settings"))
        QShortcut(QKeySequence("Escape"), self, lambda: self._switch_view("dashboard"))
        QShortcut(QKeySequence("Ctrl+Q"), self, self.close)

    def _on_navigate(self, target):
        if target == "logout":
            self._logout()
        elif target == "settings" and not self.is_admin:
            QMessageBox.warning(self, "وصول ممنوع", "هذه الصفحة مخصصة لمدير النظام فقط")
        else:
            self._switch_view(target)

    def _switch_view(self, view_name):
        if view_name == "dashboard":
            self.stack.setCurrentIndex(0)
            self.status_bar.clearMessage()
            self.top_bar.home_btn.setVisible(False)
            self.dashboard._load_expired()
            self.dashboard._load_low_stock()
            return

        self.top_bar.home_btn.setVisible(True)

        if view_name == "settings" and not self.is_admin:
            QMessageBox.warning(self, "وصول ممنوع", "هذه الصفحة مخصصة لمدير النظام فقط")
            return

        index_map = {
            "pos": 1, "inventory": 2, "debts": 3,
            "doctors": 4, "settings": 5, "reports": 6,
        }
        idx = index_map.get(view_name, 0)
        self.stack.setCurrentIndex(idx)

        name_map = {
            "pos": "🛒 نقطة البيع", "inventory": "📦 المخزون",
            "debts": "💰 الديون", "doctors": "👨‍⚕️ الأطباء",
            "settings": "⚙️ الإعدادات", "reports": "📊 التقارير",
        }
        name = name_map.get(view_name, "")
        self.status_bar.showMessage(f"📍 {name}")

        if view_name == "debts":
            self.debts_widget._load_debts()
        if view_name == "settings":
            self.settings_widget._load_users()
        if view_name == "inventory":
            self.inventory_widget._load_products()
        if view_name == "reports":
            self.reports_widget._load_today_report()

    def _on_sale_completed(self, sale_id):
        self._switch_view("pos")

    def _on_users_changed(self):
        QMessageBox.information(self, "تم", "تم تحديث بيانات المستخدمين\nسيتم تطبيق التغييرات عند تسجيل الدخول التالي")

    def _check_alerts(self):
        expired = self.expiry_ctrl.get_expired()
        expiring = self.expiry_ctrl.get_expiring_soon(90)
        low_stock = self.product_ctrl.get_low_stock()
        alerts = []
        if expired:
            names = "\n".join(f"• {p['name']} (صلاحية: {p['expiry_date']})" for p in expired[:10])
            alerts.append(f"⚠️ منتهية ({len(expired)}):\n{names}")
        if expiring:
            names = "\n".join(f"• {p['name']} (صلاحية: {p['expiry_date']})" for p in expiring[:10])
            alerts.append(f"⏳ قرب الانتهاء ({len(expiring)}):\n{names}")
        if low_stock:
            names = "\n".join(f"• {p['name']} (المتبقي: {p['stock_quantity']})" for p in low_stock[:10])
            alerts.append(f"📦 تحت الأمان ({len(low_stock)}):\n{names}")
        if alerts:
            msg = "\n\n".join(alerts)
            ToastNotification.show_message(msg, 30000, self, "تنبيهات المخزون")

    def _check_for_update(self):
        from utils.updater import check_for_update, download_update, UPDATE_URL

        def _do_check():
            try:
                result = check_for_update()
                if result is None:
                    return
                latest_ver, dl_url, notes = result

                from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar
                from PyQt5.QtCore import Qt

                dialog = QDialog(self)
                dialog.setWindowTitle("🔄 تحديث متاح")
                dialog.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
                dialog.setStyleSheet("QDialog{background:#0b1120;border:1px solid #1e293b;border-radius:12px;}")
                dialog.resize(480, 380)

                lay = QVBoxLayout(dialog)
                lay.setContentsMargins(24, 20, 24, 20)
                lay.setSpacing(12)

                title = QLabel(f"🔄 تحديث جديد متاح v{latest_ver}")
                title.setStyleSheet("font-size:20px;font-weight:700;color:#14b8a6;background:transparent;border:none;")
                lay.addWidget(title)

                info = QLabel(f"النسخة الحالية: v{VERSION}\nالنسخة الجديدة: v{latest_ver}")
                info.setStyleSheet("font-size:14px;color:#94a3b8;background:transparent;border:none;")
                lay.addWidget(info)

                if notes:
                    notes_lbl = QLabel(f"📝 ملاحظات:\n{notes}")
                    notes_lbl.setStyleSheet("font-size:13px;color:#e2e8f0;background:transparent;border:none;")
                    notes_lbl.setWordWrap(True)
                    lay.addWidget(notes_lbl)

                self._update_progress = QProgressBar()
                self._update_progress.setVisible(False)
                self._update_progress.setStyleSheet("""
                    QProgressBar{background:#1e293b;border:none;border-radius:6px;height:12px;text-align:center;font-size:10px;color:#f1f5f9;}
                    QProgressBar::chunk{background:#14b8a6;border-radius:6px;}
                """)
                lay.addWidget(self._update_progress)

                btn_row = QHBoxLayout()
                download_btn = QPushButton(f"⬇ تنزيل v{latest_ver}")
                download_btn.setStyleSheet("QPushButton{font-size:14px;font-weight:700;background:#0d9488;color:#fff;border:none;border-radius:8px;padding:10px 24px;}QPushButton:hover{background:#0f766e;}")
                btn_row.addWidget(download_btn)

                skip_btn = QPushButton("تخطي")
                skip_btn.setStyleSheet("QPushButton{font-size:14px;background:#334155;color:#94a3b8;border:none;border-radius:8px;padding:10px 24px;}QPushButton:hover{background:#475569;}")
                btn_row.addWidget(skip_btn)

                later_btn = QPushButton("لاحقاً")
                later_btn.setStyleSheet("QPushButton{font-size:14px;background:#1e293b;color:#64748b;border:1px solid #334155;border-radius:8px;padding:10px 24px;}QPushButton:hover{background:#334155;}")
                later_btn.clicked.connect(dialog.reject)
                btn_row.addWidget(later_btn)

                lay.addLayout(btn_row)

                def _do_download():
                    download_btn.setEnabled(False)
                    skip_btn.setEnabled(False)
                    self._update_progress.setVisible(True)
                    self._update_progress.setValue(0)

                    def on_progress(pct):
                        self._update_progress.setValue(int(pct * 100))

                    def _dl_thread():
                        try:
                            dl_path = download_update(dl_url, on_progress)
                            self._update_progress.setValue(100)
                            dialog.accept()
                            from utils.updater import apply_update
                            apply_update(dl_path)
                            QApplication.instance().quit()
                        except Exception as e:
                            from utils.toast import ToastNotification
                            ToastNotification.show_message(f"فشل التحميل: {str(e)}", 8000, self, "❌ تحديث")

                    import threading
                    threading.Thread(target=_dl_thread, daemon=True).start()

                download_btn.clicked.connect(_do_download)
                skip_btn.clicked.connect(dialog.reject)

                dialog.exec_()
            except Exception:
                pass

        threading.Thread(target=_do_check, daemon=True).start()

    def _auto_backup(self):
        try:
            db_dir = Path(__file__).resolve().parent.parent / "data"
            src = db_dir / "pharma.db"
            if not src.exists():
                return

            backup_dir = db_dir / "backups"
            backup_dir.mkdir(exist_ok=True)

            now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            dest = backup_dir / f"RTX_auto_{now}.bak"

            db = DatabaseManager()
            db.execute("PRAGMA wal_checkpoint(TRUNCATE)")

            shutil.copy2(str(src), str(dest))

            # Delete backups older than 20 days
            cutoff = datetime.datetime.now() - datetime.timedelta(days=20)
            for f in backup_dir.glob("RTX_auto_*.bak"):
                try:
                    mtime = datetime.datetime.fromtimestamp(f.stat().st_mtime)
                    if mtime < cutoff:
                        f.unlink()
                except Exception:
                    pass
        except Exception:
            pass  # Silently fail — backup shouldn't prevent shutdown

    def _logout(self):
        reply = QMessageBox.question(
            self, "تسجيل الخروج", "هل تريد تسجيل الخروج؟",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            from views.login_dialog import LoginDialog
            login = LoginDialog()
            if login.exec_() == LoginDialog.Accepted:
                # تحديث بيانات المستخدم وإعادة تهيئة النوافذ
                self.user_data = login.user_data
                self.is_admin = self.user_data.get("role") == "admin"
                self.setWindowTitle(f"RTX - {self.user_data['full_name']}")
                # إعادة تحميل الداشبورد
                self.dashboard.user_data = self.user_data
                self._switch_view("dashboard")
            else:
                self._auto_backup()
                QApplication.instance().quit()

