import sys
import os
import calendar
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QDateEdit, QDialog, QFrame, QGraphicsDropShadowEffect,
    QStackedWidget, QLineEdit, QDoubleSpinBox, QFormLayout, QFileDialog,
    QMessageBox, QSplitter, QGridLayout, QComboBox
)
from PyQt5.QtCore import Qt, QDate, QLocale
from PyQt5.QtGui import QColor, QBrush, QFont, QPainter, QLinearGradient
from PyQt5.QtPrintSupport import QPrintDialog, QPrinter
from PyQt5.QtGui import QTextDocument

from database.connection import DatabaseManager
from utils.decimal_handler import format_currency, to_decimal, from_decimal, DECIMAL_ZERO
from utils.modern_msgbox import ModernMessageBox as QMessageBox

# ── style constants ──
_BG    = "#0f172a"
_CARD  = "#1e293b"
_BORD  = "#334155"
_GREEN = "#34d399"  # Brighter emerald green
_BLUE  = "#38bdf8"  # Sky blue
_RED   = "#f87171"  # Coral red
_AMBER = "#fbbf24"  # Warm amber
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
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = DatabaseManager()
        self._selected_supplier_name = None
        self.setWindowTitle("تسجيل مصروف جديد")
        self.setMinimumSize(560, 500)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ─── Content inside a padded frame ───
        content = QVBoxLayout()
        content.setContentsMargins(28, 22, 28, 18)
        content.setSpacing(16)

        # Header
        hdr = QHBoxLayout()
        hdr.addWidget(_lbl("💸 تسجيل مصروف جديد", "#ec4899", 22, True))
        hdr.addStretch()
        content.addLayout(hdr)

        # Separator
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background:#334155")
        content.addWidget(sep)

        # Description — separate line edit + selection buttons
        content.addWidget(_lbl("البيان", "#cbd5e1", 17, True))
        desc_row = QHBoxLayout()
        desc_row.setSpacing(8)

        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("اكتب بيان المصروف...")
        self.desc_input.setAlignment(Qt.AlignRight)
        self.desc_input.setStyleSheet("""
            QLineEdit{background:#0f172a;color:#ffffff;border:2px solid #334155;
                      border-radius:8px;padding:8px 14px;font-size:20px}
            QLineEdit:focus{border-color:#ec4899}
        """)
        self.desc_input.setFixedHeight(56)
        desc_row.addWidget(self.desc_input, 1)

        # Populate previous descriptions
        desc_list = []
        for row in self.db.fetchall(
            "SELECT DISTINCT description FROM expenses WHERE description IS NOT NULL AND description != '' ORDER BY description ASC"
        ):
            desc_list.append(row["description"])
        self._supplier_map = {}
        for s in self.db.fetchall("SELECT id, name FROM suppliers ORDER BY name"):
            pending = self.db.fetchall(
                "SELECT id, remaining_amount FROM supplier_debts WHERE supplier_id = ? AND status != 'paid' ORDER BY created_at DESC",
                (s["id"],)
            )
            if pending:
                total_remaining = sum(float(p["remaining_amount"]) for p in pending)
                label = f"تسديد للمورد: {s['name']} (المتبقي: {total_remaining:,.0f})"
                self._supplier_map[label] = {"supplier_id": s["id"], "debts": pending}
                desc_list.append(label)

        self._desc_list = desc_list
        self.btn_prev = QPushButton("📋")
        self.btn_prev.setToolTip("اختيار من البيانات السابقة")
        self.btn_prev.setFixedSize(56, 56)
        self.btn_prev.setStyleSheet("""
            QPushButton{background:#1e293b;color:#f1f5f9;border:2px solid #334155;
                       border-radius:8px;font-size:22px}
            QPushButton:hover{background:#334155;border-color:#ec4899}
            QPushButton:pressed{background:#0f172a}
        """)
        self.btn_prev.clicked.connect(self._show_desc_popup)
        desc_row.addWidget(self.btn_prev)

        content.addLayout(desc_row)

        # Supplier info banner
        self._debt_info = QFrame()
        self._debt_info.setStyleSheet("QFrame{background:#78350f20;border:1px solid #f59e0b40;border-radius:6px}")
        di = QHBoxLayout(self._debt_info)
        di.setContentsMargins(10, 6, 10, 6)
        self._debt_label = QLabel("")
        self._debt_label.setStyleSheet("font-size:13px;color:#fbbf24;background:transparent")
        di.addWidget(self._debt_label)
        self._debt_info.setVisible(False)
        content.addWidget(self._debt_info)
        # Amount + Date side by side
        ad = QHBoxLayout()
        ad.setSpacing(12)

        amt = QVBoxLayout()
        amt.setSpacing(4)
        amt.addWidget(_lbl("المبلغ", "#cbd5e1", 16, True))
        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(0, 999999999)
        self.amount_spin.setDecimals(2)
        self.amount_spin.setSingleStep(1000)
        self.amount_spin.setSuffix(" د.ع")
        self.amount_spin.setAlignment(Qt.AlignRight)
        self.amount_spin.setLocale(QLocale(QLocale.English, QLocale.UnitedStates))
        self.amount_spin.setGroupSeparatorShown(True)
        self.amount_spin.setStyleSheet("""
            QDoubleSpinBox{background:#0f172a;color:#fff;border:2px solid #334155;
                          border-radius:8px;padding:8px 14px;font-size:22px;font-weight:700}
            QDoubleSpinBox:focus{border-color:#ec4899}
        """)
        self.amount_spin.setFixedHeight(56)
        amt.addWidget(self.amount_spin)
        ad.addLayout(amt)

        dt = QVBoxLayout()
        dt.setSpacing(4)
        dt.addWidget(_lbl("التاريخ", "#cbd5e1", 16, True))
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setDate(QDate.currentDate())
        el = QLocale(QLocale.English, QLocale.UnitedStates)
        self.date_edit.setLocale(el)
        if self.date_edit.calendarWidget():
            self.date_edit.calendarWidget().setLocale(el)
        self.date_edit.setStyleSheet("""
            QDateEdit{background:#0f172a;color:#fff;border:2px solid #334155;
                     border-radius:8px;padding:8px 40px 8px 14px;font-size:20px}
            QDateEdit:focus{border-color:#ec4899}
            QDateEdit::drop-down{subcontrol-origin:padding;subcontrol-position:left;
                      width:38px;border:none;border-radius:6px}
            QDateEdit::down-arrow{image:none;width:0;height:0;
                      border-left:7px solid transparent;border-right:7px solid transparent;
                      border-top:9px solid #cbd5e1}
        """)
        self.date_edit.setFixedHeight(56)
        dt.addWidget(self.date_edit)
        ad.addLayout(dt)
        content.addLayout(ad)

        root.addLayout(content)
        root.addStretch()

        # ─── Footer buttons ───
        footer = QFrame()
        footer.setStyleSheet("QFrame{background:#0c1220;border-top:1px solid #1e293b}")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(24, 12, 24, 12)

        self.btn_cancel = QPushButton("إلغاء")
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.setStyleSheet("""
            QPushButton{background:#1e293b;color:#94a3b8;font-weight:700;font-size:15px;
                       border:none;border-radius:8px;padding:12px 28px;min-width:90px}
            QPushButton:hover{background:#334155;color:#fff}
        """)
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_save = QPushButton("💾 حفظ المصروف")
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.setStyleSheet("""
            QPushButton{background:#ec4899;color:#fff;font-weight:700;font-size:16px;
                       border:none;border-radius:8px;padding:12px 32px}
            QPushButton:hover{background:#db2777}
        """)
        self.btn_save.clicked.connect(self._save_expense)

        fl.addStretch()
        fl.addWidget(self.btn_cancel)
        fl.addWidget(self.btn_save)
        footer.setLayout(fl)
        root.addWidget(footer)

        self.setStyleSheet("""
            QDialog{background-color:#0f172a;border:1.5px solid #334155;border-radius:12px}
            QLabel{color:#f1f5f9}
        """)

    def _show_desc_popup(self):
        from PyQt5.QtWidgets import QMenu
        if not self._desc_list:
            QMessageBox.information(self, "تنبيه", "لا توجد بيانات سابقة")
            return
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu{background:#ffffff;color:#1e293b;border:2px solid #334155;
                  border-radius:8px;padding:6px;font-size:16px}
            QMenu::item{padding:10px 18px;min-height:32px;border-radius:4px}
            QMenu::item:selected{background:#ec4899;color:#ffffff}
        """)
        for text in self._desc_list:
            action = menu.addAction(text)
            action.setData(text)
        chosen = menu.exec_(self.btn_prev.mapToGlobal(
            self.btn_prev.rect().bottomLeft()
        ))
        if chosen:
            text = chosen.data()
            self.desc_input.setText(text)
            if text in self._supplier_map:
                info = self._supplier_map[text]
                debts = info["debts"]
                self._selected_supplier_name = text
                if debts:
                    total_remaining = sum(float(d["remaining_amount"]) for d in debts)
                    self._debt_label.setText(f"سيتم تسديد {total_remaining:,.0f} د.ع من دين المورد")
                    self._debt_info.setVisible(True)
            else:
                self._selected_supplier_name = None
                self._debt_info.setVisible(False)

    def _save_expense(self):
        from controllers.supplier_debt_controller import SupplierDebtController

        desc = self.desc_input.text().strip()
        amount = self.amount_spin.value()
        exp_date = self.date_edit.date().toString("yyyy-MM-dd")
        if not desc:
            QMessageBox.warning(self, "تنبيه", "يرجى إدخال بيان المصروف")
            return
        if amount <= 0:
            QMessageBox.warning(self, "تنبيه", "يرجى إدخال مبلغ صحيح")
            return
        try:
            # Always save as expense
            self.db.execute(
                "INSERT INTO expenses (amount, description, expense_date) VALUES (?, ?, ?)",
                (str(amount), desc, exp_date),
            )

            # If supplier selected, auto-reduce their debt
            if desc in self._supplier_map:
                info = self._supplier_map[desc]
                debt_ctrl = SupplierDebtController()
                for d in info["debts"]:
                    debt_id = d["id"]
                    remaining = float(d["remaining_amount"])
                    pay_amount = min(amount, remaining)
                    if pay_amount > 0:
                        debt_ctrl.add_payment(debt_id, pay_amount, f"تسديد عبر المصروفات")
                        amount -= pay_amount
                        if amount <= 0:
                            break

            QMessageBox.information(self, "تم", "تم تسجيل المصروف بنجاح")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"حدث خطأ أثناء حفظ المصروف:\n{str(e)}")


class ReportsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = DatabaseManager()
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
        self.btn_quick_yesterday = _btn("البارحة", _AMBER, fs=14, h=36)
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

        self.btn_filter = _btn("🔍 تطبيق الفلترة", _BLUE, h=38)
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

        self.btn_pdf_active = _btn("📄 تصدير التقرير كـ PDF", _AMBER, h=40)
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
        self.card_credit = self._create_stat_card("المبيعات الآجلة للفترة", "0.00 د.ع", _AMBER)
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
        top_bar.addWidget(back_btn)
        top_bar.addWidget(_lbl("📋 فواتير المبيعات الصادرة للفترة المحددة", _BLUE, 18, True))
        top_bar.addStretch()
        lay.addLayout(top_bar)

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
        top_bar.addWidget(back_btn)
        top_bar.addWidget(_lbl("📦 فواتير الشراء وإدخال المخزن للفترة المحددة", _RED, 18, True))
        top_bar.addStretch()
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
        top_bar.addWidget(back_btn)
        top_bar.addWidget(_lbl("💊 كشف تفاصيل العلاج المصروف وتكلفته للفترة", _BLUE, 18, True))
        top_bar.addStretch()
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
        top_bar.addWidget(back_btn)
        top_bar.addWidget(_lbl("📦 جرد القيمة الكلية ورأس مال المخزن المتوفر", _BLUE, 18, True))
        top_bar.addStretch()

        self.stock_search = QLineEdit()
        self.stock_search.setPlaceholderText("🔍 ابحث باسم المادة أو الباركود...")
        self.stock_search.setFixedWidth(300)
        self.stock_search.textChanged.connect(self._on_stock_search_changed)
        top_bar.addWidget(self.stock_search)
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
        dialog = AddExpenseDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self._load_data()

    def _on_filter_clicked(self):
        self._load_data()

    def _load_data(self):
        d1 = self.date_from.date().toString("yyyy-MM-dd")
        d2 = self.date_to.date().toString("yyyy-MM-dd")

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

        r_exp = self.db.fetchone("SELECT SUM(CAST(amount AS REAL)) FROM expenses WHERE expense_date BETWEEN ? AND ?", (d1, d2))
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
            color = _GREEN if method == "cash" else _AMBER
            
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
            color = _GREEN if status == "paid" else (_AMBER if status == "partial" else _RED)
            
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
        printer.setPageMargins(12, 12, 12, 12, QPrinter.Millimeter)
        
        dialog = QPrintDialog(printer, self)
        dialog.setWindowTitle(f"طباعة - {title}")
        if dialog.exec_() == QPrintDialog.Accepted:
            doc = QTextDocument()
            doc.setHtml(html_content)
            doc.setPageSize(printer.pageRect().size())
            doc.print_(printer)

    def _export_pdf_content(self, html_content, default_filename):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "حفظ التقرير كملف PDF", default_filename, "PDF Files (*.pdf)"
        )
        if file_path:
            if not file_path.endswith(".pdf"):
                file_path += ".pdf"
            
            printer = QPrinter(QPrinter.ScreenResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(file_path)
            printer.setPageMargins(12, 12, 12, 12, QPrinter.Millimeter)
            
            doc = QTextDocument()
            doc.setHtml(html_content)
            doc.setPageSize(printer.pageRect().size())
            doc.print_(printer)
            
            QMessageBox.information(self, "تم بنجاح", f"تم حفظ ملف PDF للتقرير بنجاح:\n{os.path.basename(file_path)}")

    # ── Print Action Connections ──
    def _print_active_report(self):
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
        html = self._generate_sales_list_html()
        self._print_html_content(html, "تقرير فواتير المبيعات للفترة")

    def _export_sales_list_pdf(self):
        html = self._generate_sales_list_html()
        self._export_pdf_content(html, f"تقرير_فواتير_المبيعات_{self.date_from.date().toString('yyyyMMdd')}.pdf")

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
        self._export_pdf_content(html, f"تقرير_رأس_مال_المخزن_{QDate.currentDate().toString('yyyyMMdd')}.pdf")

    # ── HTML Generators ──
    def _generate_comprehensive_html(self):
        d1 = self.date_from.date().toString("yyyy-MM-dd")
        d2 = self.date_to.date().toString("yyyy-MM-dd")
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

        r_exp = self.db.fetchone("SELECT SUM(CAST(amount AS REAL)) FROM expenses WHERE expense_date BETWEEN ? AND ?", (d1, d2))
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

        purchases_invoices = self.db.fetchall("""
            SELECT sd.*, s.name as supplier_name
            FROM supplier_debts sd
            LEFT JOIN suppliers s ON sd.supplier_id = s.id
            WHERE date(sd.created_at, 'localtime') BETWEEN ? AND ?
            ORDER BY sd.created_at DESC
        """, (d1, d2))

        expenses_list = self.db.fetchall("""
            SELECT * FROM expenses WHERE expense_date BETWEEN ? AND ? ORDER BY expense_date DESC
        """, (d1, d2))

        html = f"""
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ direction: rtl; font-family: Tahoma, Arial, sans-serif; color: #1e293b; margin: 15px; font-size: 11px; }}
                .header {{ text-align: center; border-bottom: 2px solid #0f172a; padding-bottom: 10px; margin-bottom: 15px; }}
                .header h1 {{ margin: 0; font-size: 20px; color: #0f172a; }}
                .header p {{ margin: 5px 0 0 0; font-size: 12px; color: #64748b; }}
                .section-title {{ font-size: 13px; font-weight: bold; color: #0f172a; border-right: 4px solid #3b82f6; padding-right: 8px; margin: 15px 0 8px 0; }}
                .stats-table {{ width: 100%; border: none; margin-bottom: 15px; border-collapse: separate; border-spacing: 6px; }}
                .stat-box {{ padding: 10px; text-align: center; border-radius: 6px; border: 1px solid #cbd5e1; background-color: #f8fafc; }}
                table.data {{ width: 100%; border-collapse: collapse; margin-bottom: 15px; }}
                table.data th {{ background-color: #0f172a; color: #ffffff; padding: 6px; text-align: center; border: 1px solid #e2e8f0; font-size: 11px; }}
                table.data td {{ padding: 6px; border: 1px solid #e2e8f0; text-align: center; }}
                table.data tr:nth-child(even) {{ background-color: #f8fafc; }}
                .footer {{ text-align: center; font-size: 9px; color: #94a3b8; border-top: 1px solid #e2e8f0; padding-top: 8px; margin-top: 25px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{ph_name}</h1>
                <p>التقرير المالي الشامل للفترة من {d1} إلى {d2}</p>
                <p style="font-size: 10px; color: #94a3b8;">تاريخ التوليد: {QDate.currentDate().toString("yyyy-MM-dd")}</p>
            </div>

            <div class="section-title">📊 الخلاصة المالية للفترة</div>
            <table class="stats-table">
                <tr>
                    <td class="stat-box" style="width: 33.3%;">
                        <div style="font-weight: bold; color: #0f172a;">إجمالي المبيعات</div>
                        <div style="font-size: 14px; font-weight: bold; color: #2563eb; margin-top: 4px;">{format_currency(str(total_sales))} د.ع</div>
                    </td>
                    <td class="stat-box" style="width: 33.3%; background-color: #ecfdf5; border-color: #a7f3d0;">
                        <div style="font-weight: bold; color: #065f46;">الاستحصال النقدي (دخل اليوم)</div>
                        <div style="font-size: 14px; font-weight: bold; color: #059669; margin-top: 4px;">{format_currency(str(total_cash))} د.ع</div>
                    </td>
                    <td class="stat-box" style="width: 33.3%; background-color: #fffbeb; border-color: #fde68a;">
                        <div style="font-weight: bold; color: #92400e;">المبيعات الآجلة (الديون)</div>
                        <div style="font-size: 14px; font-weight: bold; color: #d97706; margin-top: 4px;">{format_currency(str(total_credit))} د.ع</div>
                    </td>
                </tr>
                <tr>
                    <td class="stat-box" style="width: 33.3%; background-color: #fef2f2; border-color: #fecaca;">
                        <div style="font-weight: bold; color: #991b1b;">إجمالي المشتريات</div>
                        <div style="font-size: 14px; font-weight: bold; color: #dc2626; margin-top: 4px;">{format_currency(str(total_purch))} د.ع</div>
                    </td>
                    <td class="stat-box" style="width: 33.3%; background-color: #faf5ff; border-color: #e9d5ff;">
                        <div style="font-weight: bold; color: #6b21a8;">إجمالي الخصومات الممنوحة</div>
                        <div style="font-size: 14px; font-weight: bold; color: #7e22ce; margin-top: 4px;">{format_currency(str(total_discount_val))} د.ع</div>
                    </td>
                    <td class="stat-box" style="width: 33.3%; background-color: #fdf2f8; border-color: #fbcfe8;">
                        <div style="font-weight: bold; color: #9d174d;">صافي الأرباح للفترة</div>
                        <div style="font-size: 14px; font-weight: bold; color: #db2777; margin-top: 4px;">{format_currency(str(net_profit))} د.ع</div>
                    </td>
                </tr>
            </table>
        """

        html += '<div class="section-title">📋 تفاصيل فواتير المبيعات الصادرة</div>'
        html += '<table class="data"><tr><th>رقم الفاتورة</th><th>التاريخ والوقت</th><th>البائع</th><th>الإجمالي</th><th>المدفوع</th><th>طريقة الدفع</th></tr>'
        if sales_invoices:
            for s in sales_invoices:
                method_ar = "نقدي" if s["payment_method"] == "cash" else "آجل"
                html += f'<tr><td>{s["invoice_number"]}</td><td>{s["created_at"][:19]}</td><td>{s["user_name"] or ""}</td><td>{format_currency(s["total_amount"])}</td><td>{format_currency(s["paid_amount"])}</td><td>{method_ar}</td></tr>'
        else:
            html += '<tr><td colspan="6">لا توجد مبيعات في هذه الفترة</td></tr>'
        html += '</table>'

        html += '<div class="section-title">📦 تفاصيل فواتير الشراء وإدخال المخزن</div>'
        html += '<table class="data"><tr><th>رقم الفاتورة</th><th>التاريخ والوقت</th><th>المذخر</th><th>الإجمالي</th><th>المدفوع</th><th>الحالة</th></tr>'
        if purchases_invoices:
            for p in purchases_invoices:
                status_ar = "مسدد" if p["status"] == "paid" else ("جزئي" if p["status"] == "partial" else "ذمة")
                html += f'<tr><td>{p["invoice_number"]}</td><td>{p["created_at"][:19]}</td><td>{p["supplier_name"] or ""}</td><td>{format_currency(str(p["total_amount"] or 0))}</td><td>{format_currency(str(p["paid_amount"] or 0))}</td><td>{status_ar}</td></tr>'
        else:
            html += '<tr><td colspan="6">لا توجد مشتريات في هذه الفترة</td></tr>'
        html += '</table>'

        html += '<div class="section-title">💸 تفاصيل سجل المصاريف</div>'
        html += '<table class="data"><tr><th>التاريخ</th><th>البيان والتفاصيل</th><th>المبلغ</th></tr>'
        if expenses_list:
            for e in expenses_list:
                html += f'<tr><td>{e["expense_date"]}</td><td>{e["description"] or ""}</td><td>{format_currency(str(e["amount"]))} د.ع</td></tr>'
        else:
            html += '<tr><td colspan="3">لا توجد مصاريف مسجلة في هذه الفترة</td></tr>'
        html += '</table>'

        html += f"""
            <div class="footer">
                نظام إدارة الصيدلية PharmaSys - التقرير الشامل للفترة
            </div>
        </body>
        </html>
        """
        return html

    def _generate_sales_list_html(self):
        d1 = self.date_from.date().toString("yyyy-MM-dd")
        d2 = self.date_to.date().toString("yyyy-MM-dd")
        ph_name = self._get_pharmacy_name()
        
        invoices = self.db.fetchall("""
            SELECT s.*, u.full_name as user_name
            FROM sales s
            LEFT JOIN users u ON s.user_id = u.id
            WHERE date(s.created_at, 'localtime') BETWEEN ? AND ?
            ORDER BY s.created_at DESC
        """, (d1, d2))
        
        html = f"""
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ direction: rtl; font-family: Tahoma, Arial, sans-serif; color: #1e293b; margin: 15px; font-size: 11px; }}
                .header {{ text-align: center; border-bottom: 2px solid #0f172a; padding-bottom: 10px; margin-bottom: 15px; }}
                .header h1 {{ margin: 0; font-size: 20px; color: #0f172a; }}
                .header p {{ margin: 5px 0 0 0; font-size: 12px; color: #64748b; }}
                table.data {{ width: 100%; border-collapse: collapse; margin-bottom: 15px; }}
                table.data th {{ background-color: #0f172a; color: #ffffff; padding: 6px; text-align: center; border: 1px solid #e2e8f0; font-size: 11px; }}
                table.data td {{ padding: 6px; border: 1px solid #e2e8f0; text-align: center; }}
                table.data tr:nth-child(even) {{ background-color: #f8fafc; }}
                .footer {{ text-align: center; font-size: 9px; color: #94a3b8; border-top: 1px solid #e2e8f0; padding-top: 8px; margin-top: 25px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{ph_name}</h1>
                <p>تقرير فواتير المبيعات الصادرة للفترة من {d1} إلى {d2}</p>
                <p style="font-size: 10px; color: #94a3b8;">تاريخ التوليد: {QDate.currentDate().toString("yyyy-MM-dd")}</p>
            </div>
            <table class="data">
                <tr>
                    <th>رقم الفاتورة</th>
                    <th>التاريخ والوقت</th>
                    <th>البائع</th>
                    <th>الإجمالي</th>
                    <th>المدفوع</th>
                    <th>طريقة الدفع</th>
                </tr>
        """
        if invoices:
            for s in invoices:
                method_ar = "نقدي" if s["payment_method"] == "cash" else "آجل"
                html += f'<tr><td>{s["invoice_number"]}</td><td>{s["created_at"][:19]}</td><td>{s["user_name"] or ""}</td><td>{format_currency(s["total_amount"])}</td><td>{format_currency(s["paid_amount"])}</td><td>{method_ar}</td></tr>'
        else:
            html += '<tr><td colspan="6">لا توجد مبيعات في هذه الفترة</td></tr>'
        html += '</table>'
        html += '</body></html>'
        return html

    def _generate_purchases_list_html(self):
        d1 = self.date_from.date().toString("yyyy-MM-dd")
        d2 = self.date_to.date().toString("yyyy-MM-dd")
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
                body {{ direction: rtl; font-family: Tahoma, Arial, sans-serif; color: #1e293b; margin: 15px; font-size: 11px; }}
                .header {{ text-align: center; border-bottom: 2px solid #0f172a; padding-bottom: 10px; margin-bottom: 15px; }}
                .header h1 {{ margin: 0; font-size: 20px; color: #0f172a; }}
                .header p {{ margin: 5px 0 0 0; font-size: 12px; color: #64748b; }}
                table.data {{ width: 100%; border-collapse: collapse; margin-bottom: 15px; }}
                table.data th {{ background-color: #0f172a; color: #ffffff; padding: 6px; text-align: center; border: 1px solid #e2e8f0; font-size: 11px; }}
                table.data td {{ padding: 6px; border: 1px solid #e2e8f0; text-align: center; }}
                table.data tr:nth-child(even) {{ background-color: #f8fafc; }}
                .footer {{ text-align: center; font-size: 9px; color: #94a3b8; border-top: 1px solid #e2e8f0; padding-top: 8px; margin-top: 25px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{ph_name}</h1>
                <p>تقرير فواتير الشراء وإدخال المخزن للفترة من {d1} إلى {d2}</p>
                <p style="font-size: 10px; color: #94a3b8;">تاريخ التوليد: {QDate.currentDate().toString("yyyy-MM-dd")}</p>
            </div>
            <table class="data">
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
        d1 = self.date_from.date().toString("yyyy-MM-dd")
        d2 = self.date_to.date().toString("yyyy-MM-dd")
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
                body {{ direction: rtl; font-family: Tahoma, Arial, sans-serif; color: #1e293b; margin: 15px; font-size: 11px; }}
                .header {{ text-align: center; border-bottom: 2px solid #0f172a; padding-bottom: 10px; margin-bottom: 15px; }}
                .header h1 {{ margin: 0; font-size: 20px; color: #0f172a; }}
                .header p {{ margin: 5px 0 0 0; font-size: 12px; color: #64748b; }}
                table.data {{ width: 100%; border-collapse: collapse; margin-bottom: 15px; }}
                table.data th {{ background-color: #0f172a; color: #ffffff; padding: 6px; text-align: center; border: 1px solid #e2e8f0; font-size: 11px; }}
                table.data td {{ padding: 6px; border: 1px solid #e2e8f0; text-align: center; }}
                table.data tr:nth-child(even) {{ background-color: #f8fafc; }}
                .totals-box {{ background-color: #f1f5f9; padding: 12px; border-radius: 6px; border: 1px solid #cbd5e1; margin-top: 15px; }}
                .footer {{ text-align: center; font-size: 9px; color: #94a3b8; border-top: 1px solid #e2e8f0; padding-top: 8px; margin-top: 25px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{ph_name}</h1>
                <p>تقرير العلاج المصروف ورأس المال المبيع للفترة من {d1} إلى {d2}</p>
                <p style="font-size: 10px; color: #94a3b8;">تاريخ التوليد: {QDate.currentDate().toString("yyyy-MM-dd")}</p>
            </div>
            <table class="data">
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
                نظام إدارة الصيدلية PharmaSys - تقرير رأس المال المصروف
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
                body {{ direction: rtl; font-family: Tahoma, Arial, sans-serif; color: #1e293b; margin: 15px; font-size: 11px; }}
                .header {{ text-align: center; border-bottom: 2px solid #0f172a; padding-bottom: 10px; margin-bottom: 15px; }}
                .header h1 {{ margin: 0; font-size: 20px; color: #0f172a; }}
                .header p {{ margin: 5px 0 0 0; font-size: 12px; color: #64748b; }}
                table.data {{ width: 100%; border-collapse: collapse; margin-bottom: 15px; }}
                table.data th {{ background-color: #0f172a; color: #ffffff; padding: 6px; text-align: center; border: 1px solid #e2e8f0; font-size: 11px; }}
                table.data td {{ padding: 6px; border: 1px solid #e2e8f0; text-align: center; }}
                table.data tr:nth-child(even) {{ background-color: #f8fafc; }}
                .totals-box {{ background-color: #f1f5f9; padding: 12px; border-radius: 6px; border: 1px solid #cbd5e1; margin-top: 15px; }}
                .footer {{ text-align: center; font-size: 9px; color: #94a3b8; border-top: 1px solid #e2e8f0; padding-top: 8px; margin-top: 25px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{ph_name}</h1>
                <p>تقرير كلفة المخزن المتوفر (رأس مال الصيدلية الحالي)</p>
                <p style="font-size: 10px; color: #94a3b8;">تاريخ الجرد: {QDate.currentDate().toString("yyyy-MM-dd")}</p>
            </div>
            <table class="data">
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
                        <td style="border: none; text-align: right; font-weight: bold; color: #b45309;">إجمالي رأس مال المخزن: {format_currency(str(stock_tot_cost))} د.ع</td>
                        <td style="border: none; text-align: center; font-weight: bold;">إجمالي القيمة البيعية المتوقعة: {format_currency(str(stock_tot_sale))} د.ع</td>
                        <td style="border: none; text-align: left; font-weight: bold; color: #059669;">الأرباح المتوقعة عند التصفية: {format_currency(str(stock_tot_profit))} د.ع</td>
                    </tr>
                </table>
            </div>
            <div class="footer">
                نظام إدارة الصيدلية PharmaSys - تقرير قيمة رأس المال بالمخزن
            </div>
        </body>
        </html>
        """
        return html
