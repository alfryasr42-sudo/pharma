import os
import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QFormLayout, QMessageBox, QAbstractItemView,
    QGroupBox, QComboBox, QFrame, QGraphicsDropShadowEffect,
    QStackedWidget, QGridLayout, QCheckBox, QFileDialog
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont
from utils.modern_msgbox import ModernMessageBox as QMessageBox

from database.connection import DatabaseManager
from utils.auth import hash_password
from utils.decimal_handler import format_currency
from utils.printer_manager import PrinterManager
from utils.logger import safe_operation

_BG    = "#0f172a"
_CARD  = "#1e293b"
_BORD  = "#334155"
_PURPLE = "#7c3aed"
_PURPLE_LIGHT = "#a78bfa"
_TEXT  = "#f1f5f9"
_MUTED = "#94a3b8"
_GREEN = "#10b981"
_BLUE  = "#38bdf8"


class SettingsWidget(QWidget):
    users_changed = pyqtSignal()

    def __init__(self, user_data: dict, parent=None):
        super().__init__(parent)
        self.user_data = user_data
        self.db = DatabaseManager()
        self.printer_manager = PrinterManager()
        self._setup_ui()
        self._load_users()
        self._load_printers()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ──
        header = QFrame()
        header.setFixedHeight(64)
        header.setStyleSheet(f"""
            QFrame{{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
                     stop:0 {_PURPLE},stop:1 #5b21b6);
                     border-bottom:1px solid {_BORD}}}
        """)
        hdr_lay = QHBoxLayout(header)
        hdr_lay.setContentsMargins(24, 0, 24, 0)

        icon_lbl = QLabel("⚙️")
        icon_lbl.setStyleSheet("font-size:24px;background:transparent")

        title_lbl = QLabel("الإعدادات")
        title_lbl.setStyleSheet("font-size:20px;font-weight:700;color:#fff;background:transparent")

        hdr_lay.addWidget(icon_lbl)
        hdr_lay.addSpacing(8)
        hdr_lay.addWidget(title_lbl)
        hdr_lay.addStretch()
        root.addWidget(header)

        # ── Body: Sidebar + Stack ──
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        # Right sidebar
        sidebar = QFrame()
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet(f"QFrame{{background:#0c1220;border-right:1px solid {_BORD}}}")
        sb = QVBoxLayout(sidebar)
        sb.setContentsMargins(12, 16, 12, 16)
        sb.setSpacing(6)

        nav_style = (
            "QPushButton{font-size:15px;font-weight:600;padding:12px 14px;"
            "background:#1e293b;color:#94a3b8;border:none;border-radius:8px;"
            "text-align:right;min-height:20px}"
            "QPushButton:hover{background:#334155;color:#f1f5f9}"
            "QPushButton:checked{background:#7c3aed;color:#fff}"
        )

        self.nav_users = QPushButton("👥  المستخدمين")
        self.nav_printers = QPushButton("🖨️  الطابعات")
        self.nav_system = QPushButton("🖥️  النظام")

        for btn in [self.nav_users, self.nav_printers, self.nav_system]:
            btn.setStyleSheet(nav_style)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setCheckable(True)

        self.nav_users.clicked.connect(lambda: self._switch_page(0))
        self.nav_printers.clicked.connect(lambda: self._switch_page(1))
        self.nav_system.clicked.connect(lambda: self._switch_page(2))

        sb.addWidget(self.nav_users)
        sb.addWidget(self.nav_printers)
        sb.addSpacing(8)
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{_BORD}")
        sb.addWidget(sep)
        sb.addSpacing(8)
        sb.addWidget(self.nav_system)
        sb.addStretch()

        body.addWidget(sidebar)

        # Stacked content
        self.stack = QStackedWidget()

        self.users_page = QWidget()
        self._setup_users_tab()
        self.stack.addWidget(self.users_page)

        self.printers_page = QWidget()
        self._setup_printers_tab()
        self.stack.addWidget(self.printers_page)

        self.system_page = QWidget()
        self._setup_system_tab()
        self.stack.addWidget(self.system_page)

        body.addWidget(self.stack, 1)
        root.addLayout(body, 1)

        # Activate first
        self._switch_page(0)

    def _switch_page(self, idx):
        self.stack.setCurrentIndex(idx)
        for i, btn in enumerate([self.nav_users, self.nav_printers, self.nav_system]):
            btn.setChecked(i == idx)

    def _setup_users_tab(self):
        layout = QVBoxLayout(self.users_page)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        self.add_btn = QPushButton("➕ إضافة مستخدم")
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.setFixedHeight(42)
        self.add_btn.setStyleSheet(f"""
            QPushButton{{background:{_GREEN};color:#fff;font-weight:700;font-size:15px;
                       border:none;border-radius:8px;padding:0 24px}}
            QPushButton:hover{{background:#059669}}
        """)
        self.add_btn.clicked.connect(self._show_add_dialog)
        top_bar = QHBoxLayout()
        top_bar.addStretch()
        top_bar.addWidget(self.add_btn)
        layout.addLayout(top_bar)

        # Users table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "ID", "اسم المستخدم", "الاسم الكامل", "الدور", "الحالة", "الإجراءات"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.horizontalHeader().resizeSection(0, 50)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.table.horizontalHeader().resizeSection(3, 140)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
        self.table.horizontalHeader().resizeSection(4, 100)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Fixed)
        self.table.horizontalHeader().resizeSection(5, 280)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setStyleSheet(f"""
            QTableWidget{{background:{_CARD};border:1.5px solid {_BORD};
                         border-radius:12px;color:{_TEXT};gridline-color:transparent;outline:none;
                         alternate-background-color:#162033}}
            QHeaderView::section{{background:{_BG};color:{_PURPLE_LIGHT};padding:12px 10px;
                        border:none;border-bottom:2px solid {_BORD};font-size:14px;font-weight:700}}
            QTableWidget::item{{padding:6px 6px;border-bottom:1px solid rgba(255,255,255,0.04);font-size:14px}}
            QTableWidget::item:hover{{background:rgba(167,139,250,0.1)}}
            QTableWidget::item:selected{{background:rgba(124,58,237,0.2);color:{_PURPLE_LIGHT}}}
            QScrollBar:vertical{{background:{_BG};width:8px;border-radius:4px;margin:4px}}
            QScrollBar::handle:vertical{{background:{_BORD};border-radius:4px}}
        """)
        layout.addWidget(self.table, 1)

        # Info box
        info = QFrame()
        info.setStyleSheet(f"QFrame{{background:rgba(124,58,237,0.08);border:1px solid rgba(124,58,237,0.2);border-radius:8px;padding:12px}}")
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(14, 10, 14, 10)
        info_text = QLabel("💡 يمكن للمستخدمين الذين لديهم دور \"مدير النظام\" فقط الوصول إلى هذه الصفحة")
        info_text.setStyleSheet(f"font-size:13px;color:{_MUTED};background:transparent")
        info_layout.addWidget(info_text)
        layout.addWidget(info)

    def _setup_printers_tab(self):
        layout = QVBoxLayout(self.printers_page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        page_title = QLabel("🖨️  إعدادات الطابعات")
        page_title.setStyleSheet(f"font-size:18px;font-weight:700;color:{_BLUE};background:transparent")
        layout.addWidget(page_title)

        # Barcode Printer
        bc_group = QFrame()
        bc_group.setStyleSheet(f"QFrame{{background:{_CARD};border:1.5px solid {_BORD};border-radius:12px}}")
        bc_lay = QVBoxLayout(bc_group)
        bc_lay.setContentsMargins(20, 20, 20, 20)
        bc_lay.setSpacing(12)

        bc_title = QLabel("🏷️  طابعة الباركود (اللاصق)")
        bc_title.setStyleSheet(f"font-size:16px;font-weight:700;color:{_BLUE};background:transparent")
        bc_lay.addWidget(bc_title)

        bc_row = QHBoxLayout()
        bc_row.setSpacing(10)
        bc_label = QLabel("الطابعة الافتراضية:")
        bc_label.setStyleSheet(f"color:{_MUTED};font-size:14px;font-weight:600;background:transparent")
        self.bc_printer_combo = QComboBox()
        self.bc_printer_combo.setStyleSheet(f"QComboBox{{background:{_BG};color:{_TEXT};border:1.5px solid {_BORD};border-radius:8px;padding:8px 12px;font-size:14px;min-height:20px}} QComboBox:focus{{border-color:{_PURPLE}}} QComboBox::drop-down{{border:none;width:28px}}")
        self.bc_printer_combo.setMinimumWidth(280)

        bc_test_btn = QPushButton("🖨️ فحص")
        bc_test_btn.setCursor(Qt.PointingHandCursor)
        bc_test_btn.setFixedHeight(38)
        bc_test_btn.setStyleSheet(f"QPushButton{{background:{_PURPLE};color:#fff;font-weight:700;font-size:13px;border:none;border-radius:8px;padding:0 16px}} QPushButton:hover{{background:#6d28d9}}")
        bc_test_btn.clicked.connect(lambda: self._test_print(self.bc_printer_combo.currentText()))

        bc_row.addWidget(bc_label)
        bc_row.addWidget(self.bc_printer_combo, 1)
        bc_row.addWidget(bc_test_btn)
        bc_lay.addLayout(bc_row)
        layout.addWidget(bc_group)

        # Receipt Printer
        rc_group = QFrame()
        rc_group.setStyleSheet(f"QFrame{{background:{_CARD};border:1.5px solid {_BORD};border-radius:12px}}")
        rc_lay = QVBoxLayout(rc_group)
        rc_lay.setContentsMargins(20, 20, 20, 20)
        rc_lay.setSpacing(12)

        rc_title = QLabel("🧾  طابعة الفواتير (الريسيت)")
        rc_title.setStyleSheet(f"font-size:16px;font-weight:700;color:{_GREEN};background:transparent")
        rc_lay.addWidget(rc_title)

        rc_row = QHBoxLayout()
        rc_row.setSpacing(10)
        rc_label = QLabel("الطابعة الافتراضية:")
        rc_label.setStyleSheet(f"color:{_MUTED};font-size:14px;font-weight:600;background:transparent")
        self.rc_printer_combo = QComboBox()
        self.rc_printer_combo.setStyleSheet(self.bc_printer_combo.styleSheet())
        self.rc_printer_combo.setMinimumWidth(280)

        rc_test_btn = QPushButton("🖨️ فحص")
        rc_test_btn.setCursor(Qt.PointingHandCursor)
        rc_test_btn.setFixedHeight(38)
        rc_test_btn.setStyleSheet(f"QPushButton{{background:{_GREEN};color:#fff;font-weight:700;font-size:13px;border:none;border-radius:8px;padding:0 16px}} QPushButton:hover{{background:#059669}}")
        rc_test_btn.clicked.connect(lambda: self._test_print(self.rc_printer_combo.currentText()))

        rc_row.addWidget(rc_label)
        rc_row.addWidget(self.rc_printer_combo, 1)
        rc_row.addWidget(rc_test_btn)
        rc_lay.addLayout(rc_row)
        layout.addWidget(rc_group)

        # Save
        save_btn = QPushButton("💾 حفظ إعدادات الطابعات")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setFixedHeight(44)
        save_btn.setStyleSheet(f"QPushButton{{background:{_PURPLE};color:#fff;font-weight:700;font-size:15px;border:none;border-radius:8px;padding:0 32px}} QPushButton:hover{{background:#6d28d9}}")
        save_btn.clicked.connect(self._save_printers)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)
        layout.addStretch()

    def _load_printers(self):
        printers = self.printer_manager.get_available_printers()
        self.bc_printer_combo.addItems(printers)
        self.rc_printer_combo.addItems(printers)
        
        bc_def = self.printer_manager.get_default_barcode_printer()
        if bc_def in printers:
            self.bc_printer_combo.setCurrentText(bc_def)
            
        rc_def = self.printer_manager.get_default_receipt_printer()
        if rc_def in printers:
            self.rc_printer_combo.setCurrentText(rc_def)

    def _save_printers(self):
        bc = self.bc_printer_combo.currentText()
        rc = self.rc_printer_combo.currentText()
        self.printer_manager.save_printer_settings(bc, rc)
        QMessageBox.success(self, "نجاح", "تم حفظ إعدادات الطابعات بنجاح!")

    def _test_print(self, printer_name):
        success, msg = self.printer_manager.test_print(printer_name)
        if success:
            QMessageBox.success(self, "نجاح", msg)
        else:
            QMessageBox.critical(self, "خطأ", msg)

    def _load_users(self):
        users = self.db.fetchall(
            "SELECT id, username, full_name, role, is_active FROM users ORDER BY id"
        )
        self._populate_table(users)

    def _populate_table(self, users):
        self.table.setRowCount(len(users))
        for i, u in enumerate(users):
            item_id = QTableWidgetItem(str(u["id"]))
            item_id.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 0, item_id)

            name_item = QTableWidgetItem(u["username"])
            name_item.setTextAlignment(Qt.AlignCenter)
            f = name_item.font()
            f.setBold(True); f.setPointSize(14)
            name_item.setFont(f)
            self.table.setItem(i, 1, name_item)

            fn_item = QTableWidgetItem(u["full_name"])
            fn_item.setTextAlignment(Qt.AlignCenter)
            f2 = fn_item.font()
            f2.setPointSize(14)
            fn_item.setFont(f2)
            self.table.setItem(i, 2, fn_item)

            role_map = {"admin": "🛡️ مدير النظام", "manager": "⭐ مشرف", "cashier": "👤 كاشير"}
            role_item = QTableWidgetItem(role_map.get(u["role"], u["role"]))
            role_item.setTextAlignment(Qt.AlignCenter)
            role_item.setFont(f2)
            self.table.setItem(i, 3, role_item)

            status = "🟢 نشط" if u["is_active"] else "🔴 موقوف"
            st_item = QTableWidgetItem(status)
            st_item.setTextAlignment(Qt.AlignCenter)
            st_item.setFont(f2)
            self.table.setItem(i, 4, st_item)

            # Actions
            action_w = QWidget()
            al = QHBoxLayout(action_w)
            al.setContentsMargins(6, 4, 6, 4)
            al.setSpacing(6)

            edit_btn = QPushButton("✏️ تعديل")
            edit_btn.setCursor(Qt.PointingHandCursor)
            edit_btn.setFixedHeight(34)
            edit_btn.setMinimumWidth(80)
            edit_btn.setStyleSheet(f"""
                QPushButton{{font-size:13px;font-weight:700;background:#2563eb;color:#fff;
                           border:none;border-radius:6px;padding:0 10px}}
                QPushButton:hover{{background:#1d4ed8}}
            """)
            edit_btn.clicked.connect(lambda checked, uid=u["id"]: self._edit_user(uid))

            pw_btn = QPushButton("🔑 كلمة السر")
            pw_btn.setCursor(Qt.PointingHandCursor)
            pw_btn.setFixedHeight(34)
            pw_btn.setMinimumWidth(100)
            pw_btn.setStyleSheet(f"""
                QPushButton{{font-size:13px;font-weight:700;background:#0d9488;color:#fff;
                           border:2px solid #0d9488;border-radius:6px;padding:0 10px}}
                QPushButton:hover{{background:#0f766e;border-color:#0d9488}}
            """)
            pw_btn.clicked.connect(lambda checked, uid=u["id"]: self._change_password(uid))

            al.addWidget(edit_btn)
            al.addWidget(pw_btn)

            if u["username"] != "admin":
                if u["is_active"]:
                    tog_btn = QPushButton("🔴 تعطيل")
                    tog_style = f"""
                        QPushButton{{font-size:13px;font-weight:700;background:#dc2626;color:#fff;
                                   border:none;border-radius:6px;padding:0 10px}}
                        QPushButton:hover{{background:#b91c1c}}
                    """
                else:
                    tog_btn = QPushButton("🟢 تفعيل")
                    tog_style = f"""
                        QPushButton{{font-size:13px;font-weight:700;background:#16a34a;color:#fff;
                                   border:none;border-radius:6px;padding:0 10px}}
                        QPushButton:hover{{background:#15803d}}
                    """
                tog_btn.setCursor(Qt.PointingHandCursor)
                tog_btn.setFixedHeight(34)
                tog_btn.setMinimumWidth(70)
                tog_btn.setStyleSheet(tog_style)
                tog_btn.clicked.connect(lambda checked, uid=u["id"], act=u["is_active"]: self._toggle_user(uid, act))
                al.addWidget(tog_btn)

            al.addStretch()
            action_w.setLayout(al)
            self.table.setCellWidget(i, 5, action_w)
            self.table.setRowHeight(i, 52)

    def _show_add_dialog(self):
        dialog = UserDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self._load_users()
            self.users_changed.emit()

    def _edit_user(self, user_id):
        user = self.db.fetchone("SELECT * FROM users WHERE id = ?", (user_id,))
        if user:
            dialog = UserDialog(self, user)
            if dialog.exec_() == QDialog.Accepted:
                self._load_users()
                self.users_changed.emit()

    def _change_password(self, user_id):
        dialog = PasswordDialog(user_id, self)
        dialog.exec_()

    def _toggle_user(self, user_id, is_active):
        new_status = 0 if is_active else 1
        self.db.execute("UPDATE users SET is_active = ? WHERE id = ?", (new_status, user_id))
        self._load_users()
        self.users_changed.emit()

    def _setup_system_tab(self):
        layout = QVBoxLayout(self.system_page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        page_title = QLabel("🖥️  إعدادات النظام وصلاحيات الأدوار")
        page_title.setStyleSheet(f"font-size:18px;font-weight:700;color:{_PURPLE_LIGHT};background:transparent")
        layout.addWidget(page_title)

        # ── General Settings Card ──
        group = QFrame()
        group.setStyleSheet(f"QFrame{{background:{_CARD};border:1.5px solid {_BORD};border-radius:12px}}")
        g = QVBoxLayout(group)
        g.setContentsMargins(24, 20, 24, 20)
        g.setSpacing(16)

        ghdr = QLabel("🏥  تخصيص النظام")
        ghdr.setStyleSheet(f"font-size:17px;font-weight:700;color:{_BLUE};background:transparent")
        g.addWidget(ghdr)

        sep1 = QFrame()
        sep1.setFixedHeight(1)
        sep1.setStyleSheet(f"background:{_BORD}")
        g.addWidget(sep1)

        form = QGridLayout()
        form.setSpacing(12)

        lbl = QLabel("اسم الصيدلية:")
        lbl.setStyleSheet(f"font-size:15px;font-weight:600;color:{_MUTED};background:transparent")
        form.addWidget(lbl, 0, 1)

        self.pharmacy_name_inp = QLineEdit()
        self.pharmacy_name_inp.setStyleSheet(f"QLineEdit{{background:{_BG};color:{_TEXT};border:1.5px solid {_BORD};border-radius:8px;padding:10px 14px;font-size:16px;font-weight:700}} QLineEdit:focus{{border-color:{_PURPLE}}}")

        current_name = self.db.fetchone("SELECT setting_value FROM settings WHERE setting_key = 'pharmacy_name'")
        self.pharmacy_name_inp.setText(current_name["setting_value"] if current_name and current_name["setting_value"] else "صيدلية الأمل")
        form.addWidget(self.pharmacy_name_inp, 0, 0)

        self.show_deal_cost_cb = QCheckBox("إظهار تفاصيل الكلفة والربح مع ديل الأطباء في نقطة البيع")
        self.show_deal_cost_cb.setStyleSheet(f"""
            QCheckBox{{font-size:15px;font-weight:600;color:{_MUTED};background:transparent;spacing:10px}}
            QCheckBox::indicator{{width:24px;height:24px;border-radius:6px;border:1.5px solid {_BORD};background:{_BG}}}
            QCheckBox::indicator:checked{{background:{_PURPLE};border-color:{_PURPLE}}}
        """)
        cs = self.db.fetchone("SELECT setting_value FROM settings WHERE setting_key = 'show_doctor_deal_cost'")
        if cs and cs["setting_value"] == '1':
            self.show_deal_cost_cb.setChecked(True)
        form.addWidget(self.show_deal_cost_cb, 1, 0, 1, 2)

        g.addLayout(form)

        save_btn = QPushButton("💾 حفظ الإعدادات")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setFixedHeight(42)
        save_btn.setStyleSheet(f"QPushButton{{background:{_GREEN};color:#fff;font-weight:700;font-size:14px;border:none;border-radius:8px;padding:0 28px}} QPushButton:hover{{background:#059669}}")
        save_btn.clicked.connect(self._save_system_settings)
        br = QHBoxLayout()
        br.addStretch()
        br.addWidget(save_btn)
        g.addLayout(br)
        layout.addWidget(group)

        # ── Permissions Matrix Card ──
        perm_group = QFrame()
        perm_group.setStyleSheet(f"QFrame{{background:{_CARD};border:1.5px solid {_BORD};border-radius:12px}}")
        pm = QVBoxLayout(perm_group)
        pm.setContentsMargins(24, 20, 24, 20)
        pm.setSpacing(12)

        pm_hdr = QHBoxLayout()
        lock_icon = QLabel("🔐")
        lock_icon.setStyleSheet("font-size:18px;background:transparent")
        pm_title = QLabel("مصفوفة الصلاحيات حسب الدور")
        pm_title.setStyleSheet(f"font-size:17px;font-weight:700;color:{_PURPLE_LIGHT};background:transparent")
        pm_hdr.addWidget(lock_icon)
        pm_hdr.addSpacing(6)
        pm_hdr.addWidget(pm_title)
        pm_hdr.addStretch()
        pm.addLayout(pm_hdr)

        sep2 = QFrame()
        sep2.setFixedHeight(1)
        sep2.setStyleSheet(f"background:{_BORD}")
        pm.addWidget(sep2)

        self.perms_table = QTableWidget()
        self.perms_table.setColumnCount(4)
        self.perms_table.setHorizontalHeaderLabels(["الصلاحية", "🛡️ مدير النظام", "⭐ مشرف", "👤 كاشير"])
        self.perms_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 4):
            self.perms_table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.perms_table.verticalHeader().setVisible(False)
        self.perms_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.perms_table.setAlternatingRowColors(True)
        self.perms_table.setStyleSheet(f"""
            QTableWidget{{background:{_BG};border:1px solid {_BORD};border-radius:8px;
                         color:{_TEXT};gridline-color:transparent;outline:none;
                         alternate-background-color:#162033}}
            QHeaderView::section{{background:{_BG};color:{_PURPLE_LIGHT};padding:10px 8px;
                        border:none;border-bottom:2px solid {_BORD};font-size:13px;font-weight:700}}
            QTableWidget::item{{padding:8px 6px;border-bottom:1px solid rgba(255,255,255,0.04);font-size:14px}}
            QTableWidget::item:hover{{background:rgba(167,139,250,0.08)}}
        """)

        features = [
            ("👥 إدارة المستخدمين", True, False, False),
            ("📦 إدارة المخزون", True, True, False),
            ("💰 نقطة البيع", True, True, True),
            ("📋 إدارة الديون", True, True, False),
            ("👨‍⚕️ إدارة الأطباء", True, True, False),
            ("📊 التقارير", True, True, True),
            ("⚙️ الإعدادات", True, False, False),
            ("🖨️ إدارة الطابعات", True, True, False),
            ("📦 الطلبية (النقوصات)", True, True, True),
            ("🗑️ حذف الفواتير", True, False, False),
        ]

        self.perms_table.setRowCount(len(features))
        for r, (feat, admin, manager, cashier) in enumerate(features):
            fi = QTableWidgetItem(feat)
            fi.setFont(QFont("Segoe UI", 14, QFont.Bold))
            self.perms_table.setItem(r, 0, fi)
            for c, val in enumerate([admin, manager, cashier], 1):
                txt = "✔️" if val else "—"
                item = QTableWidgetItem(txt)
                item.setTextAlignment(Qt.AlignCenter)
                item.setForeground(QColor(_GREEN) if val else QColor(_BORD))
                self.perms_table.setItem(r, c, item)
            self.perms_table.setRowHeight(r, 40)

        pm.addWidget(self.perms_table, 1)

        info = QFrame()
        info.setStyleSheet(f"QFrame{{background:rgba(124,58,237,0.08);border:1px solid rgba(124,58,237,0.2);border-radius:8px;padding:10px}}")
        il = QHBoxLayout(info)
        il.setContentsMargins(12, 8, 12, 8)
        ilbl = QLabel("💡 صلاحيات ثابتة حسب الدور — يتم التحكم بها من قاعدة البيانات")
        ilbl.setStyleSheet(f"font-size:12px;color:{_MUTED};background:transparent")
        il.addWidget(ilbl)
        pm.addWidget(info)

        layout.addWidget(perm_group, 1)

        # ── Backup / Restore Card ──
        backup_group = QFrame()
        backup_group.setStyleSheet(f"QFrame{{background:{_CARD};border:1.5px solid {_BORD};border-radius:12px}}")
        bk = QVBoxLayout(backup_group)
        bk.setContentsMargins(24, 20, 24, 20)
        bk.setSpacing(12)

        bk_hdr = QHBoxLayout()
        bk_icon = QLabel("💾")
        bk_icon.setStyleSheet("font-size:18px;background:transparent")
        bk_title = QLabel("النسخ الاحتياطي للبيانات")
        bk_title.setStyleSheet(f"font-size:17px;font-weight:700;color:{_GREEN};background:transparent")
        bk_hdr.addWidget(bk_icon)
        bk_hdr.addSpacing(6)
        bk_hdr.addWidget(bk_title)
        bk_hdr.addStretch()
        bk.addLayout(bk_hdr)

        bk_sep = QFrame()
        bk_sep.setFixedHeight(1)
        bk_sep.setStyleSheet(f"background:{_BORD}")
        bk.addWidget(bk_sep)

        bk_desc = QLabel("إنشاء نسخة احتياطية من قاعدة البيانات (المواد، الفواتير، المستخدمين، إلخ)\n"
                         "واسترجاعها عند الحاجة. يوصى بعمل نسخة احتياطية أسبوعياً.")
        bk_desc.setStyleSheet(f"font-size:13px;color:{_MUTED};background:transparent;line-height:1.6;")
        bk_desc.setWordWrap(True)
        bk.addWidget(bk_desc)

        bk_btn_row = QHBoxLayout()
        bk_btn_row.setSpacing(12)

        self.btn_backup = QPushButton("💾 إنشاء نسخة احتياطية")
        self.btn_backup.setCursor(Qt.PointingHandCursor)
        self.btn_backup.setFixedHeight(42)
        self.btn_backup.setStyleSheet(f"""
            QPushButton{{background:{_GREEN};color:#fff;font-weight:700;font-size:14px;
                       border:none;border-radius:8px;padding:0 24px}}
            QPushButton:hover{{background:#059669}}
        """)
        self.btn_backup.clicked.connect(self._do_backup)
        bk_btn_row.addWidget(self.btn_backup)

        self.btn_restore = QPushButton("📂 استرجاع نسخة")
        self.btn_restore.setCursor(Qt.PointingHandCursor)
        self.btn_restore.setFixedHeight(42)
        self.btn_restore.setStyleSheet(f"""
            QPushButton{{background:{_PURPLE};color:#fff;font-weight:700;font-size:14px;
                       border:none;border-radius:8px;padding:0 24px}}
            QPushButton:hover{{background:#6d28d9}}
        """)
        self.btn_restore.clicked.connect(self._do_restore)
        bk_btn_row.addWidget(self.btn_restore)

        bk_btn_row.addStretch()
        bk.addLayout(bk_btn_row)

        # Info label
        self._bk_info = QLabel("")
        self._bk_info.setStyleSheet(f"font-size:12px;color:{_MUTED};background:transparent;")
        bk.addWidget(self._bk_info)

        layout.addWidget(backup_group)

        # Init backup info
        db_path = self._get_db_path()
        if os.path.exists(db_path):
            mtime = os.path.getmtime(db_path)
            last_mod = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
            size_kb = os.path.getsize(db_path) / 1024
            self._bk_info.setText(f"📁 قاعدة البيانات: {size_kb:.0f} KB  |  آخر تعديل: {last_mod}")
        else:
            self._bk_info.setText("⚠️ قاعدة البيانات غير موجودة")

    def _save_system_settings(self):
        new_name = self.pharmacy_name_inp.text().strip()
        show_deal = '1' if self.show_deal_cost_cb.isChecked() else '0'
        
        if new_name:
            self.db.execute(
                "INSERT INTO settings (setting_key, setting_value) VALUES ('pharmacy_name', ?) "
                "ON CONFLICT(setting_key) DO UPDATE SET setting_value = excluded.setting_value",
                (new_name,)
            )
            self.db.execute(
                "INSERT INTO settings (setting_key, setting_value) VALUES ('show_doctor_deal_cost', ?) "
                "ON CONFLICT(setting_key) DO UPDATE SET setting_value = excluded.setting_value",
                (show_deal,)
            )
            QMessageBox.information(self, "نجاح", "تم حفظ إعدادات النظام بنجاح!")
        else:
            QMessageBox.warning(self, "تنبيه", "يرجى كتابة اسم الصيدلية.")

    def _get_db_path(self):
        from pathlib import Path
        base = Path(__file__).resolve().parent.parent / "data"
        base.mkdir(parents=True, exist_ok=True)
        return str(base / "pharma.db")

    def _do_backup(self):
        import shutil
        src = self._get_db_path()
        if not os.path.exists(src):
            QMessageBox.warning(self, "خطأ", "قاعدة البيانات غير موجودة في المسار المتوقع.")
            return

        default_name = f"RTX_backup_{datetime.date.today().strftime('%Y%m%d_%H%M%S')}.bak"
        dest, _ = QFileDialog.getSaveFileName(
            self, "حفظ النسخة الاحتياطية", default_name,
            "ملفات النسخ الاحتياطي (*.bak);;جميع الملفات (*.*)"
        )
        if not dest:
            return

        try:
            # Checkpoint WAL to ensure all data is flushed to main db file
            self.db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            shutil.copy2(src, dest)
            size_mb = os.path.getsize(dest) / (1024 * 1024)
            self._bk_info.setText(f"✅ آخر نسخة: {os.path.basename(dest)} ({size_mb:.1f} MB)")
            QMessageBox.information(self, "✓ تم",
                f"تم إنشاء النسخة الاحتياطية بنجاح.\n"
                f"الموقع: {dest}\n"
                f"الحجم: {size_mb:.1f} MB")
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"فشل إنشاء النسخة الاحتياطية:\n{str(e)}")

    def _do_restore(self):
        import shutil
        src, _ = QFileDialog.getOpenFileName(
            self, "اختر ملف النسخة الاحتياطية", "",
            "ملفات النسخ الاحتياطي (*.bak);;جميع الملفات (*.*)"
        )
        if not src:
            return

        confirm = QMessageBox.question(self, "تأكيد الاسترجاع",
            "⚠️ تحذير: استرجاع النسخة الاحتياطية سيحل محل جميع البيانات الحالية!\n\n"
            "جميع الفواتير والمواد والمستخدمين والإعدادات الحالية ستُستبدل.\n"
            "لا يمكن التراجع عن هذا الإجراء.\n\n"
            "هل أنت متأكد من الاستمرار؟",
            QMessageBox.Yes | QMessageBox.No)
        if confirm != QMessageBox.Yes:
            return

        try:
            dest = self._get_db_path()
            # Close DB connection to release file lock
            self.db.close()
            shutil.copy2(src, dest)
            # Reconnect
            self.db = DatabaseManager()
            self._bk_info.setText(f"✅ تم استرجاع النسخة: {os.path.basename(src)}")
            QMessageBox.information(self, "✓ تم",
                "تم استرجاع النسخة الاحتياطية بنجاح.\n"
                "يرجى إعادة تشغيل البرنامج لتطبيق التغييرات بالكامل.")
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"فشل استرجاع النسخة:\n{str(e)}")
class UserDialog(QDialog):
    def __init__(self, parent=None, user=None):
        super().__init__(parent)
        self.user = user
        self.db = DatabaseManager()
        self.setWindowTitle("تعديل مستخدم" if user else "إضافة مستخدم جديد")
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.CustomizeWindowHint)
        self.setFixedSize(400, 350)
        self._setup_ui()
        if user:
            self._load_data(user)

    def _setup_ui(self):
        self.setStyleSheet("""
            UserDialog {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1a1a2e, stop:1 #24243e);
            }
            QLineEdit {
                background: rgba(255,255,255,0.1);
                border: 1px solid rgba(255,255,255,0.15);
                border-radius: 8px; padding: 10px; color: white; font-size: 14px;
            }
            QLineEdit:focus { border: 1px solid rgba(102,126,234,0.6); }
            QComboBox {
                background: rgba(255,255,255,0.1);
                border: 1px solid rgba(255,255,255,0.15);
                border-radius: 8px; padding: 10px; color: white; font-size: 14px;
            }
            QComboBox:focus { border: 1px solid rgba(102,126,234,0.6); }
            QComboBox::drop-down { border: none; width: 30px; }
            QComboBox QAbstractItemView {
                background: #1a1a2e; color: white; selection-background-color: rgba(102,126,234,0.6);
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(14)
        layout.setContentsMargins(28, 24, 28, 24)

        title = QLabel("معلومات المستخدم")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: white; padding-bottom: 8px;")
        layout.addWidget(title)

        form = QVBoxLayout()
        form.setSpacing(10)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("اسم المستخدم")
        form.addWidget(self.username_input)

        self.fullname_input = QLineEdit()
        self.fullname_input.setPlaceholderText("الاسم الكامل")
        form.addWidget(self.fullname_input)

        self.role_combo = QComboBox()
        self.role_combo.addItem("🛡️ مدير النظام", "admin")
        self.role_combo.addItem("⭐ مشرف", "manager")
        self.role_combo.addItem("👤 كاشير", "cashier")
        form.addWidget(self.role_combo)

        if not self.user:
            self.password_input = QLineEdit()
            self.password_input.setPlaceholderText("كلمة المرور")
            self.password_input.setEchoMode(QLineEdit.Password)
            form.addWidget(self.password_input)

            self.confirm_input = QLineEdit()
            self.confirm_input.setPlaceholderText("تأكيد كلمة المرور")
            self.confirm_input.setEchoMode(QLineEdit.Password)
            form.addWidget(self.confirm_input)

        layout.addLayout(form)
        layout.addStretch()

        buttons = QHBoxLayout()
        save_btn = QPushButton("💾 حفظ")
        save_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(67,233,123,0.8), stop:1 rgba(56,249,215,0.8));
                color: white; font-weight: bold; padding: 12px;
                border: none; border-radius: 10px; font-size: 14px;
            }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 rgba(67,233,123,1), stop:1 rgba(56,249,215,1)); }
        """)
        save_btn.clicked.connect(self._save)
        cancel_btn = QPushButton("إلغاء")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.1); color: rgba(255,255,255,150);
                padding: 12px; border: 1px solid rgba(255,255,255,0.15);
                border-radius: 10px; font-size: 14px;
            }
            QPushButton:hover { background: rgba(255,255,255,0.2); }
        """)
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)

        self.setLayout(layout)

    def _load_data(self, user):
        self.username_input.setText(user["username"])
        self.username_input.setEnabled(False)
        self.fullname_input.setText(user["full_name"])
        idx = self.role_combo.findData(user["role"])
        if idx >= 0:
            self.role_combo.setCurrentIndex(idx)

    @safe_operation("حدث خطأ أثناء حفظ بيانات المستخدم")
    def _save(self):
        username = self.username_input.text().strip()
        full_name = self.fullname_input.text().strip()

        if not username or not full_name:
            QMessageBox.warning(None, "خطأ", "يرجى ملء جميع الحقول")
            return

        if self.user:
            self.db.execute(
                "UPDATE users SET full_name = ?, role = ? WHERE id = ?",
                (full_name, self.role_combo.currentData(), self.user["id"]),
            )
        else:
            password = self.password_input.text()
            confirm = self.confirm_input.text()
            if not password or len(password) < 4:
                QMessageBox.warning(None, "خطأ", "كلمة المرور يجب أن تكون 4 أحرف على الأقل")
                return
            if password != confirm:
                QMessageBox.warning(None, "خطأ", "كلمة المرور غير متطابقة")
                return
            exists = self.db.fetchone("SELECT id FROM users WHERE username = ?", (username,))
            if exists:
                QMessageBox.warning(None, "خطأ", "اسم المستخدم موجود مسبقاً")
                return
            self.db.execute(
                "INSERT INTO users (username, password_hash, full_name, role) VALUES (?, ?, ?, ?)",
                (username, hash_password(password), full_name, self.role_combo.currentData()),
            )
        self.accept()


class PasswordDialog(QDialog):
    def __init__(self, user_id, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.db = DatabaseManager()
        self.setWindowTitle("تغيير كلمة المرور")
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.CustomizeWindowHint)
        self.setFixedSize(420, 340)
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet("""
            PasswordDialog {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1a1a2e, stop:1 #24243e);
            }
            QLineEdit {
                background: rgba(255,255,255,0.1);
                border: 1px solid rgba(255,255,255,0.15);
                border-radius: 8px; padding: 12px; color: white; font-size: 15px;
            }
            QLineEdit:focus { border: 1px solid rgba(102,126,234,0.6); }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(16)
        layout.setContentsMargins(32, 28, 32, 28)

        title = QLabel("🔑 تغيير كلمة المرور")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: white; padding-bottom: 6px;background:transparent")
        layout.addWidget(title)

        pw_lbl = QLabel("كلمة المرور الجديدة:")
        pw_lbl.setStyleSheet("color: rgba(255,255,255,180); font-size: 14px;background:transparent")
        layout.addWidget(pw_lbl)

        self.new_pass = QLineEdit()
        self.new_pass.setPlaceholderText("أدخل كلمة المرور الجديدة")
        self.new_pass.setEchoMode(QLineEdit.Password)
        self.new_pass.setFixedHeight(44)
        layout.addWidget(self.new_pass)

        confirm_lbl = QLabel("تأكيد كلمة المرور:")
        confirm_lbl.setStyleSheet("color: rgba(255,255,255,180); font-size: 14px;background:transparent")
        layout.addWidget(confirm_lbl)

        self.confirm_pass = QLineEdit()
        self.confirm_pass.setPlaceholderText("أعد إدخال كلمة المرور")
        self.confirm_pass.setEchoMode(QLineEdit.Password)
        self.confirm_pass.setFixedHeight(44)
        layout.addWidget(self.confirm_pass)

        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        save_btn = QPushButton("💾 حفظ")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setFixedHeight(44)
        save_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(67,233,123,0.9), stop:1 rgba(56,249,215,0.9));
                color: white; font-weight: bold; padding: 0 24px;
                border: none; border-radius: 10px; font-size: 15px;
            }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 rgba(67,233,123,1), stop:1 rgba(56,249,215,1)); }
        """)
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)

        cancel_btn = QPushButton("✕ إلغاء")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setFixedHeight(44)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.12); color: rgba(255,255,255,180);
                padding: 0 24px; border: 1px solid rgba(255,255,255,0.2);
                border-radius: 10px; font-size: 15px;
            }
            QPushButton:hover { background: rgba(255,255,255,0.25); }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        layout.addLayout(btn_row)

        self.setLayout(layout)

    @safe_operation("حدث خطأ أثناء تغيير كلمة المرور")
    def _save(self):
        new = self.new_pass.text()
        confirm = self.confirm_pass.text()
        if not new or len(new) < 4:
            QMessageBox.warning(None, "خطأ", "كلمة المرور يجب أن تكون 4 أحرف على الأقل")
            return
        if new != confirm:
            QMessageBox.warning(None, "خطأ", "كلمة المرور غير متطابقة")
            return
        self.db.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (hash_password(new), self.user_id),
        )
        QMessageBox.information(None, "تم", "تم تغيير كلمة المرور بنجاح")
        self.accept()
