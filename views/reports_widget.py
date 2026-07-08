import sys
import os
import calendar
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QDateEdit, QDialog, QFrame, QGraphicsDropShadowEffect,
    QStackedWidget, QLineEdit, QDoubleSpinBox, QFormLayout, QFileDialog,
    QMessageBox, QSplitter, QGridLayout, QComboBox, QProgressBar, QCheckBox, QInputDialog
)
from PyQt5.QtCore import Qt, QDate, QLocale, QPointF, QRectF, QBuffer, QByteArray, QIODevice
from PyQt5.QtGui import QColor, QBrush, QFont, QPainter, QLinearGradient, QPen, QPainterPath, QImage
from PyQt5.QtPrintSupport import QPrintDialog, QPrintPreviewDialog, QPrinter
from PyQt5.QtGui import QTextDocument
import base64
import math

from database.connection import DatabaseManager
from controllers.supplier_debt_controller import SupplierDebtController
from utils.decimal_handler import format_currency, to_decimal, from_decimal, DECIMAL_ZERO
from utils.modern_msgbox import ModernMessageBox as QMessageBox

# ── style constants ──
_BG    = "#0f172a"
_CARD  = "#1e293b"
_BORD  = "#334155"
_GREEN = "#34d399"  # Brighter emerald green
_BLUE  = "#38bdf8"  # Sky blue
_RED   = "#f87171"  # Coral red
_TEAL = "#14b8a6"
_TEXT  = "#f1f5f9"
_MUTED = "#94a3b8"

def _lbl(text, color=_TEXT, size=15, bold=False):
    l = QLabel(text)
    l.setStyleSheet(
        f"font-size:{size}px;font-weight:{'700' if bold else '500'};"
        f"color:{color};background:transparent;border:none;"
    )
    l.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    return l

def _btn(text, bg=_GREEN, color="white", fs=14, h=42):
    b = QPushButton(text)
    b.setFixedHeight(h)
    b.setCursor(Qt.PointingHandCursor)
    b.setStyleSheet(
        f"QPushButton {{"
        f"  background: {bg}; color: {color}; font-weight: 700; font-size: {fs}px;"
        f"  border: none; border-radius: 8px; padding: 0px 16px; text-align: center;"
        f"}}"
        f"QPushButton:hover {{"
        f"  background: {bg}dd;"
        f"}}"
        f"QPushButton:pressed {{"
        f"  background: {bg}aa;"
        f"}}"
    )
    return b

class InvoiceItemsDialog(QDialog):
    def __init__(self, invoice_number, sale_id, parent=None):
        super().__init__(parent)
        self.db = DatabaseManager()
        self.setWindowTitle(f"تفاصيل الفاتورة #{invoice_number}")
        self.setMinimumSize(600, 450)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._setup_ui(sale_id)

    def _setup_ui(self, sale_id):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel(f"📦 محتويات الفاتورة")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #38bdf8;")
        layout.addWidget(title)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["اسم المادة", "الكمية", "سعر الوحدة", "الإجمالي"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 4):
            self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.table)

        # Load items
        items = self.db.fetchall(
            """SELECT si.*, p.name as product_name
               FROM sale_items si
               JOIN products p ON si.product_id = p.id
               WHERE si.sale_id = ?""",
            (sale_id,),
        )
        self.table.setRowCount(0)
        for row_data in items:
            r = self.table.rowCount()
            self.table.insertRow(r)
            
            name_item = QTableWidgetItem(row_data["product_name"] or "")
            name_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(r, 0, name_item)
            
            qty_item = QTableWidgetItem(str(row_data["quantity"] or 0))
            qty_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r, 1, qty_item)
            
            price_item = QTableWidgetItem(format_currency(row_data["unit_price"]))
            price_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r, 2, price_item)
            
            total_item = QTableWidgetItem(format_currency(row_data["total_price"]))
            total_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r, 3, total_item)

        close_btn = QPushButton("إغلاق")
        close_btn.setStyleSheet("""
            QPushButton {
                background: #334155; color: white; font-weight: bold;
                padding: 10px 20px; border: none; border-radius: 6px; font-size: 14px;
            }
            QPushButton:hover { background: #475569; }
        """)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, 0, Qt.AlignLeft)

        self.setStyleSheet("""
            QDialog { background-color: #0f172a; }
            QLabel { color: #ffffff; }
            QTableWidget {
                background-color: #1e293b;
                border: 1.5px solid #334155;
                border-radius: 10px;
                gridline-color: #334155;
            }
            QTableWidget::item {
                color: #f1f5f9; font-size: 15px; padding: 8px; border-bottom: 1px solid #334155;
            }
            QHeaderView::section {
                background-color: #0f172a; color: #38bdf8; padding: 10px; border: none;
                border-bottom: 2px solid #334155; font-weight: bold; font-size: 15px;
            }
        """)


class PurchaseItemsDialog(QDialog):
    def __init__(self, invoice_number, purchase_id, parent=None):
        super().__init__(parent)
        self.db = DatabaseManager()
        self.setWindowTitle(f"تفاصيل فاتورة الشراء #{invoice_number}")
        self.setMinimumSize(600, 450)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._setup_ui(purchase_id)

    def _setup_ui(self, purchase_id):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel(f"📦 محتويات فاتورة الشراء")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #38bdf8;")
        layout.addWidget(title)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["اسم المادة", "الكمية", "سعر الكلفة", "الإجمالي"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 4):
            self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.table)

        items = self.db.fetchall(
            """SELECT * FROM supplier_debt_items WHERE supplier_debt_id = ?""",
            (purchase_id,),
        )
        self.table.setRowCount(0)
        for row_data in items:
            r = self.table.rowCount()
            self.table.insertRow(r)
            
            name_item = QTableWidgetItem(row_data["name"] or "")
            name_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(r, 0, name_item)
            
            qty_item = QTableWidgetItem(str(row_data["quantity"] or 0))
            qty_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r, 1, qty_item)
            
            price_item = QTableWidgetItem(format_currency(str(row_data["unit_price"] or 0)))
            price_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r, 2, price_item)
            
            total_item = QTableWidgetItem(format_currency(str(row_data["total_price"] or 0)))
            total_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r, 3, total_item)

        close_btn = QPushButton("إغلاق")
        close_btn.setStyleSheet("""
            QPushButton {
                background: #334155; color: white; font-weight: bold;
                padding: 10px 20px; border: none; border-radius: 6px; font-size: 14px;
            }
            QPushButton:hover { background: #475569; }
        """)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, 0, Qt.AlignLeft)

        self.setStyleSheet("""
            QDialog { background-color: #0f172a; }
            QLabel { color: #ffffff; }
            QTableWidget {
                background-color: #1e293b;
                border: 1.5px solid #334155;
                border-radius: 10px;
                gridline-color: #334155;
            }
            QTableWidget::item {
                color: #f1f5f9; font-size: 15px; padding: 8px; border-bottom: 1px solid #334155;
            }
            QHeaderView::section {
                background-color: #0f172a; color: #38bdf8; padding: 10px; border: none;
                border-bottom: 2px solid #334155; font-weight: bold; font-size: 15px;
            }
        """)


class AddExpenseDialog(QDialog):
    _DBG = "#0b1120"
    _CARD = "#141d2e"
    _BORD = "#2a3f5f"
    _FOCUS = "#4a8fe7"
    _NUM = "#7ba3ff"
    _TEXT = "#f1f5f9"
    _MUTED = "#94a3b8"
    _GREEN = "#34d399"
    _RED = "#f87171"
    _TEAL = "#14b8a6"

    def __init__(self, user_data=None, parent=None):
        super().__init__(parent)
        self.db = DatabaseManager()
        self.supplier_debt_ctrl = SupplierDebtController()
        self.user_data = user_data or {}
        self._income_rows = []
        self.setWindowTitle("تسجيل مصروف جديد")
        self.setMinimumSize(920, 750)
        self.setWindowFlags(Qt.Dialog)
        self._setup_ui()
        self._load_income_sources()

    def _lbl(self, text, color=None, size=14, bold=False):
        l = QLabel(text)
        l.setStyleSheet(
            f"font-size:{size}px;font-weight:{'700' if bold else '500'};"
            f"color:{color or self._TEXT};background:transparent;border:none;"
        )
        l.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        return l

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.setStyleSheet(f"""
            QDialog {{ background-color: {self._DBG}; }}
            QLabel {{ color: {self._TEXT}; background: transparent; }}
            QComboBox, QDoubleSpinBox {{
                background: {self._CARD}; color: {self._TEXT};
                border: none; border-bottom: 2px solid {self._BORD};
                border-radius: 0; padding: 10px 12px 6px 12px;
                font-size: 18px; min-height: 32px;
            }}
            QComboBox:focus, QDoubleSpinBox:focus {{
                border-bottom: 2px solid {self._FOCUS};
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding; subcontrol-position: left;
                width: 30px; border: none;
            }}
            QComboBox::down-arrow {{
                image: none; width: 0; height: 0;
                border-left: 6px solid transparent; border-right: 6px solid transparent;
                border-top: 8px solid {self._MUTED};
            }}
            QComboBox QAbstractItemView {{
                background: {self._CARD}; color: {self._TEXT};
                selection-background-color: {self._FOCUS};
                border: 1px solid {self._BORD}; border-radius: 6px;
                font-size: 16px; padding: 4px;
            }}
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
                subcontrol-origin: padding; width: 28px; border: none;
            }}
            QDoubleSpinBox::up-arrow {{
                image: none; width: 0; height: 0;
                border-left: 6px solid transparent; border-right: 6px solid transparent;
                border-bottom: 9px solid {self._NUM};
            }}
            QDoubleSpinBox::down-arrow {{
                image: none; width: 0; height: 0;
                border-left: 6px solid transparent; border-right: 6px solid transparent;
                border-top: 9px solid {self._RED};
            }}
            QTableWidget {{
                background: {self._CARD}; color: {self._TEXT};
                border: 1px solid {self._BORD}; border-radius: 8px;
                gridline-color: #1e3a5f; font-size: 13px;
            }}
            QTableWidget::item {{
                padding: 6px 8px; border-bottom: 1px solid #1e3a5f;
                border-right: 1px solid #1a2a4a;
            }}
            QTableWidget::item:selected {{
                background: rgba(74, 143, 231, 0.25); color: {self._FOCUS};
            }}
            QHeaderView::section {{
                background: {self._DBG}; color: {self._FOCUS};
                font-weight: 700; font-size: 12px; border: none;
                border-bottom: 2px solid {self._BORD}; padding: 6px 2px;
            }}
        """)

        content = QVBoxLayout()
        content.setContentsMargins(28, 22, 28, 12)
        content.setSpacing(14)

        hdr = QHBoxLayout()
        hdr.addWidget(self._lbl("💸 تسجيل مصروف جديد", self._GREEN, 22, True))
        hdr.addStretch()
        content.addLayout(hdr)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{self._BORD}")
        content.addWidget(sep)

        # Expense type + Amount row
        type_row = QHBoxLayout()
        type_row.setSpacing(10)
        tv = QVBoxLayout()
        tv.setSpacing(4)
        tv.addWidget(self._lbl("🏷 نوع المصروف", self._MUTED, 13))
        self.type_combo = QComboBox()
        self.type_combo.setEditable(True)
        self.type_combo.setInsertPolicy(QComboBox.NoInsert)
        self.type_combo.lineEdit().setPlaceholderText("اكتب اسم المصروف أو اختر من القائمة...")
        self.type_combo.setMinimumHeight(44)
        for row in self.db.fetchall("SELECT name FROM expense_types ORDER BY name"):
            self.type_combo.addItem(row["name"])
        tv.addWidget(self.type_combo)
        self.type_combo.insertItem(0, "🔹 تسديد مذخر")
        self.type_combo.setCurrentIndex(-1)
        self.type_combo.currentTextChanged.connect(self._on_expense_type_changed)
        type_row.addLayout(tv, 3)

        av = QVBoxLayout()
        av.setSpacing(4)
        av.addWidget(self._lbl("💰 المبلغ", self._MUTED, 13))
        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(0, 999999999)
        self.amount_spin.setDecimals(0)
        self.amount_spin.setSingleStep(1000)
        self.amount_spin.setSuffix(" د.ع")
        self.amount_spin.setAlignment(Qt.AlignRight)
        self.amount_spin.setLocale(QLocale(QLocale.English, QLocale.UnitedStates))
        self.amount_spin.setGroupSeparatorShown(True)
        self.amount_spin.setMinimumHeight(44)
        self.amount_spin.valueChanged.connect(self._auto_distribute)
        av.addWidget(self.amount_spin)
        type_row.addLayout(av, 1)
        content.addLayout(type_row)

        # Supplier section (hidden unless "تسديد مذخر" is selected)
        self.supplier_section = QFrame()
        self.supplier_section.setStyleSheet(f"background:{self._CARD};border:1px solid {self._BORD};border-radius:8px;")
        sl = QVBoxLayout(self.supplier_section)
        sl.setContentsMargins(12, 10, 12, 10)
        sl.setSpacing(8)
        sr = QHBoxLayout()
        sr.addWidget(self._lbl("🏪 اختر المذخر:", self._MUTED, 13))
        self.supplier_combo = QComboBox()
        self.supplier_combo.setMinimumWidth(300)
        self.supplier_combo.setMinimumHeight(40)
        self.supplier_combo.setStyleSheet(f"""
            QComboBox{{background:{self._DBG};color:{self._TEXT};border:none;
                       border-bottom:2px solid {self._BORD};border-radius:0;
                       padding:8px 12px;font-size:16px;min-height:24px;}}
            QComboBox:focus{{border-bottom:2px solid {self._FOCUS};}}
            QComboBox::drop-down{{subcontrol-origin:padding;subcontrol-position:left;width:30px;border:none;}}
            QComboBox::down-arrow{{image:none;width:0;height:0;border-left:6px solid transparent;
                                   border-right:6px solid transparent;border-top:8px solid {self._MUTED};}}
            QComboBox QAbstractItemView{{background:{self._CARD};color:{self._TEXT};
                selection-background-color:{self._FOCUS};border:1px solid {self._BORD};border-radius:6px;
                font-size:15px;padding:4px;}}
        """)
        sr.addWidget(self.supplier_combo)
        sr.addStretch()
        sl.addLayout(sr)
        # Sub-label showing auto-distribute info
        self._supplier_info = QLabel("سيتم توزيع المبلغ تلقائياً على فواتير المذخر (الأحدث فالأقدم)")
        self._supplier_info.setStyleSheet(f"font-size:12px;color:{self._MUTED};background:transparent;border:none;")
        sl.addWidget(self._supplier_info)
        self.supplier_section.setVisible(False)
        content.addWidget(self.supplier_section)

        # Auto info line
        info = QLabel(f"👤 {self.user_data.get('full_name', 'غير معروف')}  |  📅 {QDate.currentDate().toPyDate().strftime('%Y-%m-%d')}")
        info.setStyleSheet(f"""
            background:{self._CARD}; color:{self._MUTED};
            border:none; border-bottom:2px solid {self._BORD};
            font-size:15px; padding:8px 12px; min-height:28px;
        """)
        info.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        content.addWidget(info)

        # Income table
        content.addWidget(self._lbl("🏦 اختر مصدر الدخل (الاستقطاع من الأحدث للأقدم)", self._MUTED, 13))
        self.income_table = QTableWidget()
        self.income_table.setColumnCount(6)
        self.income_table.setHorizontalHeaderLabels(["", "التاريخ", "اجمالي الدخل", "مصروفات سابقة", "المتبقي", "المسحوب"])
        self.income_table.setColumnWidth(0, 32)
        self.income_table.setColumnWidth(1, 110)
        self.income_table.setColumnWidth(2, 120)
        self.income_table.setColumnWidth(3, 120)
        self.income_table.setColumnWidth(4, 120)
        self.income_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self.income_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.income_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.income_table.verticalHeader().setVisible(False)
        self.income_table.setMinimumHeight(190)
        content.addWidget(self.income_table)

        # Global progress bar (full width, red → yellow → green)
        self._global_bar = QProgressBar()
        self._global_bar.setRange(0, 100)
        self._global_bar.setValue(0)
        self._global_bar.setFixedHeight(28)
        self._global_bar.setTextVisible(True)
        self._global_bar.setFormat("0%")
        content.addWidget(self._global_bar)

        # Summary
        self._summary = QLabel("")
        self._summary.setStyleSheet(f"font-size:14px;color:{self._GREEN};background:transparent;border:none;padding:4px 0;")
        self._summary.setVisible(False)
        content.addWidget(self._summary)

        # Warning
        self._warn = QLabel("")
        self._warn.setStyleSheet(f"font-size:13px;color:{self._RED};background:transparent;border:none;")
        self._warn.setVisible(False)
        content.addWidget(self._warn)

        root.addLayout(content)
        root.addStretch()

        # Footer
        footer = QFrame()
        footer.setStyleSheet(f"QFrame{{background:{self._DBG};border-top:1px solid {self._BORD}}}")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(24, 12, 24, 12)

        self.btn_cancel = self._mkbtn("إلغاء", self._CARD, self._MUTED)
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_save = self._mkbtn("💾 حفظ المصروف", self._FOCUS, "#ffffff")
        self.btn_save.clicked.connect(self._save_expense)

        fl.addStretch()
        fl.addWidget(self.btn_cancel)
        fl.addWidget(self.btn_save)
        footer.setLayout(fl)
        root.addWidget(footer)

    def _mkbtn(self, text, bg, fg):
        b = QPushButton(text)
        b.setFixedHeight(44)
        b.setCursor(Qt.PointingHandCursor)
        b.setStyleSheet(
            f"QPushButton{{background:{bg};color:{fg};font-weight:700;font-size:15px;"
            f"border:none;border-radius:8px;padding:0 28px;min-width:90px;}}"
            f"QPushButton:hover{{background:{bg};color:{fg};}}"
            f"QPushButton:pressed{{background:{bg};color:{fg};}}"
        )
        return b

    def _on_expense_type_changed(self, text):
        is_supplier = text.strip() == "🔹 تسديد مذخر"
        self.supplier_section.setVisible(is_supplier)
        if is_supplier and self.supplier_combo.count() == 0:
            self._load_suppliers()

    def _load_suppliers(self):
        self.supplier_combo.clear()
        self.supplier_combo.addItem("-- اختر المذخر --", None)
        for r in self.supplier_debt_ctrl.get_suppliers_with_debt_totals():
            label = f"{r['name']}  💳  {r['total_remaining']:,.0f} د.ع"
            idx = self.supplier_combo.count()
            self.supplier_combo.addItem(label, r["id"])
            self.supplier_combo.setItemData(idx, r["name"], Qt.UserRole + 1)
        self.supplier_combo.setCurrentIndex(-1)

    def _load_income_sources(self):
        self.income_table.setRowCount(0)
        self._income_rows = []

        today = QDate.currentDate()
        month_start = QDate(today.year(), today.month(), 1).toPyDate().strftime("%Y-%m-%d")
        month_end = today.toPyDate().strftime("%Y-%m-%d")

        rows = self.db.fetchall("""
            SELECT date(created_at, 'localtime') as d,
                   SUM(CAST(total_amount AS REAL)) as total_income
            FROM sales
            WHERE date(created_at, 'localtime') BETWEEN ? AND ?
            GROUP BY date(created_at, 'localtime')
            ORDER BY d DESC
        """, (month_start, month_end))

        payment_rows = self.db.fetchall("""
            SELECT date(payment_date, 'localtime') as d,
                   SUM(CAST(amount AS REAL)) as total_payments
            FROM debt_payments
            WHERE date(payment_date, 'localtime') BETWEEN ? AND ?
            GROUP BY date(payment_date, 'localtime')
            ORDER BY d DESC
        """, (month_start, month_end))
        payment_map = {}
        for pr in payment_rows:
            payment_map[pr["d"]] = float(pr["total_payments"] or 0)

        alloc_rows = self.db.fetchall("""
            SELECT eis.income_date, SUM(CAST(eis.amount AS REAL)) as total_alloc
            FROM expense_income_sources eis
            JOIN expenses e ON eis.expense_id = e.id
            WHERE eis.income_date BETWEEN ? AND ?
            GROUP BY eis.income_date
        """, (month_start, month_end))
        alloc_map = {}
        for ar in alloc_rows:
            alloc_map[ar["income_date"]] = float(ar["total_alloc"] or 0)

        for r in rows:
            d = r["d"]
            income = float(r["total_income"] or 0) + payment_map.get(d, 0)
            allocated = alloc_map.get(d, 0)
            remaining = income - allocated
            self._income_rows.append({
                "date": d, "income": income,
                "allocated": allocated, "remaining": remaining,
                "to_take": 0, "checked": False,
            })

        if not self._income_rows:
            self.income_table.insertRow(0)
            self.income_table.setItem(0, 1, QTableWidgetItem("لا توجد مبيعات في هذا الشهر"))
            self._warn.setText("⚠️ لا يوجد دخل متاح في الشهر الحالي")
            self._warn.setVisible(True)
            return

        current = QDate(today.year(), today.month(), 1)
        date_set = {ir["date"] for ir in self._income_rows}
        while current <= today:
            ds = current.toPyDate().strftime("%Y-%m-%d")
            if ds not in date_set:
                self._income_rows.append({
                    "date": ds, "income": 0,
                    "allocated": alloc_map.get(ds, 0),
                    "remaining": -alloc_map.get(ds, 0),
                    "to_take": 0, "checked": False,
                })
            current = current.addDays(1)
        self._income_rows.sort(key=lambda x: x["date"], reverse=True)

        for ir in self._income_rows:
            row = self.income_table.rowCount()
            self.income_table.insertRow(row)

            cb = QCheckBox()
            cb.stateChanged.connect(lambda st, r=row: self._on_check_changed(r))
            cw = QWidget()
            cl = QHBoxLayout(cw)
            cl.setContentsMargins(0, 0, 0, 0)
            cl.addWidget(cb, 0, Qt.AlignCenter)
            self.income_table.setCellWidget(row, 0, cw)

            date_item = QTableWidgetItem(ir["date"])
            date_item.setTextAlignment(Qt.AlignCenter)
            self.income_table.setItem(row, 1, date_item)

            inc_item = QTableWidgetItem(format_currency(ir["income"]))
            inc_item.setTextAlignment(Qt.AlignCenter)
            inc_item.setForeground(QColor(self._NUM))
            self.income_table.setItem(row, 2, inc_item)

            alloc_item = QTableWidgetItem(format_currency(ir["allocated"]))
            alloc_item.setTextAlignment(Qt.AlignCenter)
            alloc_item.setForeground(QColor(self._TEAL))
            self.income_table.setItem(row, 3, alloc_item)

            rem_item = QTableWidgetItem(format_currency(ir["remaining"]))
            rem_item.setTextAlignment(Qt.AlignCenter)
            rem_item.setForeground(QColor(self._GREEN if ir["remaining"] > 0 else self._RED))
            self.income_table.setItem(row, 4, rem_item)

            take_item = QTableWidgetItem("—")
            take_item.setTextAlignment(Qt.AlignCenter)
            take_item.setForeground(QColor(self._FOCUS))
            self.income_table.setItem(row, 5, take_item)

        self._auto_distribute()

    def _on_check_changed(self, row):
        try:
            if row >= len(self._income_rows):
                return
            cw = self.income_table.cellWidget(row, 0)
            cb = cw.findChild(QCheckBox) if cw else None
            if not cb or not cb.isChecked():
                self._auto_distribute()
                return

            widgets = []
            for i in range(len(self._income_rows)):
                w = self.income_table.cellWidget(i, 0)
                c = w.findChild(QCheckBox) if w else None
                if c:
                    c.blockSignals(True)
                    widgets.append(c)

            for i, ir in enumerate(self._income_rows):
                ir["checked"] = (i == row)

            if row < len(widgets):
                widgets[row].setChecked(True)
            for i in range(len(self._income_rows)):
                if i != row and i < len(widgets):
                    widgets[i].setChecked(False)

            need = self.amount_spin.value()
            for i in range(row, len(self._income_rows)):
                ir = self._income_rows[i]
                if i != row:
                    ir["checked"] = True
                    if i < len(widgets):
                        widgets[i].setChecked(True)
                avail = max(ir["remaining"], 0)
                need -= avail
                if need <= 0:
                    for j in range(i + 1, len(self._income_rows)):
                        self._income_rows[j]["checked"] = False
                        if j < len(widgets):
                            widgets[j].setChecked(False)
                    break

            for c in widgets:
                c.blockSignals(False)

            self._auto_distribute()
        except Exception as e:
            import traceback
            QMessageBox.critical(self, "خطأ", f"حدث خطأ في اختيار الدخل:\n{str(e)}\n\n{traceback.format_exc()}")

    def _auto_distribute(self):
        try:
            amount = self.amount_spin.value()
            need = amount
            total_available = 0

            for ir in self._income_rows:
                ir["to_take"] = 0

            if amount <= 0 or not self._income_rows:
                self._update_display(need, 0)
                return

            checked_rows = [(i, ir) for i, ir in enumerate(self._income_rows) if ir["checked"]]
            if not checked_rows:
                self._update_display(amount, 0)
                return

            total_available = sum(ir["remaining"] for _, ir in checked_rows if ir["remaining"] > 0)

            checked_rows.sort(key=lambda x: x[1]["date"], reverse=True)
            for idx, ir in checked_rows:
                if need <= 0:
                    break
                avail = max(ir["remaining"], 0)
                if avail <= 0:
                    continue
                take = min(avail, need)
                ir["to_take"] = take
                need -= take

            self._update_display(need, total_available)
        except Exception as e:
            import traceback
            QMessageBox.critical(self, "خطأ", f"خطأ في التوزيع:\n{str(e)}\n\n{traceback.format_exc()}")

    def _update_display(self, remaining_need, total_available):
        amount = self.amount_spin.value()

        for i, ir in enumerate(self._income_rows):
            take_text = format_currency(ir["to_take"]) if ir["to_take"] > 0 else "—"
            item = self.income_table.item(i, 5)
            if item:
                item.setText(take_text)
                if ir["to_take"] > 0:
                    item.setForeground(QColor(self._FOCUS))
                else:
                    item.setForeground(QColor(self._MUTED))

            # Update المتبقي column (4) to show remaining AFTER this expense
            rem_item = self.income_table.item(i, 4)
            if rem_item:
                remaining_after = ir["remaining"] - ir["to_take"]
                rem_item.setText(format_currency(remaining_after))
                if remaining_after > 0:
                    rem_item.setForeground(QColor(self._GREEN))
                elif remaining_after == 0:
                    rem_item.setForeground(QColor(self._MUTED))
                else:
                    rem_item.setForeground(QColor(self._RED))

            bg = QColor(self._CARD)
            if ir["to_take"] > 0:
                bg = QColor("#1a2a4a")
            for c in range(6):
                it = self.income_table.item(i, c)
                if it:
                    it.setBackground(bg)

        # Update global progress bar
        covered = amount - remaining_need
        if amount > 0:
            pct = int(min(covered / amount * 100, 100))
        else:
            pct = 0
        self._global_bar.setValue(pct)
        self._global_bar.setFormat(f"{format_currency(covered)} / {format_currency(amount)}  ({pct}%)")

        # Color: red → yellow → green
        if pct >= 100:
            bar_bg = "#065f46"
            bar_chunk = "#34d399"
        elif pct >= 50:
            bar_bg = "#134e4a"
            bar_chunk = "#14b8a6"
        else:
            bar_bg = "#7f1d1d"
            bar_chunk = "#f87171"
        self._global_bar.setStyleSheet(f"""
            QProgressBar{{background:{bar_bg};border:1px solid {self._BORD};
                         border-radius:6px;text-align:center;font-size:14px;
                         font-weight:700;color:{self._TEXT};padding:2px;}}
            QProgressBar::chunk{{background:{bar_chunk};border-radius:4px;}}
        """)

        if amount <= 0:
            self._summary.setVisible(False)
            self._warn.setVisible(False)
            return

        used_dates = [(ir["date"], ir["to_take"]) for ir in self._income_rows if ir["to_take"] > 0]
        if used_dates and remaining_need <= 0:
            parts = [f"{d} ({format_currency(t)})" for d, t in used_dates]
            self._summary.setText(f"✅ سيتم السحب من: {', '.join(parts)}")
            self._summary.setStyleSheet(f"font-size:14px;color:{self._GREEN};background:transparent;border:none;padding:4px 0;")
            self._summary.setVisible(True)
            self._warn.setVisible(False)
        elif remaining_need > 0:
            self._summary.setText(f"⚠️ المبلغ المتبقي: {format_currency(remaining_need)} د.ع لم يتم تغطيته")
            self._summary.setStyleSheet(f"font-size:14px;color:{self._TEAL};background:transparent;border:none;padding:4px 0;")
            self._summary.setVisible(True)
            self._warn.setText(f"❌ الدخل الكلي المتاح ({format_currency(total_available)} د.ع) لا يكفي لتغطية {format_currency(amount)} د.ع")
            self._warn.setVisible(True)
        else:
            self._summary.setVisible(False)
            self._warn.setVisible(False)

    def _save_expense(self):
        expense_type = self.type_combo.currentText().strip()
        amount = self.amount_spin.value()
        user_name = self.user_data.get("full_name", "غير معروف")
        exp_date = QDate.currentDate().toPyDate().strftime("%Y-%m-%d")

        if not expense_type:
            QMessageBox.warning(self, "تنبيه", "يرجى كتابة أو اختيار نوع المصروف")
            return
        if amount <= 0:
            QMessageBox.warning(self, "تنبيه", "يرجى إدخال مبلغ صحيح")
            return

        is_supplier_payment = (expense_type == "🔹 تسديد مذخر")
        if is_supplier_payment:
            supplier_id = self.supplier_combo.currentData()
            if not supplier_id:
                QMessageBox.warning(self, "تنبيه", "يرجى اختيار المذخر من القائمة")
                return
            supp_name = self.supplier_combo.itemData(self.supplier_combo.currentIndex(), Qt.UserRole + 1)
            # Validate amount doesn't exceed total remaining debt
            debts = self.supplier_debt_ctrl.get_unpaid_debts(supplier_id)
            total_debt = sum(float(d["remaining_amount"]) for d in debts)
            if amount > total_debt:
                QMessageBox.warning(self, "تنبيه",
                    f"المبلغ ({format_currency(amount)} د.ع) أكبر من إجمالي دين المذخر\n"
                    f"({format_currency(total_debt)} د.ع). يرجى تقليل المبلغ.")
                return
            type_name = "تسديد مذخر"
            description = f"تسديد مذخر - {supp_name}"
        else:
            type_name = expense_type
            description = expense_type

        used_dates = [ir for ir in self._income_rows if ir["to_take"] > 0]
        total_taken = sum(ir["to_take"] for ir in used_dates)
        if total_taken < amount:
            QMessageBox.warning(self, "تنبيه",
                f"المبلغ المطلوب {format_currency(amount)} د.ع لم يتم تغطيته بالكامل.\n"
                f"تم توفير {format_currency(total_taken)} د.ع فقط من الدخل.\n"
                f"يرجى تقليل المبلغ أو اختيار أيام دخل إضافية.")
            return

        try:
            existing = self.db.fetchone("SELECT id FROM expense_types WHERE name = ?", (type_name,))
            if existing:
                type_id = existing["id"]
            else:
                self.db.execute("INSERT INTO expense_types (name) VALUES (?)", (type_name,))
                type_id = self.db.fetchone("SELECT id FROM expense_types WHERE name = ?", (type_name,))[0]

            self.db.execute(
                """INSERT INTO expenses (amount, description, expense_type_id, user_name, expense_date)
                   VALUES (?, ?, ?, ?, ?)""",
                (str(amount), description, type_id, user_name, exp_date),
            )
            expense_id = self.db.fetchone("SELECT last_insert_rowid()")[0]

            for ir in used_dates:
                self.db.execute(
                    "INSERT INTO expense_income_sources (expense_id, income_date, amount) VALUES (?, ?, ?)",
                    (expense_id, ir["date"], str(ir["to_take"])),
                )

            # Distribute payment across supplier's unpaid debts
            if is_supplier_payment and supplier_id:
                remaining = amount
                for d in debts:
                    if remaining <= 0:
                        break
                    debt_remaining = float(d["remaining_amount"])
                    take = min(remaining, debt_remaining)
                    self.supplier_debt_ctrl.add_payment(d["id"], take, "تسديد مذخر - مصروف")
                    remaining -= take

            msg = f"تم تسجيل المصروف بنجاح\nسحب من: {', '.join(ir['date'] for ir in used_dates)}"
            if is_supplier_payment:
                msg += f"\n✅ تم تخفيض دين المذخر تلقائياً"
            QMessageBox.information(self, "تم", msg)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"حدث خطأ أثناء حفظ المصروف:\n{str(e)}")


class CancelExpenseDialog(QDialog):
    """Dialog to view and cancel recent expenses with full audit trail."""
    def __init__(self, user_data=None, parent=None):
        super().__init__(parent)
        self.db = DatabaseManager()
        self.user_data = user_data or {}
        self._cancelled = False
        self._setup_ui()
        self._load_expenses()

    _TEAL = "#0d9488"
    _TEAL_LIGHT = "#14b8a6"
    _TEAL_DARK = "#134e4a"
    _BG = "#0b1120"
    _CARD = "#141d2e"
    _MUTED = "#94a3b8"
    _TEXT = "#f1f5f9"

    def _lbl(self, text, color, size, bold=False):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"font-size:{size}px;font-weight:{'700' if bold else '400'};color:{color};background:transparent;border:none;")
        return lbl

    def _mkbtn(self, text, bg, fg="#fff", h=38):
        btn = QPushButton(text)
        btn.setFixedHeight(h)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(
            f"QPushButton{{font-size:13px;font-weight:700;background:{bg};color:{fg};"
            f"border:none;border-radius:8px;padding:0 14px;}}"
            f"QPushButton:hover{{opacity:0.8;}}"
        )
        return btn

    def _setup_ui(self):
        self.setWindowTitle("🔄 إلغاء مصروف")
        self.setStyleSheet(f"background:{self._BG};color:{self._TEXT};")
        self.setMinimumWidth(650)
        self.setMinimumHeight(500)
        self.resize(700, 550)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        # Header
        hdr = QHBoxLayout()
        hdr.addWidget(self._lbl("🔄 إلغاء مصروف - اختر المصروف للإلغاء", self._TEAL_LIGHT, 18, True))
        hdr.addStretch()
        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet(f"font-size:13px;color:{self._TEAL_LIGHT};background:transparent;border:none;")
        hdr.addWidget(self._status_lbl)
        layout.addLayout(hdr)

        # Date filter
        filter_row = QHBoxLayout()
        filter_row.addWidget(self._lbl("من:", self._MUTED, 13))
        self._date_from = QDateEdit()
        self._date_from.setDate(QDate.currentDate().addMonths(-1))
        self._date_from.setCalendarPopup(True)
        self._date_from.setStyleSheet(
            "QDateEdit{font-size:13px;padding:4px 10px;background:#1e293b;color:#f1f5f9;"
            "border:1px solid #334155;border-radius:6px;}"
        )
        filter_row.addWidget(self._date_from)
        filter_row.addWidget(self._lbl("إلى:", self._MUTED, 13))
        self._date_to = QDateEdit()
        self._date_to.setDate(QDate.currentDate())
        self._date_to.setCalendarPopup(True)
        self._date_to.setStyleSheet(self._date_from.styleSheet())
        filter_row.addWidget(self._date_to)
        self._filter_btn = self._mkbtn("🔍 تصفية", self._TEAL, h=36)
        self._filter_btn.clicked.connect(self._load_expenses)
        filter_row.addWidget(self._filter_btn)
        filter_row.addStretch()
        layout.addLayout(filter_row)

        # Scroll area for cards
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}"
            "QScrollBar:vertical{background:#1e293b;width:8px;border-radius:4px;}"
            "QScrollBar::handle:vertical{background:#475569;border-radius:4px;min-height:24px;}"
            "QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}")
        self._container = QWidget()
        self._container.setStyleSheet("background:transparent;")
        self._grid = QVBoxLayout(self._container)
        self._grid.setSpacing(8)
        self._scroll.setWidget(self._container)
        layout.addWidget(self._scroll, 1)

        close_btn = self._mkbtn("إغلاق", "#334155")
        close_btn.clicked.connect(self.reject)
        layout.addWidget(close_btn)

    def _load_expenses(self):
        # Clear existing cards
        for i in reversed(range(self._grid.count())):
            w = self._grid.itemAt(i).widget()
            if w:
                w.setParent(None)
                w.deleteLater()

        d1 = self._date_from.date().toPyDate().strftime("%Y-%m-%d")
        d2 = self._date_to.date().toPyDate().strftime("%Y-%m-%d")

        rows = self.db.fetchall("""
            SELECT e.*, et.name as type_name
            FROM expenses e
            LEFT JOIN expense_types et ON e.expense_type_id = et.id
            WHERE e.expense_date BETWEEN ? AND ? AND (e.is_cancelled IS NULL OR e.is_cancelled = 0)
            ORDER BY e.expense_date DESC, e.created_at DESC
        """, (d1, d2))

        if not rows:
            no_data = QLabel("📭 لا توجد مصاريف مسجلة في هذه الفترة")
            no_data.setStyleSheet(f"font-size:16px;color:{self._MUTED};background:transparent;border:none;padding:40px;")
            no_data.setAlignment(Qt.AlignCenter)
            self._grid.addWidget(no_data)
            self._status_lbl.setText("")
            return

        self._status_lbl.setText(f"✅ {len(rows)} مصروف قابل للإلغاء")
        for r in rows:
            self._add_expense_card(r)

    def _add_expense_card(self, row):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame{{background:{self._CARD};border:1px solid {self._TEAL_LIGHT}40;border-radius:10px;}}
            QFrame:hover{{border-color:{self._TEAL_LIGHT};}}
        """)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(14, 10, 14, 10)
        cl.setSpacing(6)

        # Header row
        hdr = QHBoxLayout()
        hdr.setContentsMargins(0, 0, 0, 0)
        hdr.addWidget(self._lbl(
            f"💸 #{row['id']} — {row['type_name'] or row.get('description','')}",
            self._TEXT, 14, True
        ))
        hdr.addStretch()
        amt = float(row["amount"] or 0)
        amt_lbl = self._lbl(f"{format_currency(amt)} د.ع", "#7ba3ff", 15, True)
        hdr.addWidget(amt_lbl)
        cl.addLayout(hdr)

        # Detail row
        detail = f"📅 {row['expense_date']}  |  👤 {row.get('user_name','?')}"
        if row.get("description"):
            detail += f"  |  📝 {row['description']}"
        cl.addWidget(self._lbl(detail, self._MUTED, 12))

        # Cancel button
        cancel_btn = self._mkbtn("🔄 إلغاء هذا المصروف", "#dc2626", h=36)
        cancel_btn.clicked.connect(lambda ch, rid=row["id"], c=card: self._cancel_expense(rid, c))
        cl.addWidget(cancel_btn)

        self._grid.addWidget(card)

    def _cancel_expense(self, expense_id, card_widget):
        from PyQt5.QtWidgets import QInputDialog
        reason, ok = QInputDialog.getText(self, "سبب الإلغاء",
            "لماذا تريد إلغاء هذا المصروف؟\n(اختياري: اكتب السبب أو اتركه فارغاً)")
        if not ok:
            return

        confirm = QMessageBox.question(self, "تأكيد الإلغاء",
            "هل أنت متأكد من إلغاء هذا المصروف؟\n"
            "سيتم عكس خصم المصروف من الدخل.\n"
            "لا يمكن التراجع عن هذا الإجراء.",
            QMessageBox.Yes | QMessageBox.No)
        if confirm != QMessageBox.Yes:
            return

        try:
            expense_id = int(expense_id)
            # 1. Mark expense as cancelled
            self.db.execute(
                "UPDATE expenses SET is_cancelled = 1, cancelled_at = datetime('now','localtime'), "
                "cancelled_by = ? WHERE id = ?",
                (self.user_data.get("id"), expense_id),
            )

            # 2. Record cancellation audit
            self.db.execute(
                "INSERT INTO expense_cancellations (expense_id, cancelled_by, reason) VALUES (?, ?, ?)",
                (expense_id, self.user_data.get("id"), reason or None),
            )

            # 3. Delete income source entries (reverse income deduction)
            self.db.execute(
                "DELETE FROM expense_income_sources WHERE expense_id = ?",
                (expense_id,),
            )

            # 4. Remove card from UI
            card_widget.setParent(None)
            card_widget.deleteLater()

            from utils.toast import ToastNotification
            ToastNotification.show_message("✅ تم إلغاء المصروف وعكس خصمه من الدخل", 5000, self, "🔄 إلغاء مصروف")

        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"فشل إلغاء المصروف:\n{str(e)}")


class ReportsWidget(QWidget):
    def __init__(self, user_data=None, parent=None):
        super().__init__(parent)
        self.db = DatabaseManager()
        self.user_data = user_data or {}
        self._all_stock_data = [] # local storage for search filtering
        self._setup_ui()
        self._load_today_report()

    def _setup_ui(self):
        # Set stylesheet globally for ReportsWidget
        self.setStyleSheet(f"""
            QWidget {{
                font-family: 'Segoe UI', 'Tahoma', 'Arial', sans-serif;
                color: #f1f5f9;  /* Force light color for readability */
            }}
            QLabel {{
                color: #f1f5f9;
            }}
            QTableWidget {{
                background-color: #1e293b;
                border: 1.5px solid #334155;
                border-radius: 12px;
                gridline-color: #334155;
                color: #f1f5f9;
            }}
            QTableWidget::item {{
                color: #f1f5f9;
                font-size: 15px;
                border-bottom: 1.5px solid #0f172a30;
                padding: 8px;
            }}
            QTableWidget::item:selected {{
                background-color: rgba(56, 189, 248, 0.2);
                color: #38bdf8;
            }}
            QHeaderView::section {{
                background-color: #0f172a;
                color: #38bdf8;
                font-size: 15px;
                font-weight: bold;
                border: none;
                border-bottom: 2.5px solid #334155;
                padding: 10px;
            }}
            QLineEdit, QDateEdit, QDoubleSpinBox {{
                background-color: #0f172a;
                color: #ffffff;
                border: 1.5px solid #334155;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 15px;
            }}
            QLineEdit:focus, QDateEdit:focus, QDoubleSpinBox:focus {{
                border-color: #38bdf8;
            }}
        """)

        # Master horizontal layout: Right Sidebar + Left Stack Content
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # ── LEFT PANEL: QStackedWidget ──
        self.stack = QStackedWidget()
        
        # Build Pages
        self._build_page_dashboard()
        self._build_page_sales()
        self._build_page_purchases()
        self._build_page_dispensed()
        self._build_page_stock()

        main_layout.addWidget(self.stack, 1)

        # ── RIGHT PANEL: Vertical Navigation Sidebar ──
        sidebar = QFrame()
        sidebar.setFixedWidth(300)
        sidebar.setStyleSheet(f"""
            QFrame {{
                background: rgba(15, 23, 42, 220);
                border: 1.5px solid {_BORD};
                border-radius: 12px;
            }}
        """)
        sb_lay = QVBoxLayout(sidebar)
        sb_lay.setContentsMargins(12, 14, 12, 14)
        sb_lay.setSpacing(8)

        # Section: Quick Filters (⚡ فلاتر سريعة للفترة)
        sb_lay.addWidget(_lbl("⚡ فلاتر سريعة", _GREEN, 15, True))
        
        quick_grid_widget = QWidget()
        quick_grid_widget.setMinimumHeight(85)
        quick_grid = QGridLayout(quick_grid_widget)
        quick_grid.setContentsMargins(2, 2, 2, 2)
        quick_grid.setSpacing(6)
        
        self.btn_quick_today = _btn("اليوم", _GREEN, fs=14, h=36)
        self.btn_quick_yesterday = _btn("البارحة", _TEAL, fs=14, h=36)
        self.btn_quick_month = _btn("هذا الشهر", _BLUE, fs=14, h=36)
        self.btn_quick_prev_month = _btn("الشهر السابق", _BORD, color="#f1f5f9", fs=14, h=36)
        
        self.btn_quick_today.clicked.connect(self._filter_today)
        self.btn_quick_yesterday.clicked.connect(self._filter_yesterday)
        self.btn_quick_month.clicked.connect(self._filter_this_month)
        self.btn_quick_prev_month.clicked.connect(self._filter_last_month)
        
        quick_grid.addWidget(self.btn_quick_today, 0, 0)
        quick_grid.addWidget(self.btn_quick_yesterday, 0, 1)
        quick_grid.addWidget(self.btn_quick_month, 1, 0)
        quick_grid.addWidget(self.btn_quick_prev_month, 1, 1)
        
        sb_lay.addWidget(quick_grid_widget)

        # Divider
        div_top = QFrame()
        div_top.setFixedHeight(1)
        div_top.setStyleSheet("background-color: #334155;")
        sb_lay.addWidget(div_top)

        # Section 1: Custom Filter
        sb_lay.addWidget(_lbl("🔍 فلترة بالتاريخ", _BLUE, 15, True))
        
        # Explicit locale set to English to render standard numbers (0-9) instead of Indic-Arabic
        en_us_locale = QLocale(QLocale.English, QLocale.UnitedStates)

        sb_lay.addWidget(_lbl("من تاريخ:", _MUTED, 13, False))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("yyyy-MM-dd")
        self.date_from.setDate(QDate.currentDate())
        self.date_from.setLocale(en_us_locale)
        if self.date_from.calendarWidget():
            self.date_from.calendarWidget().setLocale(en_us_locale)
        sb_lay.addWidget(self.date_from)

        sb_lay.addWidget(_lbl("إلى تاريخ:", _MUTED, 13, False))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("yyyy-MM-dd")
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setLocale(en_us_locale)
        if self.date_to.calendarWidget():
            self.date_to.calendarWidget().setLocale(en_us_locale)
        sb_lay.addWidget(self.date_to)

        self.btn_filter = _btn("🔍 تطبيق الفلترة", _BLUE, h=46)
        self.btn_filter.clicked.connect(self._on_filter_clicked)
        sb_lay.addWidget(self.btn_filter)

        # Divider
        div1 = QFrame()
        div1.setFixedHeight(1)
        div1.setStyleSheet("background-color: #334155;")
        sb_lay.addWidget(div1)

        # Section 2: Navigations
        sb_lay.addWidget(_lbl("📋 عرض البيانات", _BLUE, 15, True))

        nav_style = (
            "QPushButton{font-size:14px;font-weight:600;padding:6px 12px;"
            "background:#1e293b;color:#f1f5f9;border:none;border-radius:6px;min-height:32px;"
            "text-align:left}"
            "QPushButton:hover{background:#334155}"
            "QPushButton:pressed{background:#0f172a}"
        )

        self.btn_nav_dashboard = QPushButton("📊 الإحصائيات العامة")
        self.btn_nav_sales = QPushButton("📋 فواتير المبيعات")
        self.btn_nav_purchases = QPushButton("📦 فواتير الشراء")
        self.btn_nav_dispensed = QPushButton("💊 العلاج المصروف")
        self.btn_nav_stock = QPushButton("📂 كلفة المخزن")

        for btn in [self.btn_nav_dashboard, self.btn_nav_sales, self.btn_nav_purchases, self.btn_nav_dispensed, self.btn_nav_stock]:
            btn.setStyleSheet(nav_style)
            btn.setCursor(Qt.PointingHandCursor)

        self.btn_nav_dashboard.clicked.connect(lambda: self._switch_to_page(0, self.btn_nav_dashboard))
        self.btn_nav_sales.clicked.connect(lambda: self._switch_to_page(1, self.btn_nav_sales))
        self.btn_nav_purchases.clicked.connect(lambda: self._switch_to_page(2, self.btn_nav_purchases))
        self.btn_nav_dispensed.clicked.connect(lambda: self._switch_to_page(3, self.btn_nav_dispensed))
        self.btn_nav_stock.clicked.connect(lambda: self._switch_to_page(4, self.btn_nav_stock))

        for btn in [self.btn_nav_dashboard, self.btn_nav_sales, self.btn_nav_purchases, self.btn_nav_dispensed, self.btn_nav_stock]:
            sb_lay.addWidget(btn)

        # Section: Financial Actions
        sb_lay.addWidget(_lbl("💸 العمليات المالية", _BLUE, 16, True))
        
        self.btn_add_expense = _btn("💸 تسجيل مصروف جديد", "#ec4899", h=40)
        self.btn_add_expense.clicked.connect(self._on_add_expense_clicked)
        sb_lay.addWidget(self.btn_add_expense)

        self.btn_cancel_expense = _btn("🔄 إلغاء مصروف", "#0d9488", h=40)
        self.btn_cancel_expense.clicked.connect(self._on_cancel_expense_clicked)
        sb_lay.addWidget(self.btn_cancel_expense)

        # Divider
        div2 = QFrame()
        div2.setFixedHeight(1)
        div2.setStyleSheet("background-color: #334155;")
        sb_lay.addWidget(div2)

        # Section 3: Printing (Context sensitive)
        sb_lay.addWidget(_lbl("🖨 خيارات الطباعة", _BLUE, 16, True))

        self.btn_print_active = _btn("🖨 طباعة التقرير النشط", _GREEN, h=40)
        self.btn_print_active.clicked.connect(self._print_active_report)
        sb_lay.addWidget(self.btn_print_active)

        self.btn_pdf_active = _btn("📄 تصدير التقرير كـ PDF", _TEAL, h=40)
        self.btn_pdf_active.clicked.connect(self._export_active_pdf)
        sb_lay.addWidget(self.btn_pdf_active)

        sb_lay.addStretch()
        main_layout.addWidget(sidebar)

        # Default Active button
        self._switch_to_page(0, self.btn_nav_dashboard)

    # ── Page 0: Summary Cards Dashboard (Symmetric 2x4 Grid) ──
    def _build_page_dashboard(self):
        pg = QWidget()
        lay = QVBoxLayout(pg)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(16)

        lay.addWidget(_lbl("📊 ملخص الأداء المالي والربحي ورأس المال الصيدلاني", _BLUE, 18, True))

        # 8 Statistic Cards
        self.card_sales = self._create_stat_card("إجمالي المبيعات للفترة", "0.00 د.ع", _BLUE)
        self.card_cash = self._create_stat_card("الاستحصال النقدي للفترة", "0.00 د.ع", _GREEN)
        self.card_credit = self._create_stat_card("المبيعات الآجلة للفترة", "0.00 د.ع", _TEAL)
        self.card_purchases = self._create_stat_card("إجمالي المشتريات للفترة", "0.00 د.ع", _RED)
        
        self.card_cogs = self._create_stat_card("كلفة المبيعات (رأس المال المسترجع)", "0.00 د.ع", "#a855f7") # Purple
        self.card_discounts = self._create_stat_card("خصومات الشهر الحالي", "0.00 د.ع", "#fb7185") # Rose pink
        self.card_stock_capital = self._create_stat_card("رأس مال المخزن الحالي", "0.00 د.ع", "#06b6d4") # Cyan
        self.card_profit = self._create_stat_card("صافي أرباح الفترة", "0.00 د.ع", "#10b981") # Emerald/Mint

        grid = QGridLayout()
        grid.setSpacing(16)
        grid.addWidget(self.card_sales, 0, 0)
        grid.addWidget(self.card_cash, 0, 1)
        grid.addWidget(self.card_credit, 0, 2)
        grid.addWidget(self.card_purchases, 0, 3)
        
        grid.addWidget(self.card_cogs, 1, 0)
        grid.addWidget(self.card_discounts, 1, 1)
        grid.addWidget(self.card_stock_capital, 1, 2)
        grid.addWidget(self.card_profit, 1, 3)

        lay.addLayout(grid)
        lay.addStretch()
        self.stack.addWidget(pg)

    # ── Page 1: Sales Invoices Table ──
    def _build_page_sales(self):
        pg = QWidget()
        lay = QVBoxLayout(pg)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        top_bar = QHBoxLayout()
        back_btn = _btn("← رجوع للإحصائيات", _BORD, h=38)
        back_btn.clicked.connect(lambda: self._switch_to_page(0, self.btn_nav_dashboard))
        top_bar.addStretch()
        top_bar.addWidget(_lbl("📋 فواتير المبيعات الصادرة ملخص وتفاصيل", _BLUE, 18, True))
        top_bar.addWidget(back_btn)
        lay.addLayout(top_bar)

        # 4 Stats Cards at the top
        self.sales_card_total = self._create_stat_card("إجمالي المبيعات", "0.00 د.ع", _GREEN)
        self.sales_card_cash = self._create_stat_card("نقدي", "0.00 د.ع", _BLUE)
        self.sales_card_credit = self._create_stat_card("آجل", "0.00 د.ع", _TEAL)
        self.sales_card_discount = self._create_stat_card("الخصومات", "0.00 د.ع", _RED)

        stats_lay = QHBoxLayout()
        stats_lay.setSpacing(12)
        stats_lay.addWidget(self.sales_card_total)
        stats_lay.addWidget(self.sales_card_cash)
        stats_lay.addWidget(self.sales_card_credit)
        stats_lay.addWidget(self.sales_card_discount)
        lay.addLayout(stats_lay)

        # Charts Section
        charts_lay = QHBoxLayout()
        charts_lay.setSpacing(12)
        
        self.sales_chart_line_lbl = QLabel()
        self.sales_chart_line_lbl.setMinimumSize(700, 260)
        self.sales_chart_line_lbl.setStyleSheet("border: 1px solid #334155; border-radius: 8px; background-color: #ffffff;")
        self.sales_chart_line_lbl.setAlignment(Qt.AlignCenter)

        self.sales_chart_donut_lbl = QLabel()
        self.sales_chart_donut_lbl.setMinimumSize(300, 260)
        self.sales_chart_donut_lbl.setStyleSheet("border: 1px solid #334155; border-radius: 8px; background-color: #ffffff;")
        self.sales_chart_donut_lbl.setAlignment(Qt.AlignCenter)

        charts_lay.addWidget(self.sales_chart_line_lbl, 7)
        charts_lay.addWidget(self.sales_chart_donut_lbl, 3)
        lay.addLayout(charts_lay)

        self.sales_table = QTableWidget()
        self.sales_table.setColumnCount(6)
        self.sales_table.setHorizontalHeaderLabels(["الفاتورة", "التاريخ والوقت", "البائع", "الإجمالي", "المدفوع", "طريقة الدفع"])
        self.sales_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 6):
            self.sales_table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.sales_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.sales_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.sales_table.doubleClicked.connect(self._on_sales_table_double_clicked)
        lay.addWidget(self.sales_table)

        self.stack.addWidget(pg)

    # ── Page 2: Purchases / Inventory Entries Table ──
    def _build_page_purchases(self):
        pg = QWidget()
        lay = QVBoxLayout(pg)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        top_bar = QHBoxLayout()
        back_btn = _btn("← رجوع للإحصائيات", _BORD, h=38)
        back_btn.clicked.connect(lambda: self._switch_to_page(0, self.btn_nav_dashboard))
        top_bar.addStretch()
        top_bar.addWidget(_lbl("📦 فواتير الشراء وإدخال المخزن للفترة المحددة", _RED, 18, True))
        top_bar.addWidget(back_btn)
        lay.addLayout(top_bar)

        self.purch_table = QTableWidget()
        self.purch_table.setColumnCount(6)
        self.purch_table.setHorizontalHeaderLabels(["الفاتورة", "التاريخ والوقت", "المذخر", "الإجمالي", "المدفوع", "الحالة"])
        self.purch_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 6):
            self.purch_table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.purch_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.purch_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.purch_table.doubleClicked.connect(self._on_purch_table_double_clicked)
        lay.addWidget(self.purch_table)

        self.stack.addWidget(pg)

    # ── Page 3: Dispensed Medicine Report ──
    def _build_page_dispensed(self):
        pg = QWidget()
        lay = QVBoxLayout(pg)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        top_bar = QHBoxLayout()
        back_btn = _btn("← رجوع للإحصائيات", _BORD, h=38)
        back_btn.clicked.connect(lambda: self._switch_to_page(0, self.btn_nav_dashboard))
        top_bar.addStretch()
        top_bar.addWidget(_lbl("💊 كشف تفاصيل العلاج المصروف وتكلفته للفترة", _BLUE, 18, True))
        top_bar.addWidget(back_btn)
        lay.addLayout(top_bar)

        self.dispensed_table = QTableWidget()
        self.dispensed_table.setColumnCount(8)
        self.dispensed_table.setHorizontalHeaderLabels([
            "الباركود", "اسم المادة", "الكمية المباعة", "كلفة الوحدة", "إجمالي الكلفة", "سعر البيع", "إجمالي البيع", "الأرباح"
        ])
        self.dispensed_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        for i in [0, 2, 3, 4, 5, 6, 7]:
            self.dispensed_table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.dispensed_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.dispensed_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        lay.addWidget(self.dispensed_table, 1)

        # Summary box (Using explicit high-contrast styled labels)
        self.disp_summary = QFrame()
        self.disp_summary.setStyleSheet(f"background: rgba(30, 41, 59, 180); border: 1.5px solid {_BORD}; border-radius: 10px;")
        ds_lay = QHBoxLayout(self.disp_summary)
        ds_lay.setContentsMargins(20, 15, 20, 15)

        self.lbl_disp_total_cost = QLabel()
        self.lbl_disp_total_sale = QLabel()
        self.lbl_disp_total_profit = QLabel()

        # Stylesheet for summary labels to make text clear
        for lbl in [self.lbl_disp_total_cost, self.lbl_disp_total_sale, self.lbl_disp_total_profit]:
            lbl.setStyleSheet("color: #f1f5f9; font-size: 15px; font-weight: bold; background: transparent; border: none;")
            lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        ds_lay.addWidget(self.lbl_disp_total_cost)
        ds_lay.addStretch()
        ds_lay.addWidget(self.lbl_disp_total_sale)
        ds_lay.addStretch()
        ds_lay.addWidget(self.lbl_disp_total_profit)
        lay.addWidget(self.disp_summary)

        self.stack.addWidget(pg)

    # ── Page 4: Stock Capital Valuation Report ──
    def _build_page_stock(self):
        pg = QWidget()
        lay = QVBoxLayout(pg)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        top_bar = QHBoxLayout()
        back_btn = _btn("← رجوع للإحصائيات", _BORD, h=38)
        back_btn.clicked.connect(lambda: self._switch_to_page(0, self.btn_nav_dashboard))
        self.stock_search = QLineEdit()
        self.stock_search.setPlaceholderText("🔍 ابحث باسم المادة أو الباركود...")
        self.stock_search.setFixedWidth(300)
        self.stock_search.textChanged.connect(self._on_stock_search_changed)
        top_bar.addWidget(self.stock_search)
        top_bar.addStretch()
        top_bar.addWidget(_lbl("📦 جرد القيمة الكلية ورأس مال المخزن المتوفر", _BLUE, 18, True))
        top_bar.addWidget(back_btn)
        lay.addLayout(top_bar)

        self.stock_table = QTableWidget()
        self.stock_table.setColumnCount(8)
        self.stock_table.setHorizontalHeaderLabels([
            "الباركود", "اسم المادة", "الصلاحية", "الكمية المتوفرة", "سعر الكلفة", "إجمالي الكلفة (رأس المال)", "سعر البيع", "إجمالي البيع المتوقع"
        ])
        self.stock_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        for i in [0, 2, 3, 4, 5, 6, 7]:
            self.stock_table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.stock_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.stock_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        lay.addWidget(self.stock_table, 1)

        # Summary box (Using explicit high-contrast styled labels)
        self.stock_summary = QFrame()
        self.stock_summary.setStyleSheet(f"background: rgba(30, 41, 59, 180); border: 1.5px solid {_BORD}; border-radius: 10px;")
        ss_lay = QHBoxLayout(self.stock_summary)
        ss_lay.setContentsMargins(20, 15, 20, 15)

        self.lbl_stock_total_cost = QLabel()
        self.lbl_stock_total_sale = QLabel()
        self.lbl_stock_total_profit = QLabel()

        for lbl in [self.lbl_stock_total_cost, self.lbl_stock_total_sale, self.lbl_stock_total_profit]:
            lbl.setStyleSheet("color: #f1f5f9; font-size: 15px; font-weight: bold; background: transparent; border: none;")
            lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        ss_lay.addWidget(self.lbl_stock_total_cost)
        ss_lay.addStretch()
        ss_lay.addWidget(self.lbl_stock_total_sale)
        ss_lay.addStretch()
        ss_lay.addWidget(self.lbl_stock_total_profit)
        lay.addWidget(self.stock_summary)

        self.stack.addWidget(pg)

    # ── Page Switching & Highlight ──
    def _switch_to_page(self, index, button):
        self.stack.setCurrentIndex(index)
        self._update_active_button(button)

    def _update_active_button(self, active_btn):
        buttons = [
            (self.btn_nav_dashboard, _BLUE),
            (self.btn_nav_sales, _BLUE),
            (self.btn_nav_purchases, _BLUE),
            (self.btn_nav_dispensed, _BLUE),
            (self.btn_nav_stock, _BLUE),
        ]
        for btn, accent in buttons:
            if btn == active_btn:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {accent}; color: #0f172a; font-weight: 800; font-size: 15px;
                        border: none; border-radius: 8px; padding: 10px 16px; text-align: right; min-height: 38px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: #1e293b; color: #f1f5f9; font-weight: 700; font-size: 14px;
                        border: 1px solid #334155; border-radius: 8px; padding: 10px 16px; text-align: right; min-height: 38px;
                    }}
                    QPushButton:hover {{
                        background: #334155;
                    }}
                """)

    # ── Stat Cards Creator ──
    def _create_stat_card(self, title, val, color):
        card = QFrame()
        card.setFixedHeight(125)
        card.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1e293b, stop:1 #0f172a);
                border: 1.5px solid #334155; border-left: 6px solid {color}; border-radius: 12px;
            }}
        """)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(20, 15, 20, 15)
        cl.setSpacing(6)

        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("color: #94a3b8; font-size: 14px; font-weight: bold; background: transparent; border: none;")
        t_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        v_lbl = QLabel(val)
        v_lbl.setObjectName("val")
        v_lbl.setStyleSheet(f"color: {color}; font-size: 26px; font-weight: 900; background: transparent; border: none;")
        v_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        cl.addWidget(t_lbl)
        cl.addWidget(v_lbl)

        # Shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 75))
        shadow.setOffset(0, 5)
        card.setGraphicsEffect(shadow)
        
        return card

    def _update_card_val(self, card, val):
        lbl = card.findChild(QLabel, "val")
        if lbl:
            lbl.setText(val)

    # ── Database Loader ──
    def _load_today_report(self):
        self._filter_today()

    def _filter_today(self):
        self.date_from.setDate(QDate.currentDate())
        self.date_to.setDate(QDate.currentDate())
        self._load_data()

    def _filter_yesterday(self):
        yesterday = QDate.currentDate().addDays(-1)
        self.date_from.setDate(yesterday)
        self.date_to.setDate(yesterday)
        self._load_data()

    def _filter_this_month(self):
        today = QDate.currentDate()
        first_day = QDate(today.year(), today.month(), 1)
        self.date_from.setDate(first_day)
        self.date_to.setDate(today)
        self._load_data()

    def _filter_last_month(self):
        today = QDate.currentDate()
        year = today.year()
        month = today.month() - 1
        if month == 0:
            month = 12
            year -= 1
        first_day = QDate(year, month, 1)
        days_in_month = calendar.monthrange(year, month)[1]
        last_day = QDate(year, month, days_in_month)
        self.date_from.setDate(first_day)
        self.date_to.setDate(last_day)
        self._load_data()

    def _on_add_expense_clicked(self):
        dialog = AddExpenseDialog(self.user_data, self)
        if dialog.exec_() == QDialog.Accepted:
            self._load_data()

    def _on_cancel_expense_clicked(self):
        dialog = CancelExpenseDialog(self.user_data, self)
        if dialog.exec_() == QDialog.Accepted:
            self._load_data()

    def _on_filter_clicked(self):
        self._load_data()

    def _load_data(self):
        d1 = self.date_from.date().toPyDate().strftime("%Y-%m-%d")
        d2 = self.date_to.date().toPyDate().strftime("%Y-%m-%d")

        # 1. Stats queries
        r_sales = self.db.fetchone("SELECT SUM(CAST(total_amount AS REAL)) FROM sales WHERE date(created_at, 'localtime') BETWEEN ? AND ?", (d1, d2))
        total_sales_val = r_sales[0] if r_sales and r_sales[0] is not None else 0.0

        r_upfront = self.db.fetchone("SELECT SUM(CAST(paid_amount AS REAL)) FROM sales WHERE date(created_at, 'localtime') BETWEEN ? AND ?", (d1, d2))
        total_upfront_val = r_upfront[0] if r_upfront and r_upfront[0] is not None else 0.0

        r_payments = self.db.fetchone("SELECT SUM(CAST(amount AS REAL)) FROM debt_payments WHERE date(payment_date, 'localtime') BETWEEN ? AND ?", (d1, d2))
        total_payments_val = r_payments[0] if r_payments and r_payments[0] is not None else 0.0
        total_cash_val = total_upfront_val + total_payments_val

        r_credit = self.db.fetchone("SELECT SUM(CAST(total_amount AS REAL) - CAST(paid_amount AS REAL)) FROM sales WHERE date(created_at, 'localtime') BETWEEN ? AND ? AND payment_method = 'credit'", (d1, d2))
        total_credit_val = r_credit[0] if r_credit and r_credit[0] is not None else 0.0

        r_purch = self.db.fetchone("SELECT SUM(CAST(total_amount AS REAL)) FROM supplier_debts WHERE date(created_at, 'localtime') BETWEEN ? AND ?", (d1, d2))
        total_purch_val = r_purch[0] if r_purch and r_purch[0] is not None else 0.0

        r_exp = self.db.fetchone("SELECT SUM(CAST(amount AS REAL)) FROM expenses WHERE expense_date BETWEEN ? AND ? AND (is_cancelled IS NULL OR is_cancelled = 0)", (d1, d2))
        total_expenses_val = r_exp[0] if r_exp and r_exp[0] is not None else 0.0

        # Current Month's Discounts (from 1st of current month to today)
        today = QDate.currentDate()
        first_of_month = QDate(today.year(), today.month(), 1).toString("yyyy-MM-dd")
        today_str = today.toString("yyyy-MM-dd")
        r_month_disc = self.db.fetchone(
            "SELECT SUM(CAST(discount AS REAL)) FROM sales WHERE date(created_at, 'localtime') BETWEEN ? AND ?",
            (first_of_month, today_str)
        )
        month_discount_val = r_month_disc[0] if r_month_disc and r_month_disc[0] is not None else 0.0

        r_cogs = self.db.fetchone("""
            SELECT SUM(si.quantity * CAST(p.purchase_price AS REAL)) 
            FROM sale_items si 
            JOIN sales s ON si.sale_id = s.id 
            JOIN products p ON si.product_id = p.id 
            WHERE date(s.created_at, 'localtime') BETWEEN ? AND ?
        """, (d1, d2))
        total_cogs_val = r_cogs[0] if r_cogs and r_cogs[0] is not None else 0.0

        r_doc = self.db.fetchone("SELECT SUM(CAST(doctor_share AS REAL)) FROM doctor_rewards WHERE date(created_at, 'localtime') BETWEEN ? AND ?", (d1, d2))
        total_doc_val = r_doc[0] if r_doc and r_doc[0] is not None else 0.0

        net_profit_val = total_sales_val - total_cogs_val - total_expenses_val - total_doc_val

        # Current Stock Capital Valuation
        r_stock = self.db.fetchone(
            "SELECT SUM(stock_quantity * CAST(purchase_price AS REAL)) FROM products WHERE stock_quantity > 0 AND is_active = 1"
        )
        stock_capital_val = r_stock[0] if r_stock and r_stock[0] is not None else 0.0

        # Update stat labels in cards
        self._update_card_val(self.card_sales, format_currency(str(total_sales_val)) + " د.ع")
        self._update_card_val(self.card_cash, format_currency(str(total_cash_val)) + " د.ع")
        self._update_card_val(self.card_credit, format_currency(str(total_credit_val)) + " د.ع")
        self._update_card_val(self.card_purchases, format_currency(str(total_purch_val)) + " د.ع")
        self._update_card_val(self.card_cogs, format_currency(str(total_cogs_val)) + " د.ع")
        self._update_card_val(self.card_discounts, format_currency(str(month_discount_val)) + " د.ع")
        self._update_card_val(self.card_stock_capital, format_currency(str(stock_capital_val)) + " د.ع")
        self._update_card_val(self.card_profit, format_currency(str(net_profit_val)) + " د.ع")

        # Page 1: Sales Summary cards & charts
        r_period_disc = self.db.fetchone("SELECT SUM(CAST(discount AS REAL)) FROM sales WHERE date(created_at, 'localtime') BETWEEN ? AND ?", (d1, d2))
        total_discount_val = r_period_disc[0] if r_period_disc and r_period_disc[0] is not None else 0.0

        self._update_card_val(self.sales_card_total, format_currency(str(total_sales_val)) + " د.ع")
        self._update_card_val(self.sales_card_cash, format_currency(str(total_cash_val)) + " د.ع")
        self._update_card_val(self.sales_card_credit, format_currency(str(total_credit_val)) + " د.ع")
        self._update_card_val(self.sales_card_discount, format_currency(str(total_discount_val)) + " د.ع")

        # Draw and display on-screen charts
        from PyQt5.QtGui import QPixmap
        line_img, donut_img = self._draw_sales_charts_images(d1, d2, total_cash_val, total_credit_val)
        self.sales_chart_line_lbl.setPixmap(QPixmap.fromImage(line_img))
        self.sales_chart_donut_lbl.setPixmap(QPixmap.fromImage(donut_img))

        # 2. Populate Sales Table
        invoices = self.db.fetchall("""
            SELECT s.*, u.full_name as user_name
            FROM sales s
            LEFT JOIN users u ON s.user_id = u.id
            WHERE date(s.created_at, 'localtime') BETWEEN ? AND ?
            ORDER BY s.created_at DESC
        """, (d1, d2))

        self.sales_table.setRowCount(0)
        for p in invoices:
            r = self.sales_table.rowCount()
            self.sales_table.insertRow(r)
            
            inv_item = QTableWidgetItem(p["invoice_number"] or "")
            inv_item.setData(Qt.UserRole, p["id"])
            inv_item.setTextAlignment(Qt.AlignCenter)
            self.sales_table.setItem(r, 0, inv_item)
            
            self.sales_table.setItem(r, 1, QTableWidgetItem(str(p["created_at"] or "")[:19]))
            self.sales_table.setItem(r, 2, QTableWidgetItem(p["user_name"] or ""))
            self.sales_table.setItem(r, 3, QTableWidgetItem(format_currency(p["total_amount"])))
            self.sales_table.setItem(r, 4, QTableWidgetItem(format_currency(p["paid_amount"])))
            
            method = p["payment_method"] or "cash"
            method_ar = "نقدي" if method == "cash" else "آجل / ذمم"
            color = _GREEN if method == "cash" else _TEAL
            
            method_item = QTableWidgetItem(method_ar)
            method_item.setTextAlignment(Qt.AlignCenter)
            method_item.setForeground(QBrush(QColor(color)))
            font = method_item.font()
            font.setBold(True)
            method_item.setFont(font)
            self.sales_table.setItem(r, 5, method_item)

            for col in [1, 2, 3, 4]:
                item = self.sales_table.item(r, col)
                if item:
                    item.setTextAlignment(Qt.AlignCenter)

        # 3. Populate Purchases Table
        purchases = self.db.fetchall("""
            SELECT sd.*, s.name as supplier_name
            FROM supplier_debts sd
            LEFT JOIN suppliers s ON sd.supplier_id = s.id
            WHERE date(sd.created_at, 'localtime') BETWEEN ? AND ?
            ORDER BY sd.created_at DESC
        """, (d1, d2))

        self.purch_table.setRowCount(0)
        for p in purchases:
            r = self.purch_table.rowCount()
            self.purch_table.insertRow(r)
            
            inv_item = QTableWidgetItem(p["invoice_number"] or "")
            inv_item.setData(Qt.UserRole, p["id"])
            inv_item.setTextAlignment(Qt.AlignCenter)
            self.purch_table.setItem(r, 0, inv_item)
            
            self.purch_table.setItem(r, 1, QTableWidgetItem(str(p["created_at"] or "")[:19]))
            self.purch_table.setItem(r, 2, QTableWidgetItem(p["supplier_name"] or ""))
            self.purch_table.setItem(r, 3, QTableWidgetItem(format_currency(str(p["total_amount"] or 0))))
            self.purch_table.setItem(r, 4, QTableWidgetItem(format_currency(str(p["paid_amount"] or 0))))
            
            status = p["status"] or "pending"
            status_ar = "مسدد" if status == "paid" else ("جزئي" if status == "partial" else "آجل / ذمم")
            color = _GREEN if status == "paid" else (_TEAL if status == "partial" else _RED)
            
            status_item = QTableWidgetItem(status_ar)
            status_item.setTextAlignment(Qt.AlignCenter)
            status_item.setForeground(QBrush(QColor(color)))
            font = status_item.font()
            font.setBold(True)
            status_item.setFont(font)
            self.purch_table.setItem(r, 5, status_item)

            for col in [1, 2, 3, 4]:
                item = self.purch_table.item(r, col)
                if item:
                    item.setTextAlignment(Qt.AlignCenter)

        # 4. Populate Dispensed Medicine Table
        dispensed_items = self.db.fetchall("""
            SELECT p.barcode, p.name as product_name, SUM(si.quantity) as total_qty, 
                   CAST(p.purchase_price AS REAL) as unit_cost, 
                   SUM(si.quantity * CAST(p.purchase_price AS REAL)) as total_cost,
                   CAST(si.unit_price AS REAL) as unit_sale,
                   SUM(si.total_price) as total_sale
            FROM sale_items si
            JOIN sales s ON si.sale_id = s.id
            JOIN products p ON si.product_id = p.id
            WHERE date(s.created_at, 'localtime') BETWEEN ? AND ?
            GROUP BY si.product_id
            ORDER BY total_qty DESC
        """, (d1, d2))

        self.dispensed_table.setRowCount(0)
        disp_tot_cost = 0.0
        disp_tot_sale = 0.0
        disp_tot_profit = 0.0

        for it in dispensed_items:
            r = self.dispensed_table.rowCount()
            self.dispensed_table.insertRow(r)
            
            qty = int(it["total_qty"] or 0)
            u_cost = float(it["unit_cost"] or 0.0)
            t_cost = float(it["total_cost"] or 0.0)
            t_sale = float(it["total_sale"] or 0.0)
            u_sale = t_sale / qty if qty > 0 else 0.0
            profit = t_sale - t_cost

            disp_tot_cost += t_cost
            disp_tot_sale += t_sale
            disp_tot_profit += profit

            self.dispensed_table.setItem(r, 0, QTableWidgetItem(it["barcode"] or ""))
            self.dispensed_table.setItem(r, 1, QTableWidgetItem(it["product_name"] or ""))
            self.dispensed_table.setItem(r, 2, QTableWidgetItem(str(qty)))
            self.dispensed_table.setItem(r, 3, QTableWidgetItem(format_currency(str(u_cost))))
            self.dispensed_table.setItem(r, 4, QTableWidgetItem(format_currency(str(t_cost))))
            self.dispensed_table.setItem(r, 5, QTableWidgetItem(format_currency(str(u_sale))))
            self.dispensed_table.setItem(r, 6, QTableWidgetItem(format_currency(str(t_sale))))
            
            p_item = QTableWidgetItem(format_currency(str(profit)))
            p_item.setForeground(QBrush(QColor(_GREEN if profit >= 0 else _RED)))
            self.dispensed_table.setItem(r, 7, p_item)

            for col in [0, 2, 3, 4, 5, 6, 7]:
                item = self.dispensed_table.item(r, col)
                if item:
                    item.setTextAlignment(Qt.AlignCenter)

        # Update dispensed totals panel using high-contrast HTML rendering
        self.lbl_disp_total_cost.setText(
            f"<span style='color: #f1f5f9;'>💰 إجمالي كلفة المواد (رأس المال): </span>"
            f"<span style='color: #38bdf8; font-size: 18px; font-weight: bold;'>{format_currency(str(disp_tot_cost))} د.ع</span>"
        )
        self.lbl_disp_total_sale.setText(
            f"<span style='color: #f1f5f9;'>📈 إجمالي قيمة المبيعات: </span>"
            f"<span style='color: #ffffff; font-size: 18px; font-weight: bold;'>{format_currency(str(disp_tot_sale))} د.ع</span>"
        )
        self.lbl_disp_total_profit.setText(
            f"<span style='color: #f1f5f9;'>💵 صافي الأرباح المحققة: </span>"
            f"<span style='color: #34d399; font-size: 18px; font-weight: bold;'>{format_currency(str(disp_tot_profit))} د.ع</span>"
        )

        # 5. Fetch Stock Valuation data
        stock_db_items = self.db.fetchall("""
            SELECT barcode, name, scientific_name, expiry_date, stock_quantity, 
                   CAST(purchase_price AS REAL) as purchase_price, 
                   CAST(sale_price AS REAL) as sale_price
            FROM products
            WHERE stock_quantity > 0 AND is_active = 1
            ORDER BY name ASC
        """)
        self._all_stock_data = [dict(item) for item in stock_db_items]
        self._filter_stock_table(self.stock_search.text())

    def _filter_stock_table(self, query):
        query = query.lower().strip()
        self.stock_table.setRowCount(0)
        
        filtered = []
        for it in self._all_stock_data:
            if not query or query in it["name"].lower() or query in it["barcode"].lower() or (it["scientific_name"] and query in it["scientific_name"].lower()):
                filtered.append(it)

        stock_tot_cost = 0.0
        stock_tot_sale = 0.0
        stock_tot_profit = 0.0

        for it in filtered:
            r = self.stock_table.rowCount()
            self.stock_table.insertRow(r)
            
            qty = int(it["stock_quantity"] or 0)
            u_cost = float(it["purchase_price"] or 0.0)
            t_cost = qty * u_cost
            u_sale = float(it["sale_price"] or 0.0)
            t_sale = qty * u_sale
            profit = t_sale - t_cost

            stock_tot_cost += t_cost
            stock_tot_sale += t_sale
            stock_tot_profit += profit

            self.stock_table.setItem(r, 0, QTableWidgetItem(it["barcode"] or ""))
            self.stock_table.setItem(r, 1, QTableWidgetItem(it["name"] or ""))
            self.stock_table.setItem(r, 2, QTableWidgetItem(it["expiry_date"] or "غير محدد"))
            self.stock_table.setItem(r, 3, QTableWidgetItem(str(qty)))
            self.stock_table.setItem(r, 4, QTableWidgetItem(format_currency(str(u_cost))))
            self.stock_table.setItem(r, 5, QTableWidgetItem(format_currency(str(t_cost))))
            self.stock_table.setItem(r, 6, QTableWidgetItem(format_currency(str(u_sale))))
            self.stock_table.setItem(r, 7, QTableWidgetItem(format_currency(str(t_sale))))

            for col in [0, 2, 3, 4, 5, 6, 7]:
                item = self.stock_table.item(r, col)
                if item:
                    item.setTextAlignment(Qt.AlignCenter)

        # Update stock summary widgets using high-contrast HTML rendering
        self.lbl_stock_total_cost.setText(
            f"<span style='color: #f1f5f9;'>💰 إجمالي رأس مال المخزن (الكلفة): </span>"
            f"<span style='color: #38bdf8; font-size: 18px; font-weight: bold;'>{format_currency(str(stock_tot_cost))} د.ع</span>"
        )
        self.lbl_stock_total_sale.setText(
            f"<span style='color: #f1f5f9;'>📈 القيمة البيعية المتوقعة: </span>"
            f"<span style='color: #ffffff; font-size: 18px; font-weight: bold;'>{format_currency(str(stock_tot_sale))} د.ع</span>"
        )
        self.lbl_stock_total_profit.setText(
            f"<span style='color: #f1f5f9;'>💵 الأرباح المتوقعة: </span>"
            f"<span style='color: #34d399; font-size: 18px; font-weight: bold;'>{format_currency(str(stock_tot_profit))} د.ع</span>"
        )

    def _on_stock_search_changed(self, text):
        self._filter_stock_table(text)

    # ── Double Click Handlers ──
    def _on_sales_table_double_clicked(self, index):
        row = index.row()
        inv_item = self.sales_table.item(row, 0)
        if not inv_item:
            return
        invoice_number = inv_item.text()
        sale_id = inv_item.data(Qt.UserRole)
        
        dialog = InvoiceItemsDialog(invoice_number, sale_id, self)
        dialog.exec_()

    def _on_purch_table_double_clicked(self, index):
        row = index.row()
        inv_item = self.purch_table.item(row, 0)
        if not inv_item:
            return
        invoice_number = inv_item.text()
        purchase_id = inv_item.data(Qt.UserRole)
        
        dialog = PurchaseItemsDialog(invoice_number, purchase_id, self)
        dialog.exec_()

    # ── PRINTING & PDF EXPORT LOGIC ──
    def _get_pharmacy_name(self):
        pn_row = self.db.fetchone("SELECT setting_value FROM settings WHERE setting_key = 'pharmacy_name'")
        return pn_row["setting_value"] if pn_row and pn_row["setting_value"] else "صيدليتي"

    def _print_html_content(self, html_content, title):
        printer = QPrinter(QPrinter.ScreenResolution)
        printer.setPageMargins(4, 4, 4, 4, QPrinter.Millimeter)
        printer.setPageSize(QPrinter.A4)
        printer.setOrientation(QPrinter.Portrait)
        # Remove @page margin (printer margins handle it)
        html_content = html_content.replace(
            '@page { size: A4 portrait; }',
            '@page { size: A4 portrait; margin: 0; }'
        )
        doc = QTextDocument()
        # Set document page size to printable area BEFORE setHtml
        from PyQt5.QtCore import QSizeF
        page = printer.pageRect(QPrinter.DevicePixel)
        doc.setPageSize(QSizeF(page.width(), page.height()))
        doc.setHtml(html_content)
        preview = QPrintPreviewDialog(printer)
        preview.setWindowTitle(f"معاينة قبل الطباعة - {title}")
        preview.resize(1000, 750)
        preview.paintRequested.connect(lambda p: doc.print_(p))
        preview.exec_()

    def _export_pdf_content(self, html_content, default_filename):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "حفظ التقرير كملف PDF", default_filename, "PDF Files (*.pdf)"
        )
        if file_path:
            if not file_path.endswith(".pdf"):
                file_path += ".pdf"
            
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(file_path)
            printer.setPageSize(QPrinter.A4)
            printer.setOrientation(QPrinter.Landscape)
            printer.setPageMargins(12, 12, 12, 12, QPrinter.Millimeter)
            
            doc = QTextDocument()
            doc.setHtml(html_content)
            # Use QSizeF (float) not QSize (int) - PyQt5 requires QSizeF here
            page_rect = printer.pageRect()
            from PyQt5.QtCore import QSizeF
            doc.setPageSize(QSizeF(page_rect.width(), page_rect.height()))
            doc.print_(printer)
            
            QMessageBox.information(self, "تم بنجاح", f"تم حفظ ملف PDF للتقرير بنجاح:\n{os.path.basename(file_path)}")

    # ── Print Action Connections ──
    def _print_active_report(self):
        try:
            idx = self.stack.currentIndex()
            if idx == 0:
                self._print_comprehensive()
            elif idx == 1:
                self._print_sales_list()
            elif idx == 2:
                self._print_purchases_list()
            elif idx == 3:
                self._print_dispensed()
            elif idx == 4:
                self._print_stock_val()
        except Exception as e:
            QMessageBox.critical(self, "خطأ في الطباعة",
                f"عذراً، لا يمكن الطباعة حالياً. تأكد من توصيل الطابعة.\n\n{str(e)}")

    def _export_active_pdf(self):
        idx = self.stack.currentIndex()
        if idx == 0:
            self._export_comprehensive_pdf()
        elif idx == 1:
            self._export_sales_list_pdf()
        elif idx == 2:
            self._export_purchases_list_pdf()
        elif idx == 3:
            self._export_dispensed_pdf()
        elif idx == 4:
            self._export_stock_pdf()

    # ── HTML Generators & Actions ──
    def _print_comprehensive(self):
        html = self._generate_comprehensive_html()
        self._print_html_content(html, "التقرير المالي الشامل للفترة")

    def _export_comprehensive_pdf(self):
        html = self._generate_comprehensive_html()
        self._export_pdf_content(html, f"التقرير_المالي_الشامل_{self.date_from.date().toString('yyyyMMdd')}_إلى_{self.date_to.date().toString('yyyyMMdd')}.pdf")

    def _print_sales_list(self):
        self._print_sales_report_direct(to_pdf=False)

    def _export_sales_list_pdf(self):
        self._print_sales_report_direct(to_pdf=True)

    def _print_sales_report_direct(self, to_pdf=False):
        """Render the full Sales Summary report directly via QPainter on a QPrinter.
        This avoids QTextDocument's inability to render data:image base64 URIs."""
        from PyQt5.QtGui import QPixmap

        d1 = self.date_from.date().toPyDate().strftime("%Y-%m-%d")
        d2 = self.date_to.date().toPyDate().strftime("%Y-%m-%d")
        ph_name = self._get_pharmacy_name()

        # ── Gather Data ──
        r_sales = self.db.fetchone("SELECT SUM(CAST(total_amount AS REAL)) FROM sales WHERE date(created_at, 'localtime') BETWEEN ? AND ?", (d1, d2))
        total_sales = r_sales[0] if r_sales and r_sales[0] is not None else 0.0

        r_upfront = self.db.fetchone("SELECT SUM(CAST(paid_amount AS REAL)) FROM sales WHERE date(created_at, 'localtime') BETWEEN ? AND ?", (d1, d2))
        total_upfront = r_upfront[0] if r_upfront and r_upfront[0] is not None else 0.0

        r_payments = self.db.fetchone("SELECT SUM(CAST(amount AS REAL)) FROM debt_payments WHERE date(payment_date, 'localtime') BETWEEN ? AND ?", (d1, d2))
        total_payments = r_payments[0] if r_payments and r_payments[0] is not None else 0.0
        total_cash = total_upfront + total_payments

        r_credit = self.db.fetchone("SELECT SUM(CAST(total_amount AS REAL) - CAST(paid_amount AS REAL)) FROM sales WHERE date(created_at, 'localtime') BETWEEN ? AND ? AND payment_method = 'credit'", (d1, d2))
        total_credit = r_credit[0] if r_credit and r_credit[0] is not None else 0.0

        r_disc = self.db.fetchone("SELECT SUM(CAST(discount AS REAL)) FROM sales WHERE date(created_at, 'localtime') BETWEEN ? AND ?", (d1, d2))
        total_discount = r_disc[0] if r_disc and r_disc[0] is not None else 0.0

        invoices = self.db.fetchall("""
            SELECT s.*, u.full_name as user_name, c.name as customer_name
            FROM sales s
            LEFT JOIN users u ON s.user_id = u.id
            LEFT JOIN customers c ON s.customer_id = c.id
            WHERE date(s.created_at, 'localtime') BETWEEN ? AND ?
            ORDER BY s.created_at DESC
        """, (d1, d2))

        # ── Build chart images ──
        line_img, donut_img = self._draw_sales_charts_images(d1, d2, total_cash, total_credit)
        line_pix = QPixmap.fromImage(line_img)
        donut_pix = QPixmap.fromImage(donut_img)

        # ── Setup Printer ──
        printer = QPrinter(QPrinter.HighResolution)
        printer.setPageSize(QPrinter.A4)
        printer.setOrientation(QPrinter.Landscape)
        printer.setPageMargins(10, 10, 10, 10, QPrinter.Millimeter)

        if to_pdf:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "حفظ التقرير كملف PDF",
                f"تقرير_ملخص_المبيعات_{d1}.pdf",
                "PDF Files (*.pdf)"
            )
            if not file_path:
                return
            if not file_path.endswith(".pdf"):
                file_path += ".pdf"
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(file_path)

            self._do_paint_sales_report(printer, line_pix, donut_pix, ph_name, d1, d2,
                                        total_sales, total_cash, total_credit, total_discount, invoices)
            QMessageBox.information(self, "تم بنجاح", f"تم حفظ ملف PDF بنجاح:\n{os.path.basename(file_path)}")
        else:
            preview = QPrintPreviewDialog(printer)
            preview.setWindowTitle("معاينة قبل الطباعة - ملخص المبيعات")
            preview.resize(1100, 800)
            preview.paintRequested.connect(
                lambda p: self._do_paint_sales_report(p, line_pix, donut_pix, ph_name, d1, d2,
                                                      total_sales, total_cash, total_credit, total_discount, invoices)
            )
            preview.exec_()

    def _do_paint_sales_report(self, printer, line_pix, donut_pix, ph_name, d1, d2,
                               total_sales, total_cash, total_credit, total_discount, invoices):
        """Draw the full Sales Summary page onto a QPrinter using QPainter directly."""
        p = QPainter()
        p.begin(printer)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)

        page_rect = printer.pageRect()
        W = page_rect.width()
        H = page_rect.height()

        # Scale factor (printer is HighResolution ~300dpi vs screen ~96dpi)
        scale = W / 1050.0

        def sc(v):
            return int(v * scale)

        # ── Background white ──
        p.fillRect(page_rect, QBrush(QColor("#ffffff")))

        # ── Title ──
        y = sc(12)
        p.setFont(QFont("Segoe UI", sc(14), QFont.Bold))
        p.setPen(QColor("#0f172a"))
        title_rect = QRectF(0, y, W, sc(30))
        p.drawText(title_rect, Qt.AlignHCenter | Qt.AlignVCenter, "1. ملخص المبيعات")
        y += sc(34)

        # ── Subtitle/Date Badge ──
        p.setFont(QFont("Segoe UI", sc(7)))
        p.setPen(QColor("#475569"))
        badge_text = f"تصفية  |  من {d1} إلى {d2}"
        badge_rect = QRectF(0, y, W, sc(16))
        p.drawText(badge_rect, Qt.AlignHCenter | Qt.AlignVCenter, badge_text)
        y += sc(22)

        # ── 4 Stats Cards ──
        cards = [
            ("إجمالي المبيعات", format_currency(str(total_sales)), "#10b981"),
            ("نقدي",            format_currency(str(total_cash)),   "#1d4ed8"),
            ("آجل",             format_currency(str(total_credit)), "#3b82f6"),
            ("الخصومات",       format_currency(str(total_discount)),"#10b981"),
        ]
        card_w = (W - sc(36)) // 4
        card_h = sc(55)
        card_spacing = sc(12)
        cx_start = sc(0)

        for i, (title, val, color) in enumerate(cards):
            cx = cx_start + i * (card_w + card_spacing)
            card_rect = QRectF(cx, y, card_w, card_h)
            # Card border
            p.setPen(QPen(QColor("#e2e8f0"), sc(0.8)))
            p.setBrush(QBrush(QColor("#ffffff")))
            p.drawRoundedRect(card_rect, sc(5), sc(5))
            # Left color bar
            bar_rect = QRectF(cx, y, sc(4), card_h)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(QColor(color)))
            p.drawRoundedRect(bar_rect, sc(2), sc(2))
            # Title text
            p.setPen(QColor("#64748b"))
            p.setFont(QFont("Segoe UI", sc(6)))
            p.drawText(QRectF(cx + sc(8), y + sc(8), card_w - sc(10), sc(14)),
                       Qt.AlignRight | Qt.AlignVCenter, title)
            # Value text
            p.setPen(QColor(color))
            p.setFont(QFont("Segoe UI", sc(10), QFont.Bold))
            p.drawText(QRectF(cx + sc(8), y + sc(22), card_w - sc(10), sc(22)),
                       Qt.AlignRight | Qt.AlignVCenter, val)
            # Unit
            p.setPen(QColor("#94a3b8"))
            p.setFont(QFont("Segoe UI", sc(5.5)))
            p.drawText(QRectF(cx + sc(8), y + sc(43), card_w - sc(10), sc(10)),
                       Qt.AlignRight | Qt.AlignVCenter, "د.ع")

        y += card_h + sc(12)

        # ── Charts Row ──
        chart_area_h = sc(145)
        line_w = int(W * 0.68)
        donut_w = W - line_w - sc(10)

        # Line chart
        scaled_line = line_pix.scaled(line_w, chart_area_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        line_img_rect = QRectF(0, y, line_w, chart_area_h)
        p.setPen(QPen(QColor("#e2e8f0"), sc(0.5)))
        p.setBrush(QBrush(QColor("#ffffff")))
        p.drawRoundedRect(line_img_rect, sc(4), sc(4))
        p.drawPixmap(int(line_img_rect.x()), int(line_img_rect.y()),
                     scaled_line.width(), scaled_line.height(), scaled_line)

        # Donut chart
        donut_x = line_w + sc(10)
        scaled_donut = donut_pix.scaled(donut_w, chart_area_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        donut_img_rect = QRectF(donut_x, y, donut_w, chart_area_h)
        p.setPen(QPen(QColor("#e2e8f0"), sc(0.5)))
        p.drawRoundedRect(donut_img_rect, sc(4), sc(4))
        p.drawPixmap(int(donut_img_rect.x()), int(donut_img_rect.y()),
                     scaled_donut.width(), scaled_donut.height(), scaled_donut)

        y += chart_area_h + sc(12)

        # ── Invoices Table Title ──
        p.setPen(QColor("#0f172a"))
        p.setFont(QFont("Segoe UI", sc(7.5), QFont.Bold))
        p.drawText(QRectF(0, y, W, sc(16)), Qt.AlignRight | Qt.AlignVCenter, "أحدث الفواتير")
        y += sc(18)

        # ── Table Header ──
        col_widths = [int(W * r) for r in [0.20, 0.14, 0.28, 0.19, 0.19]]
        headers = ["القيمة", "التاريخ", "الزبون", "نوع الدفع", "رقم الفاتورة"]
        row_h = sc(18)

        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor("#f8fafc")))
        p.drawRect(QRectF(0, y, W, row_h))

        p.setPen(QPen(QColor("#e2e8f0"), sc(0.5)))
        p.drawLine(QPointF(0, y + row_h), QPointF(W, y + row_h))

        p.setFont(QFont("Segoe UI", sc(6), QFont.Bold))
        p.setPen(QColor("#475569"))
        cx2 = W
        for ci, (h, cw) in enumerate(zip(headers, col_widths)):
            cx2 -= cw
            p.drawText(QRectF(cx2, y, cw, row_h), Qt.AlignHCenter | Qt.AlignVCenter, h)
        y += row_h

        # ── Table Rows ──
        display_invoices = invoices[:12]
        p.setFont(QFont("Segoe UI", sc(5.8)))
        for ri, s in enumerate(display_invoices):
            method_ar = "نقدي" if s["payment_method"] == "cash" else "آجل"
            cust_name = s["customer_name"] or "زبون عام"
            row_vals = [format_currency(s["total_amount"]) + " د.ع",
                        s["created_at"][:10], cust_name, method_ar, s["invoice_number"]]

            row_bg = QColor("#f9fafb") if ri % 2 == 1 else QColor("#ffffff")
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(row_bg))
            p.drawRect(QRectF(0, y, W, row_h))

            p.setPen(QPen(QColor("#f1f5f9"), sc(0.4)))
            p.drawLine(QPointF(0, y + row_h), QPointF(W, y + row_h))

            p.setPen(QColor("#334155"))
            cx2 = W
            for ci, (rv, cw) in enumerate(zip(row_vals, col_widths)):
                cx2 -= cw
                if ci == 0:
                    p.setFont(QFont("Segoe UI", sc(5.8), QFont.Bold))
                    p.setPen(QColor("#0f172a"))
                else:
                    p.setFont(QFont("Segoe UI", sc(5.8)))
                    p.setPen(QColor("#334155"))
                p.drawText(QRectF(cx2, y, cw, row_h), Qt.AlignHCenter | Qt.AlignVCenter, rv)
            y += row_h

        # ── Footer ──
        p.setPen(QColor("#94a3b8"))
        p.setFont(QFont("Segoe UI", sc(5)))
        p.drawText(QRectF(0, H - sc(14), W, sc(12)),
                   Qt.AlignHCenter | Qt.AlignVCenter,
                   f"RTX - ملخص المبيعات | {ph_name} | {QDate.currentDate().toPyDate().strftime('%Y-%m-%d')}")

        p.end()

    def _print_purchases_list(self):
        html = self._generate_purchases_list_html()
        self._print_html_content(html, "تقرير فواتير الشراء وإدخال المخزن")

    def _export_purchases_list_pdf(self):
        html = self._generate_purchases_list_html()
        self._export_pdf_content(html, f"تقرير_فواتير_الشراء_{self.date_from.date().toString('yyyyMMdd')}.pdf")

    def _print_dispensed(self):
        html = self._generate_dispensed_html()
        self._print_html_content(html, "تقرير العلاج المصروف ورأس المال")

    def _export_dispensed_pdf(self):
        html = self._generate_dispensed_html()
        self._export_pdf_content(html, f"تقرير_العلاج_المصروف_{self.date_from.date().toString('yyyyMMdd')}.pdf")

    def _print_stock_val(self):
        html = self._generate_stock_html()
        self._print_html_content(html, "تقرير قيمة وجرد المخزن")

    def _export_stock_pdf(self):
        html = self._generate_stock_html()
        self._export_pdf_content(html, f"تقرير_رأس_مال_المخزن_{QDate.currentDate().toPyDate().strftime('%Y%m%d')}.pdf")

    # ── HTML Generators ──
    def _generate_comprehensive_html(self):
        d1 = self.date_from.date().toPyDate().strftime("%Y-%m-%d")
        d2 = self.date_to.date().toPyDate().strftime("%Y-%m-%d")
        ph_name = self._get_pharmacy_name()

        r_sales = self.db.fetchone("SELECT SUM(CAST(total_amount AS REAL)) FROM sales WHERE date(created_at, 'localtime') BETWEEN ? AND ?", (d1, d2))
        total_sales = r_sales[0] if r_sales and r_sales[0] is not None else 0.0

        r_upfront = self.db.fetchone("SELECT SUM(CAST(paid_amount AS REAL)) FROM sales WHERE date(created_at, 'localtime') BETWEEN ? AND ?", (d1, d2))
        total_upfront = r_upfront[0] if r_upfront and r_upfront[0] is not None else 0.0

        r_payments = self.db.fetchone("SELECT SUM(CAST(amount AS REAL)) FROM debt_payments WHERE date(payment_date, 'localtime') BETWEEN ? AND ?", (d1, d2))
        total_payments = r_payments[0] if r_payments and r_payments[0] is not None else 0.0
        total_cash = total_upfront + total_payments

        r_credit = self.db.fetchone("SELECT SUM(CAST(total_amount AS REAL) - CAST(paid_amount AS REAL)) FROM sales WHERE date(created_at, 'localtime') BETWEEN ? AND ? AND payment_method = 'credit'", (d1, d2))
        total_credit = r_credit[0] if r_credit and r_credit[0] is not None else 0.0

        r_purch = self.db.fetchone("SELECT SUM(CAST(total_amount AS REAL)) FROM supplier_debts WHERE date(created_at, 'localtime') BETWEEN ? AND ?", (d1, d2))
        total_purch = r_purch[0] if r_purch and r_purch[0] is not None else 0.0

        r_exp = self.db.fetchone("SELECT SUM(CAST(amount AS REAL)) FROM expenses WHERE expense_date BETWEEN ? AND ? AND (is_cancelled IS NULL OR is_cancelled = 0)", (d1, d2))
        total_expenses = r_exp[0] if r_exp and r_exp[0] is not None else 0.0

        r_disc = self.db.fetchone("SELECT SUM(CAST(discount AS REAL)) FROM sales WHERE date(created_at, 'localtime') BETWEEN ? AND ?", (d1, d2))
        total_discount_val = r_disc[0] if r_disc and r_disc[0] is not None else 0.0

        r_cogs = self.db.fetchone("""
            SELECT SUM(si.quantity * CAST(p.purchase_price AS REAL)) 
            FROM sale_items si 
            JOIN sales s ON si.sale_id = s.id 
            JOIN products p ON si.product_id = p.id 
            WHERE date(s.created_at, 'localtime') BETWEEN ? AND ?
        """, (d1, d2))
        total_cogs = r_cogs[0] if r_cogs and r_cogs[0] is not None else 0.0

        r_doc = self.db.fetchone("SELECT SUM(CAST(doctor_share AS REAL)) FROM doctor_rewards WHERE date(created_at, 'localtime') BETWEEN ? AND ?", (d1, d2))
        total_doc = r_doc[0] if r_doc and r_doc[0] is not None else 0.0

        net_profit = total_sales - total_cogs - total_expenses - total_doc

        sales_invoices = self.db.fetchall("""
            SELECT s.*, u.full_name as user_name
            FROM sales s
            LEFT JOIN users u ON s.user_id = u.id
            WHERE date(s.created_at, 'localtime') BETWEEN ? AND ?
            ORDER BY s.created_at DESC
        """, (d1, d2))

        # Calculate cost + profit per invoice
        cost_map = {}
        if sales_invoices:
            ids = [s["id"] for s in sales_invoices]
            placeholders = ",".join("?" for _ in ids)
            cost_rows = self.db.fetchall(f"""
                SELECT si.sale_id, SUM(
                    CAST(si.total_price AS REAL) 
                    / NULLIF(CAST(p.sale_price AS REAL) * COALESCE(NULLIF(p.strips_per_pack, 0), 1), 0) 
                    * COALESCE(CAST(p.purchase_price AS REAL), 0)
                ) as total_cost
                FROM sale_items si
                LEFT JOIN products p ON si.product_id = p.id
                WHERE si.sale_id IN ({placeholders})
                GROUP BY si.sale_id
            """, tuple(ids))
            for row in cost_rows:
                cost_map[row["sale_id"]] = float(row["total_cost"] or 0.0)

        purchases_invoices = self.db.fetchall("""
            SELECT sd.*, s.name as supplier_name
            FROM supplier_debts sd
            LEFT JOIN suppliers s ON sd.supplier_id = s.id
            WHERE date(sd.created_at, 'localtime') BETWEEN ? AND ?
            ORDER BY sd.created_at DESC
        """, (d1, d2))

        expenses_list = self.db.fetchall("""
            SELECT e.*, et.name as type_name
            FROM expenses e
            LEFT JOIN expense_types et ON e.expense_type_id = et.id
            WHERE e.expense_date BETWEEN ? AND ? AND (e.is_cancelled IS NULL OR e.is_cancelled = 0)
            ORDER BY e.expense_date DESC
        """, (d1, d2))

        # Build income_source map per expense
        exp_income_map = {}
        if expenses_list:
            eids = tuple(e["id"] for e in expenses_list)
            if eids:
                ph = ",".join("?" for _ in eids)
                src_rows = self.db.fetchall(f"""
                    SELECT expense_id, income_date, amount
                    FROM expense_income_sources
                    WHERE expense_id IN ({ph})
                    ORDER BY income_date DESC
                """, eids)
                for sr in src_rows:
                    eid = sr["expense_id"]
                    if eid not in exp_income_map:
                        exp_income_map[eid] = []
                    exp_income_map[eid].append(sr)

        supplier_debts = self.db.fetchall("""
            SELECT s.name as supplier_name,
                   COUNT(sd.id) as invoice_count,
                   SUM(CAST(sd.total_amount AS REAL)) as total_debt,
                   SUM(CAST(sd.paid_amount AS REAL)) as total_paid,
                   SUM(CAST(sd.remaining_amount AS REAL)) as remaining
            FROM supplier_debts sd
            LEFT JOIN suppliers s ON sd.supplier_id = s.id
            WHERE sd.status != 'paid' AND date(sd.created_at, 'localtime') BETWEEN ? AND ?
            GROUP BY sd.supplier_id
            ORDER BY remaining DESC
        """, (d1, d2))

        product_sales_data = self.db.fetchall("""
            SELECT p.name, p.stock_quantity,
                   COALESCE(SUM(si.quantity), 0) as sold_qty,
                   COALESCE(SUM(CAST(si.total_price AS REAL)), 0) as total_sale
            FROM products p
            LEFT JOIN sale_items si ON si.product_id = p.id
            LEFT JOIN sales s ON si.sale_id = s.id AND date(s.created_at, 'localtime') BETWEEN ? AND ?
            WHERE p.is_active = 1
            GROUP BY p.id
            ORDER BY p.name ASC
        """, (d1, d2))

        html = f"""
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                @page {{ size: A4 portrait; }}
                body {{ font-family: "Segoe UI", Tahoma, Arial, sans-serif; color: #1e293b; margin: 0; padding: 0; font-size: 13pt; line-height: 1.7; text-align: center; }}
                .header {{ border-bottom: 3px solid #b8860b; margin-bottom: 20px; padding-bottom: 16px; }}
                .header h1 {{ margin: 0; font-size: 26pt; color: #0f172a; font-weight: 800; letter-spacing: 3px; }}
                .date-range {{ margin: 6px 0 16px 0; font-size: 13pt; color: #78716c; font-family: "Segoe UI", "Calibri", Arial, sans-serif; font-weight: 500; letter-spacing: 1px; }}
                h2 {{ font-size: 18pt; color: #1e293b; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; margin: 0 0 14px 0; font-weight: 700; }}
                h2.section-break {{ page-break-before: always; }}
                .summary-page {{ padding-top: 10px; }}
                .summary {{ border-collapse: collapse; }}
                .summary th {{ background: #1e293b; color: #ffffff; padding: 14px 10px; border: 1px solid #334155; text-align: center; font-size: 17pt; font-weight: 700; }}
                .summary td {{ padding: 12px 10px; border: 1px solid #cbd5e1; text-align: center; font-size: 17pt; font-weight: 600; color: #0f172a; }}
                table {{ width: 100%; border-collapse: collapse; margin: 0 auto 10px auto; }}
                .table-data th {{ background: #f1f5f9; color: #1e293b; padding: 5px 3px; border: 1px solid #cbd5e1; text-align: center; font-size: 8pt; font-weight: 700; white-space: nowrap; }}
                .table-data td {{ padding: 3px 3px; border: 1px solid #e2e8f0; text-align: center; font-size: 8pt; white-space: nowrap; }}
                .footer {{ text-align: center; font-size: 9pt; color: #94a3b8; border-top: 1px solid #e2e8f0; padding-top: 5px; margin-top: 16px; }}
        </head>
        <body>
            <div class="header">
                <h1>RTX</h1>
            </div>

            <div class="summary-page">
            <h2>📊 الخلاصة المالية للفترة</h2>
            <p class="date-range">{d1} — {d2}</p>
            <table width="100%" cellspacing="0" cellpadding="0" class="summary">
                <tr><th width="50%">البيان</th><th width="50%">المبلغ</th></tr>
                <tr><td>💰 إجمالي المبيعات</td><td style="color:#2563eb;font-weight:700;">{format_currency(str(total_sales))} د.ع</td></tr>
                <tr><td>✅ الاستحصال النقدي</td><td style="color:#059669;font-weight:700;">{format_currency(str(total_cash))} د.ع</td></tr>
                <tr><td>📋 المبيعات الآجلة</td><td style="color:#0d9488;font-weight:700;">{format_currency(str(total_credit))} د.ع</td></tr>
                <tr><td>📦 إجمالي المشتريات</td><td style="color:#dc2626;font-weight:700;">{format_currency(str(total_purch))} د.ع</td></tr>
                <tr><td>💸 إجمالي المصاريف</td><td style="color:#ea580c;font-weight:700;">{format_currency(str(total_expenses))} د.ع</td></tr>
                <tr><td>🏷️ الخصومات الممنوحة</td><td style="color:#7c3aed;font-weight:700;">{format_currency(str(total_discount_val))} د.ع</td></tr>
                <tr><td>📄 عدد فواتير المبيعات</td><td style="font-weight:700;">{len(sales_invoices)}</td></tr>
                <tr><td style="font-weight:700;background:#f3f4f6;">📈 صافي الأرباح</td><td style="color:#059669;font-weight:800;background:#f3f4f6;">{format_currency(str(net_profit))} د.ع</td></tr>
            </table>
            </div>
        """

        html += '<h2 class="section-break">📋 تفاصيل فواتير المبيعات</h2>'
        html += '<table width="100%" cellspacing="0" cellpadding="0" class="table-data">'
        html += '<tr>'
        html += '<th width="9%">الدفع</th><th width="9%">الربح</th><th width="10%">المدفوع</th><th width="10%">الكلفة</th><th width="7%">الخصم</th><th width="10%">المبلغ</th><th width="10%">البائع</th><th width="11%">التاريخ</th><th width="18%">الفاتورة</th><th width="6%">ت</th>'
        html += '</tr>'
        if sales_invoices:
            sum_total = 0.0
            sum_discount = 0.0
            sum_cost = 0.0
            sum_paid = 0.0
            sum_profit = 0.0
            for i, s in enumerate(sales_invoices, 1):
                method_ar = "نقدي" if s["payment_method"] == "cash" else "آجل"
                total = float(s["total_amount"] or 0)
                discount = float(s["discount"] or 0)
                cost = cost_map.get(s["id"], 0.0)
                paid = float(s["paid_amount"] or 0)
                profit = total - cost
                sum_total += total + discount
                sum_discount += discount
                sum_cost += cost
                sum_paid += paid
                sum_profit += profit
                profit_color = "#059669" if profit >= 0 else "#dc2626"
                d = format_currency(discount) if discount else "—"
                c = format_currency(cost) if cost else "—"
                p = format_currency(paid) if paid else "—"
                inv_no = s["invoice_number"] or ""
                if len(inv_no) > 12:
                    inv_no = ".." + inv_no[-10:]
                html += '<tr>'
                html += f'<td style="color:#64748b;font-size:8.5pt;">{method_ar}</td>'
                html += f'<td style="color:{profit_color};font-weight:700;">{format_currency(profit)}</td>'
                html += f'<td>{p}</td>'
                html += f'<td style="color:#78716c;">{c}</td>'
                html += f'<td style="color:#0d9488;">{d}</td>'
                html += f'<td style="color:#2563eb;font-weight:600;">{format_currency(total + discount)}</td>'
                html += f'<td>{s["user_name"] or ""}</td>'
                html += f'<td style="color:#475569;">{s["created_at"][:10]}</td>'
                html += f'<td style="font-size:7.5pt;direction:ltr;">{inv_no}</td>'
                html += f'<td style="color:#94a3b8;font-size:8.5pt;">{i}</td>'
                html += '</tr>'
            # Totals row
            prof_col = "#059669" if sum_profit >= 0 else "#dc2626"
            html += '<tr style="font-weight:800;background:#f1f5f9;">'
            html += f'<td style="color:#1e293b;font-size:9pt;">المجموع</td>'
            html += f'<td style="color:{prof_col};font-size:9pt;">{format_currency(sum_profit)}</td>'
            html += f'<td style="color:#0f172a;font-size:9pt;">{format_currency(sum_paid)}</td>'
            html += f'<td style="color:#78716c;font-size:9pt;">{format_currency(sum_cost)}</td>'
            html += f'<td style="color:#0d9488;font-size:9pt;">{format_currency(sum_discount)}</td>'
            html += f'<td style="color:#2563eb;font-size:9pt;">{format_currency(sum_total)}</td>'
            html += f'<td colspan="2" style="color:#475569;font-size:8pt;">—</td>'
            html += f'<td style="color:#64748b;font-size:8pt;">{len(sales_invoices)} فاتورة</td>'
            html += f'<td style="color:#94a3b8;font-size:8pt;">∑</td>'
            html += '</tr>'
        else:
            html += '<tr><td colspan="10">لا توجد مبيعات في هذه الفترة</td></tr>'
        html += '</table>'

        html += '<h2 class="section-break">📦 تفاصيل فواتير الشراء</h2>'
        html += '<table width="100%" cellspacing="0" cellpadding="0" class="table-data">'
        html += '<tr><th width="12%">الحالة</th><th width="14%">المدفوع</th><th width="14%">المبلغ</th><th width="20%">المورد</th><th width="24%">التاريخ</th><th width="16%">الفاتورة</th></tr>'
        if purchases_invoices:
            for p in purchases_invoices:
                status_ar = "مسدد" if p["status"] == "paid" else ("جزئي" if p["status"] == "partial" else "ذمة")
                html += f'<tr><td>{status_ar}</td><td>{format_currency(str(p["paid_amount"] or 0))}</td><td>{format_currency(str(p["total_amount"] or 0))}</td><td>{p["supplier_name"] or ""}</td><td>{p["created_at"][:19]}</td><td>{p["invoice_number"]}</td></tr>'
        else:
            html += '<tr><td colspan="6">لا توجد مشتريات في هذه الفترة</td></tr>'
        html += '</table>'

        html += '<h2 class="section-break">💸 سجل المصاريف</h2>'
        html += '<table width="100%" cellspacing="0" cellpadding="0" class="table-data">'
        html += '<tr><th width="14%">المبلغ</th><th width="20%">نوع المصروف</th><th width="22%">سحب من (التاريخ - المبلغ)</th><th width="16%">المستخدم</th><th width="28%">التاريخ</th></tr>'
        if expenses_list:
            sum_exp = 0.0
            for e in expenses_list:
                amt = float(e["amount"] or 0)
                sum_exp += amt
                srcs = exp_income_map.get(e["id"], [])
                if srcs:
                    src_parts = [f"{sr['income_date']} ({format_currency(sr['amount'])})" for sr in srcs]
                    src_text = ", ".join(src_parts)
                else:
                    src_text = e["income_date"] or "—"
                html += f'<tr><td>{format_currency(amt)}</td><td>{e["type_name"] or e["description"] or ""}</td><td style="font-size:7.5pt;color:#1e293b;">{src_text}</td><td>{e["user_name"] or "—"}</td><td>{e["expense_date"]}</td></tr>'
            html += f'<tr style="font-weight:800;background:#f1f5f9;"><td style="color:#2563eb;">{format_currency(sum_exp)}</td><td colspan="4" style="color:#1e293b;">المجموع</td></tr>'
        else:
            html += '<tr><td colspan="5">لا توجد مصاريف مسجلة في هذه الفترة</td></tr>'
        html += '</table>'

        html += '<h2 class="section-break">📋 الديون المستحقة للموردين</h2>'
        html += '<table width="100%" cellspacing="0" cellpadding="0" class="table-data">'
        html += '<tr><th width="15%">المتبقي</th><th width="20%">المدفوع</th><th width="20%">إجمالي الديون</th><th width="15%">عدد الفواتير</th><th width="30%">المورد</th></tr>'
        if supplier_debts:
            for d in supplier_debts:
                rem = float(d["remaining"] or 0)
                html += f'<tr><td style="color:#dc2626;font-weight:700;">{format_currency(rem)}</td><td style="color:#059669;">{format_currency(str(d["total_paid"] or 0))}</td><td style="color:#2563eb;">{format_currency(str(d["total_debt"] or 0))}</td><td>{d["invoice_count"]}</td><td style="font-weight:600;">{d["supplier_name"] or ""}</td></tr>'
        else:
            html += '<tr><td colspan="5">لا توجد ديون مستحقة للموردين في هذه الفترة</td></tr>'
        html += '</table>'

        html += '<h2 class="section-break">📊 مبيعات المواد مع المخزون</h2>'
        html += '<table width="100%" cellspacing="0" cellpadding="0" class="table-data">'
        html += '<tr><th width="15%">الاستحصال</th><th width="15%">المتبقي</th><th width="15%">المصروف</th><th width="15%">المخزون</th><th width="40%">اسم المادة</th></tr>'
        tot_stock = 0
        tot_sold = 0
        tot_remaining = 0
        tot_revenue = 0.0
        if product_sales_data:
            for it in product_sales_data:
                stock = int(it["stock_quantity"] or 0)
                sold = int(it["sold_qty"] or 0)
                remaining = max(stock - sold, 0)
                rev = float(it["total_sale"] or 0.0)
                tot_stock += stock
                tot_sold += sold
                tot_remaining += remaining
                tot_revenue += rev
                html += f'<tr><td style="color:#2563eb;">{format_currency(str(rev))}</td><td style="color:{"#059669" if remaining > 0 else "#dc2626"};font-weight:700;">{remaining}</td><td style="color:#0f766e;">{sold}</td><td style="color:#2563eb;">{stock}</td><td style="text-align:right;font-weight:600;">{it["name"]}</td></tr>'
        else:
            html += '<tr><td colspan="5">لا توجد مواد مسجلة</td></tr>'
        html += '</table>'
        html += '<table width="100%" cellspacing="0" cellpadding="0" class="table-data" style="margin-top:4px;">'
        html += '<tr>'
        html += f'<td width="15%" style="text-align:center;font-weight:bold;color:#2563eb;border:1px solid #cbd5e1;padding:5px 3px;">💰 {format_currency(str(tot_revenue))}</td>'
        html += f'<td width="15%" style="text-align:center;font-weight:bold;color:#059669;border:1px solid #cbd5e1;padding:5px 3px;">📥 {tot_remaining}</td>'
        html += f'<td width="15%" style="text-align:center;font-weight:bold;color:#0f766e;border:1px solid #cbd5e1;padding:5px 3px;">📤 {tot_sold}</td>'
        html += f'<td width="15%" style="text-align:center;font-weight:bold;color:#2563eb;border:1px solid #cbd5e1;padding:5px 3px;">📦 {tot_stock}</td>'
        html += '<td width="40%" style="text-align:center;font-weight:bold;color:#1e293b;border:1px solid #cbd5e1;padding:5px 3px;">الإجمالي</td>'
        html += '</tr></table>'

        html += f"""
            <div class="footer">
                نظام إدارة الصيدلية RTX - التقرير الشامل للفترة
            </div>
        </body>
        </html>
        """
        return html

    def _draw_sales_charts_images(self, d1, d2, total_cash, total_credit):
        # Build contiguous date list
        qdate1 = QDate.fromString(d1, "yyyy-MM-dd")
        qdate2 = QDate.fromString(d2, "yyyy-MM-dd")
        dates_list = []
        curr = qdate1
        while curr <= qdate2:
            dates_list.append(curr.toString("yyyy-MM-dd"))
            curr = curr.addDays(1)

        daily_vals = {d: 0.0 for d in dates_list}
        
        # Query sales grouped by day
        sales_by_day = self.db.fetchall("""
            SELECT date(created_at, 'localtime') as day, SUM(CAST(total_amount AS REAL)) as amount
            FROM sales
            WHERE date(created_at, 'localtime') BETWEEN ? AND ?
            GROUP BY day
        """, (d1, d2))
        
        for row in sales_by_day:
            day = row["day"]
            if day in daily_vals:
                daily_vals[day] = float(row["amount"] or 0.0)

        max_val = max(daily_vals.values()) if daily_vals else 0.0
        nice_max = 1000.0
        if max_val > 0:
            mag = 10 ** math.floor(math.log10(max_val))
            if mag > 0:
                ratio = max_val / mag
                if ratio <= 1.0: nice_ratio = 1.0
                elif ratio <= 2.0: nice_ratio = 2.0
                elif ratio <= 5.0: nice_ratio = 5.0
                else: nice_ratio = 10.0
                nice_max = nice_ratio * mag
            else:
                nice_max = max_val

        # ── 1. LINE CHART IMAGE ──
        line_img = QImage(700, 260, QImage.Format_ARGB32)
        line_img.fill(QColor("#ffffff"))
        painter = QPainter(line_img)
        painter.setRenderHint(QPainter.Antialiasing)

        margin_left = 65
        margin_right = 25
        margin_top = 35
        margin_bottom = 35
        width = 700 - margin_left - margin_right
        height = 260 - margin_top - margin_bottom

        # Draw Title
        painter.setPen(QColor("#1e293b"))
        painter.setFont(QFont("Segoe UI", 11, QFont.Bold))
        painter.drawText(QRectF(0, 5, 700, 25), Qt.AlignCenter, "المبيعات اليومية")

        # Draw Y-grid lines and labels
        painter.setFont(QFont("Segoe UI", 9))
        for i in range(4):
            val = (nice_max / 3) * i
            y = (margin_top + height) - (val / nice_max) * height
            if i > 0:
                pen_grid = QPen(QColor("#f1f5f9"), 1, Qt.SolidLine)
                painter.setPen(pen_grid)
                painter.drawLine(margin_left, int(y), margin_left + width, int(y))
            
            val_str = ""
            if val >= 1000000:
                val_str = f"{val/1000000:.1f}M".replace(".0", "")
            elif val >= 1000:
                val_str = f"{val/1000:.0f}K"
            else:
                val_str = f"{val:.0f}"
            
            painter.setPen(QColor("#64748b"))
            painter.drawText(5, int(y - 8), margin_left - 10, 16, Qt.AlignRight | Qt.AlignVCenter, val_str)

        # Plot coordinates
        points = []
        n = len(dates_list)
        for idx, date_str in enumerate(dates_list):
            val = daily_vals[date_str]
            x = margin_left + (idx / (n - 1) * width) if n > 1 else margin_left + width/2
            y = (margin_top + height) - (val / nice_max) * height
            points.append(QPointF(x, y))

        # Fill path
        if len(points) > 1:
            fill_path = QPainterPath()
            fill_path.moveTo(points[0].x(), margin_top + height)
            for pt in points:
                fill_path.lineTo(pt)
            fill_path.lineTo(points[-1].x(), margin_top + height)
            fill_path.closeSubpath()
            
            grad = QLinearGradient(0, margin_top, 0, margin_top + height)
            grad.setColorAt(0, QColor(59, 130, 246, 60))
            grad.setColorAt(1, QColor(59, 130, 246, 0))
            painter.fillPath(fill_path, QBrush(grad))

        # Line path
        if len(points) > 1:
            path = QPainterPath()
            path.moveTo(points[0])
            for pt in points:
                path.lineTo(pt)
            pen_line = QPen(QColor("#3b82f6"), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen_line)
            painter.drawPath(path)

        # Dot markers and X-axis labels
        sample_step = max(1, n // 6)
        months_ar = {
            1: "مايو" if qdate1.month() == 5 else "يناير",
            2: "فبراير", 3: "مارس", 4: "أبريل", 5: "مايو", 6: "يونيو",
            7: "يوليو", 8: "أغسطس", 9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر"
        }
        for idx, pt in enumerate(points):
            painter.setPen(QPen(QColor("#3b82f6"), 1))
            painter.setBrush(QBrush(QColor("#ffffff")))
            painter.drawEllipse(pt, 3, 3)
            
            if idx % sample_step == 0 or idx == n - 1:
                qdate = QDate.fromString(dates_list[idx], "yyyy-MM-dd")
                month_name = months_ar.get(qdate.month(), "")
                lbl_text = f"{qdate.day()} {month_name}"
                painter.setPen(QColor("#64748b"))
                rect = QRectF(pt.x() - 40, margin_top + height + 5, 80, 20)
                painter.drawText(rect, Qt.AlignCenter, lbl_text)
                
        painter.end()

        # ── 2. DOUGHNUT CHART IMAGE ──
        donut_img = QImage(300, 260, QImage.Format_ARGB32)
        donut_img.fill(QColor("#ffffff"))
        painter = QPainter(donut_img)
        painter.setRenderHint(QPainter.Antialiasing)

        painter.setPen(QColor("#1e293b"))
        painter.setFont(QFont("Segoe UI", 11, QFont.Bold))
        painter.drawText(QRectF(0, 5, 300, 25), Qt.AlignCenter, "توزيع المبيعات")

        cx, cy = 100, 135
        r_out = 70
        r_in = 44

        total_vals = total_cash + total_credit
        if total_vals <= 0:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor("#e2e8f0")))
            painter.drawEllipse(QPointF(cx, cy), r_out, r_out)
            painter.setBrush(QBrush(QColor("#ffffff")))
            painter.drawEllipse(QPointF(cx, cy), r_in, r_in)
            
            painter.setFont(QFont("Segoe UI", 9))
            painter.setPen(QColor("#64748b"))
            painter.drawText(195, 110, 100, 20, Qt.AlignLeft | Qt.AlignVCenter, "0% نقدي")
            painter.drawText(195, 140, 100, 20, Qt.AlignLeft | Qt.AlignVCenter, "0% آجل")
        else:
            p_cash = total_cash / total_vals
            p_credit = total_credit / total_vals
            
            angle_cash = int(p_cash * 360 * 16)
            angle_credit = int(p_credit * 360 * 16)
            start_angle = 90 * 16
            
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor("#3b82f6")))
            painter.drawPie(cx - r_out, cy - r_out, r_out * 2, r_out * 2, start_angle, angle_cash)
            
            painter.setBrush(QBrush(QColor("#93c5fd")))
            painter.drawPie(cx - r_out, cy - r_out, r_out * 2, r_out * 2, start_angle + angle_cash, angle_credit)
            
            painter.setBrush(QBrush(QColor("#ffffff")))
            painter.drawEllipse(QPointF(cx, cy), r_in, r_in)

            pct_cash = round(p_cash * 100)
            pct_credit = 100 - pct_cash
            
            # Cash Legend
            painter.setBrush(QBrush(QColor("#3b82f6")))
            painter.drawRoundedRect(QRectF(195, 105, 11, 11), 3, 3)
            painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
            painter.setPen(QColor("#1e293b"))
            painter.drawText(212, 95, 80, 18, Qt.AlignLeft | Qt.AlignVCenter, f"{pct_cash}%")
            painter.setFont(QFont("Segoe UI", 8))
            painter.setPen(QColor("#64748b"))
            painter.drawText(212, 112, 80, 16, Qt.AlignLeft | Qt.AlignVCenter, "نقدي")

            # Credit Legend
            painter.setBrush(QBrush(QColor("#93c5fd")))
            painter.drawRoundedRect(QRectF(195, 155, 11, 11), 3, 3)
            painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
            painter.setPen(QColor("#1e293b"))
            painter.drawText(212, 145, 80, 18, Qt.AlignLeft | Qt.AlignVCenter, f"{pct_credit}%")
            painter.setFont(QFont("Segoe UI", 8))
            painter.setPen(QColor("#64748b"))
            painter.drawText(212, 162, 80, 16, Qt.AlignLeft | Qt.AlignVCenter, "آجل")
            
        painter.end()
        return line_img, donut_img

    def _generate_sales_charts_base64(self, d1, d2, total_cash, total_credit):
        line_img, donut_img = self._draw_sales_charts_images(d1, d2, total_cash, total_credit)
        
        # Convert to Base64
        ba_line = QByteArray()
        buf_line = QBuffer(ba_line)
        buf_line.open(QIODevice.WriteOnly)
        line_img.save(buf_line, "PNG")
        b64_line = base64.b64encode(ba_line.data()).decode("utf-8")
        
        ba_donut = QByteArray()
        buf_donut = QBuffer(ba_donut)
        buf_donut.open(QIODevice.WriteOnly)
        donut_img.save(buf_donut, "PNG")
        b64_donut = base64.b64encode(ba_donut.data()).decode("utf-8")

        return b64_line, b64_donut

    def _generate_sales_list_html(self):
        d1 = self.date_from.date().toPyDate().strftime("%Y-%m-%d")
        d2 = self.date_to.date().toPyDate().strftime("%Y-%m-%d")
        ph_name = self._get_pharmacy_name()

        # 1. Query KPI statistics
        r_sales = self.db.fetchone("SELECT SUM(CAST(total_amount AS REAL)) FROM sales WHERE date(created_at, 'localtime') BETWEEN ? AND ?", (d1, d2))
        total_sales = r_sales[0] if r_sales and r_sales[0] is not None else 0.0

        r_upfront = self.db.fetchone("SELECT SUM(CAST(paid_amount AS REAL)) FROM sales WHERE date(created_at, 'localtime') BETWEEN ? AND ?", (d1, d2))
        total_upfront = r_upfront[0] if r_upfront and r_upfront[0] is not None else 0.0
        
        r_payments = self.db.fetchone("SELECT SUM(CAST(amount AS REAL)) FROM debt_payments WHERE date(payment_date, 'localtime') BETWEEN ? AND ?", (d1, d2))
        total_payments = r_payments[0] if r_payments and r_payments[0] is not None else 0.0
        total_cash = total_upfront + total_payments

        r_credit = self.db.fetchone("SELECT SUM(CAST(total_amount AS REAL) - CAST(paid_amount AS REAL)) FROM sales WHERE date(created_at, 'localtime') BETWEEN ? AND ? AND payment_method = 'credit'", (d1, d2))
        total_credit = r_credit[0] if r_credit and r_credit[0] is not None else 0.0

        r_disc = self.db.fetchone("SELECT SUM(CAST(discount AS REAL)) FROM sales WHERE date(created_at, 'localtime') BETWEEN ? AND ?", (d1, d2))
        total_discount = r_disc[0] if r_disc and r_disc[0] is not None else 0.0

        # Generate base64 chart images
        b64_line, b64_donut = self._generate_sales_charts_base64(d1, d2, total_cash, total_credit)

        # 2. Fetch sales invoices
        invoices = self.db.fetchall("""
            SELECT s.*, u.full_name as user_name, c.name as customer_name
            FROM sales s
            LEFT JOIN users u ON s.user_id = u.id
            LEFT JOIN customers c ON s.customer_id = c.id
            WHERE date(s.created_at, 'localtime') BETWEEN ? AND ?
            ORDER BY s.created_at DESC
        """, (d1, d2))

        html = f"""
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                @page {{ size: A4 portrait; }}
                body {{
                    font-family: "Segoe UI", "Tahoma", Arial, sans-serif;
                    color: #0f172a;
                    margin: 0;
                    padding: 0;
                    font-size: 11pt;
                    line-height: 1.4;
                    background-color: #ffffff;
                }}
                .title {{
                    text-align: center;
                    font-size: 20pt;
                    font-weight: 800;
                    color: #0f172a;
                    margin: 0 0 8px 0;
                }}
                .filter-bar {{
                    text-align: center;
                    margin-bottom: 15px;
                }}
                .filter-badge {{
                    background-color: #f8fafc;
                    border: 1px solid #e2e8f0;
                    border-radius: 6px;
                    padding: 6px 14px;
                    font-size: 9.5pt;
                    color: #475569;
                    display: inline-block;
                }}
                /* 4-Column stats grid */
                .stats-table {{
                    width: 100%;
                    border-collapse: separate;
                    border-spacing: 6px 0;
                    margin-bottom: 12px;
                }}
                .stat-card {{
                    background-color: #ffffff;
                    border: 1px solid #e2e8f0;
                    border-radius: 8px;
                    padding: 10px;
                    text-align: center;
                }}
                .stat-title {{
                    font-size: 9.5pt;
                    color: #64748b;
                    margin-bottom: 4px;
                    font-weight: 600;
                }}
                .stat-val {{
                    font-size: 15pt;
                    font-weight: 800;
                }}
                .color-total {{ color: #10b981; }}
                .color-cash {{ color: #1e3a8a; }}
                .color-credit {{ color: #2563eb; }}
                .color-discount {{ color: #10b981; }}
                
                .stat-unit {{
                    font-size: 8.5pt;
                    color: #64748b;
                    margin-top: 2px;
                    font-weight: normal;
                }}
                /* Charts Row */
                .charts-table {{
                    width: 100%;
                    border-collapse: separate;
                    border-spacing: 6px 0;
                    margin-bottom: 12px;
                }}
                .chart-container {{
                    background-color: #ffffff;
                    border: 1px solid #e2e8f0;
                    border-radius: 8px;
                    text-align: center;
                    vertical-align: top;
                }}
                .chart-img {{
                    display: block;
                    margin: 0 auto;
                }}
                /* Invoices Table */
                .table-title {{
                    font-size: 11pt;
                    font-weight: bold;
                    color: #0f172a;
                    margin: 8px 12px 6px 0;
                }}
                .data-table {{
                    width: 100%;
                    margin-bottom: 10px;
                    border-collapse: collapse;
                }}
                .data-table th {{
                    background-color: #f8fafc;
                    color: #475569;
                    font-size: 9.5pt;
                    font-weight: 700;
                    border-bottom: 2px solid #e2e8f0;
                    padding: 7px 10px;
                    text-align: center;
                }}
                .data-table td {{
                    padding: 7px 10px;
                    border-bottom: 1px solid #f1f5f9;
                    font-size: 9pt;
                    text-align: center;
                    color: #334155;
                }}
                .data-table tr:nth-child(even) {{
                    background-color: #fafbfc;
                }}
                .show-more {{
                    font-size: 8.5pt;
                    color: #2563eb;
                    font-weight: 600;
                    margin: 6px 12px 0 0;
                    text-align: right;
                }}
            </style>
        </head>
        <body>
            <div class="title">1. ملخص المبيعات</div>
            
            <div class="filter-bar">
                <span class="filter-badge">
                    تصفية &nbsp; | &nbsp; من {d1} إلى {d2}
                </span>
            </div>

            <table class="stats-table">
                <tr>
                    <td width="25%">
                        <div class="stat-card">
                            <div class="stat-title">إجمالي المبيعات</div>
                            <div class="stat-val color-total">{format_currency(str(total_sales))}</div>
                            <div class="stat-unit">د.ع</div>
                        </div>
                    </td>
                    <td width="25%">
                        <div class="stat-card">
                            <div class="stat-title">نقدي</div>
                            <div class="stat-val color-cash">{format_currency(str(total_cash))}</div>
                            <div class="stat-unit">د.ع</div>
                        </div>
                    </td>
                    <td width="25%">
                        <div class="stat-card">
                            <div class="stat-title">آجل</div>
                            <div class="stat-val color-credit">{format_currency(str(total_credit))}</div>
                            <div class="stat-unit">د.ع</div>
                        </div>
                    </td>
                    <td width="25%">
                        <div class="stat-card">
                            <div class="stat-title">الخصومات</div>
                            <div class="stat-val color-discount">{format_currency(str(total_discount))}</div>
                            <div class="stat-unit">د.ع</div>
                        </div>
                    </td>
                </tr>
            </table>

            <table class="charts-table">
                <tr>
                    <td width="67%" class="chart-container">
                        <img class="chart-img" width="100%" src="data:image/png;base64,{b64_line}" />
                    </td>
                    <td width="33%" class="chart-container">
                        <img class="chart-img" width="100%" src="data:image/png;base64,{b64_donut}" />
                    </td>
                </tr>
            </table>

            <div class="table-title">أحدث الفواتير</div>
            <table class="data-table">
                <thead>
                    <tr>
                        <th width="20%">رقم الفاتورة</th>
                        <th width="15%">نوع الدفع</th>
                        <th width="25%">الزبون</th>
                        <th width="20%">التاريخ</th>
                        <th width="20%">القيمة</th>
                    </tr>
                </thead>
                <tbody>
        """

        # Limit to latest 10 invoices in the printed summary to fit perfectly on A4 landscape page
        display_invoices = invoices[:10]
        if display_invoices:
            for s in display_invoices:
                method_ar = "نقدي" if s["payment_method"] == "cash" else "آجل"
                cust_name = s["customer_name"] or "زبون عام"
                html += f"""
                <tr>
                    <td>{s["invoice_number"]}</td>
                    <td>{method_ar}</td>
                    <td>{cust_name}</td>
                    <td>{s["created_at"][:10]}</td>
                    <td style="font-weight: 700; color: #0f172a;">{format_currency(s["total_amount"])} د.ع</td>
                </tr>
                """
        else:
            html += '<tr><td colspan="5">لا توجد مبيعات في هذه الفترة</td></tr>'

        html += """
                </tbody>
            </table>
            <div class="show-more">عرض المزيد</div>
        </body>
        </html>
        """
        return html

    def _generate_purchases_list_html(self):
        d1 = self.date_from.date().toPyDate().strftime("%Y-%m-%d")
        d2 = self.date_to.date().toPyDate().strftime("%Y-%m-%d")
        ph_name = self._get_pharmacy_name()
        
        purchases = self.db.fetchall("""
            SELECT sd.*, s.name as supplier_name
            FROM supplier_debts sd
            LEFT JOIN suppliers s ON sd.supplier_id = s.id
            WHERE date(sd.created_at, 'localtime') BETWEEN ? AND ?
            ORDER BY sd.created_at DESC
        """, (d1, d2))
        
        html = f"""
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                @page {{ size: A4 portrait; }}
                body {{ font-family: "Segoe UI", Tahoma, Arial, sans-serif; color: #1e293b; margin: 0; padding: 0; font-size: 13pt; line-height: 1.6; }}
                .header {{ border-bottom: 3px solid #b8860b; margin-bottom: 20px; padding-bottom: 16px; }}
                .header h1 {{ margin: 0; font-size: 26pt; color: #0f172a; font-weight: 800; letter-spacing: 3px; }}
                .date-range {{ margin: 6px 0 16px 0; font-size: 13pt; color: #78716c; font-family: "Segoe UI", "Calibri", Arial, sans-serif; font-weight: 500; letter-spacing: 1px; }}
                table {{ width: 100%; border-collapse: collapse; margin-bottom: 10px; }}
                .table-data th {{ background: #f1f5f9; color: #1e293b; padding: 7px 3px; border: 1px solid #cbd5e1; text-align: center; font-size: 9pt; font-weight: 700; }}
                .table-data td {{ padding: 4px 3px; border: 1px solid #e2e8f0; text-align: center; font-size: 9pt; }}
                .footer {{ text-align: center; font-size: 9pt; color: #94a3b8; border-top: 1px solid #e2e8f0; padding-top: 5px; margin-top: 12px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>RTX</h1>
            </div>
            <p class="date-range" style="margin-bottom: 10px;">{d1} — {d2}</p>
            <table width="100%" cellspacing="0" cellpadding="0" class="table-data">
                <tr>
                    <th>رقم الفاتورة</th>
                    <th>التاريخ والوقت</th>
                    <th>المذخر / المورد</th>
                    <th>الإجمالي</th>
                    <th>المدفوع</th>
                    <th>الحالة</th>
                </tr>
        """
        if purchases:
            for p in purchases:
                status_ar = "مسدد" if p["status"] == "paid" else ("جزئي" if p["status"] == "partial" else "ذمة")
                html += f'<tr><td>{p["invoice_number"]}</td><td>{p["created_at"][:19]}</td><td>{p["supplier_name"] or ""}</td><td>{format_currency(str(p["total_amount"] or 0))}</td><td>{format_currency(str(p["paid_amount"] or 0))}</td><td>{status_ar}</td></tr>'
        else:
            html += '<tr><td colspan="6">لا توجد مشتريات في هذه الفترة</td></tr>'
        html += '</table>'
        html += '</body></html>'
        return html

    def _generate_dispensed_html(self):
        d1 = self.date_from.date().toPyDate().strftime("%Y-%m-%d")
        d2 = self.date_to.date().toPyDate().strftime("%Y-%m-%d")
        ph_name = self._get_pharmacy_name()

        dispensed_items = self.db.fetchall("""
            SELECT p.barcode, p.name as product_name, SUM(si.quantity) as total_qty, 
                   CAST(p.purchase_price AS REAL) as unit_cost, 
                   SUM(si.quantity * CAST(p.purchase_price AS REAL)) as total_cost,
                   CAST(si.unit_price AS REAL) as unit_sale,
                   SUM(si.total_price) as total_sale
            FROM sale_items si
            JOIN sales s ON si.sale_id = s.id
            JOIN products p ON si.product_id = p.id
            WHERE date(s.created_at, 'localtime') BETWEEN ? AND ?
            GROUP BY si.product_id
            ORDER BY total_qty DESC
        """, (d1, d2))

        disp_tot_cost = 0.0
        disp_tot_sale = 0.0
        disp_tot_profit = 0.0

        html = f"""
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                @page {{ size: A4 portrait; }}
                body {{ font-family: "Segoe UI", Tahoma, Arial, sans-serif; color: #1e293b; margin: 0; padding: 0; font-size: 13pt; line-height: 1.6; }}
                .header {{ border-bottom: 3px solid #b8860b; margin-bottom: 20px; padding-bottom: 16px; }}
                .header h1 {{ margin: 0; font-size: 26pt; color: #0f172a; font-weight: 800; letter-spacing: 3px; }}
                .date-range {{ margin: 6px 0 16px 0; font-size: 13pt; color: #78716c; font-family: "Segoe UI", "Calibri", Arial, sans-serif; font-weight: 500; letter-spacing: 1px; }}
                table {{ width: 100%; border-collapse: collapse; margin-bottom: 10px; }}
                .table-data th {{ background: #f1f5f9; color: #1e293b; padding: 7px 3px; border: 1px solid #cbd5e1; text-align: center; font-size: 9pt; font-weight: 700; }}
                .table-data td {{ padding: 4px 3px; border: 1px solid #e2e8f0; text-align: center; font-size: 9pt; }}
                .totals-box {{ background: #f3f4f6; padding: 8px 10px; border: 1px solid #cbd5e1; margin-top: 8px; }}
                .footer {{ text-align: center; font-size: 9pt; color: #94a3b8; border-top: 1px solid #e2e8f0; padding-top: 5px; margin-top: 12px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>RTX</h1>
            </div>
            <p class="date-range" style="margin-bottom: 10px;">{d1} — {d2}</p>
            <table width="100%" cellspacing="0" cellpadding="0" class="table-data">
                <tr>
                    <th>الباركود</th>
                    <th>اسم المادة</th>
                    <th>الكمية المباعة</th>
                    <th>سعر الكلفة (للوحدة)</th>
                    <th>إجمالي الكلفة (رأس المال)</th>
                    <th>سعر البيع (المتوسط)</th>
                    <th>إجمالي المبيعات</th>
                    <th>صافي الربح</th>
                </tr>
        """
        if dispensed_items:
            for it in dispensed_items:
                qty = int(it["total_qty"] or 0)
                u_cost = float(it["unit_cost"] or 0.0)
                t_cost = float(it["total_cost"] or 0.0)
                t_sale = float(it["total_sale"] or 0.0)
                u_sale = t_sale / qty if qty > 0 else 0.0
                profit = t_sale - t_cost

                disp_tot_cost += t_cost
                disp_tot_sale += t_sale
                disp_tot_profit += profit

                html += f"""
                <tr>
                    <td>{it["barcode"]}</td>
                    <td style="text-align: right;">{it["product_name"]}</td>
                    <td>{qty}</td>
                    <td>{format_currency(str(u_cost))}</td>
                    <td>{format_currency(str(t_cost))}</td>
                    <td>{format_currency(str(u_sale))}</td>
                    <td>{format_currency(str(t_sale))}</td>
                    <td>{format_currency(str(profit))}</td>
                </tr>
                """
        else:
            html += '<tr><td colspan="8">لا توجد مواد مصروفة في هذه الفترة</td></tr>'

        html += f"""
            </table>
            <div class="totals-box">
                <table style="width: 100%; border: none; margin: 0;">
                    <tr>
                        <td style="border: none; text-align: right; font-weight: bold;">إجمالي كلفة العلاج المصروف (رأس المال): {format_currency(str(disp_tot_cost))} د.ع</td>
                        <td style="border: none; text-align: center; font-weight: bold;">إجمالي قيمة المبيعات: {format_currency(str(disp_tot_sale))} د.ع</td>
                        <td style="border: none; text-align: left; font-weight: bold; color: #059669;">صافي الربح المحقق: {format_currency(str(disp_tot_profit))} د.ع</td>
                    </tr>
                </table>
            </div>
            <div class="footer">
                نظام إدارة الصيدلية RTX - تقرير رأس المال المصروف
            </div>
        </body>
        </html>
        """
        return html

    def _generate_stock_html(self):
        ph_name = self._get_pharmacy_name()

        stock_db_items = self.db.fetchall("""
            SELECT barcode, name, expiry_date, stock_quantity, 
                   CAST(purchase_price AS REAL) as purchase_price, 
                   CAST(sale_price AS REAL) as sale_price
            FROM products
            WHERE stock_quantity > 0 AND is_active = 1
            ORDER BY name ASC
        """)

        stock_tot_cost = 0.0
        stock_tot_sale = 0.0
        stock_tot_profit = 0.0

        html = f"""
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                @page {{ size: A4 portrait; }}
                body {{ font-family: "Segoe UI", Tahoma, Arial, sans-serif; color: #1e293b; margin: 0; padding: 0; font-size: 13pt; line-height: 1.6; }}
                .header {{ border-bottom: 3px solid #b8860b; margin-bottom: 20px; padding-bottom: 16px; }}
                .header h1 {{ margin: 0; font-size: 26pt; color: #0f172a; font-weight: 800; letter-spacing: 3px; }}
                .date-range {{ margin: 6px 0 16px 0; font-size: 13pt; color: #78716c; font-family: "Segoe UI", "Calibri", Arial, sans-serif; font-weight: 500; letter-spacing: 1px; }}
                table {{ width: 100%; border-collapse: collapse; margin-bottom: 10px; }}
                .table-data th {{ background: #f1f5f9; color: #1e293b; padding: 7px 3px; border: 1px solid #cbd5e1; text-align: center; font-size: 9pt; font-weight: 700; }}
                .table-data td {{ padding: 4px 3px; border: 1px solid #e2e8f0; text-align: center; font-size: 9pt; }}
                .totals-box {{ background: #f3f4f6; padding: 8px 10px; border: 1px solid #cbd5e1; margin-top: 8px; }}
                .footer {{ text-align: center; font-size: 9pt; color: #94a3b8; border-top: 1px solid #e2e8f0; padding-top: 5px; margin-top: 12px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>RTX</h1>
            </div>
            <table width="100%" cellspacing="0" cellpadding="0" class="table-data">
                <tr>
                    <th>الباركود</th>
                    <th>اسم المادة</th>
                    <th>تاريخ الانتهاء</th>
                    <th>الكمية المتوفرة</th>
                    <th>سعر الكلفة (الشراء)</th>
                    <th>إجمالي الكلفة (رأس المال)</th>
                    <th>سعر البيع</th>
                    <th>إجمالي القيمة البيعية</th>
                </tr>
        """
        if stock_db_items:
            for it in stock_db_items:
                qty = int(it["stock_quantity"] or 0)
                u_cost = float(it["purchase_price"] or 0.0)
                t_cost = qty * u_cost
                u_sale = float(it["sale_price"] or 0.0)
                t_sale = qty * u_sale
                profit = t_sale - t_cost

                stock_tot_cost += t_cost
                stock_tot_sale += t_sale
                stock_tot_profit += profit

                html += f"""
                <tr>
                    <td>{it["barcode"]}</td>
                    <td style="text-align: right;">{it["name"]}</td>
                    <td>{it["expiry_date"] or "غير محدد"}</td>
                    <td>{qty}</td>
                    <td>{format_currency(str(u_cost))}</td>
                    <td>{format_currency(str(t_cost))}</td>
                    <td>{format_currency(str(u_sale))}</td>
                    <td>{format_currency(str(t_sale))}</td>
                </tr>
                """
        else:
            html += '<tr><td colspan="8">المخزن فارغ حالياً!</td></tr>'

        html += f"""
            </table>
            <div class="totals-box">
                <table style="width: 100%; border: none; margin: 0;">
                    <tr>
                        <td style="border: none; text-align: right; font-weight: bold; color: #0f766e;">إجمالي رأس مال المخزن: {format_currency(str(stock_tot_cost))} د.ع</td>
                        <td style="border: none; text-align: center; font-weight: bold;">إجمالي القيمة البيعية المتوقعة: {format_currency(str(stock_tot_sale))} د.ع</td>
                        <td style="border: none; text-align: left; font-weight: bold; color: #059669;">الأرباح المتوقعة عند التصفية: {format_currency(str(stock_tot_profit))} د.ع</td>
                    </tr>
                </table>
            </div>
            <div class="footer">
                نظام إدارة الصيدلية RTX - تقرير قيمة رأس المال بالمخزن
            </div>
        </body>
        </html>
        """
        return html
