from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QFormLayout, QDoubleSpinBox, QSpinBox,
    QMessageBox, QComboBox, QDateEdit, QAbstractItemView,
    QFrame, QSizePolicy, QScrollArea, QCompleter, QInputDialog,
)
from PyQt5.QtCore import Qt, QDate, QTimer, QStringListModel, QLocale
from PyQt5.QtGui import QColor, QFont, QPainter, QLinearGradient, QBrush, QKeySequence
from PyQt5.QtWidgets import QShortcut
from utils.modern_msgbox import ModernMessageBox as QMessageBox

from controllers.product_controller import ProductController
from controllers.order_controller import OrderController
from views.bulk_purchase_dialog import BulkPurchaseDialog
from controllers.supplier_controller import SupplierController
from database.connection import DatabaseManager
from utils.printer_manager import PrinterManager
from utils.decimal_handler import to_decimal, format_currency, DECIMAL_ZERO
from decimal import Decimal
from utils.logger import safe_operation

import datetime


# ── helpers ────────────────────────────────────────────────────
def _lbl(text, color="#e2e8f0", size=14, bold=False, align=None):
    l = QLabel(text)
    w = "700" if bold else "400"
    l.setStyleSheet(f"font-size:{size}px;font-weight:{w};color:{color};background:transparent")
    if align:
        l.setAlignment(align)
    return l


def _stat_card(icon, title, value_str, accent, bg_icon):
    """بطاقة إحصائية مربعة الزوايا المستديرة"""
    card = QFrame()
    card.setObjectName("statCard")
    card.setStyleSheet(
        "QFrame#statCard{"
        "background:#1e293b;border:1px solid #334155;"
        "border-radius:14px;padding:4px"
        "}"
    )
    card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    card.setFixedHeight(100)

    h = QHBoxLayout(card)
    h.setContentsMargins(16, 10, 16, 10)
    h.setSpacing(16)

    icon_lbl = QLabel(icon)
    icon_lbl.setFixedSize(54, 54)
    icon_lbl.setAlignment(Qt.AlignCenter)
    icon_lbl.setStyleSheet(
        f"font-size:26px;background:{bg_icon};"
        f"border-radius:12px;color:{accent}"
    )
    h.addWidget(icon_lbl)

    v = QVBoxLayout()
    v.setSpacing(2)
    t = QLabel(title)
    t.setStyleSheet("font-size:13px;color:#94a3b8;font-weight:600;background:transparent")
    v.addWidget(t)
    val = QLabel(value_str)
    val.setObjectName("statValue")
    val.setStyleSheet(
        f"font-size:28px;font-weight:800;color:{accent};background:transparent"
    )
    v.addWidget(val)
    h.addLayout(v)
    h.addStretch()

    return card, val


def _alert_item(msg, color="#f59e0b"):
    """عنصر تنبيه واحد في اللوحة الجانبية"""
    w = QFrame()
    w.setStyleSheet(
        f"QFrame{{background:#0f172a;border-left:3px solid {color};"
        f"border-radius:6px;padding:4px}}"
    )
    lay = QVBoxLayout(w)
    lay.setContentsMargins(8, 6, 8, 6)
    lay.setSpacing(2)
    icon = "⚠" if color == "#f59e0b" else "⛔"
    lbl = QLabel(f"{icon} {msg}")
    lbl.setWordWrap(True)
    lbl.setStyleSheet(
        f"font-size:12px;color:{color};font-weight:600;background:transparent"
    )
    lay.addWidget(lbl)
    return w


# ═══════════════════════════════════════════════════════════════
class InventoryWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.product_ctrl = ProductController()
        self.supplier_ctrl = SupplierController()
        self.db = DatabaseManager()
        self._all_products = []
        self._filter_category = None   # None = all
        self._filter_status = None     # None = all | "ok" | "low" | "expired"
        self._setup_ui()
        self._load_products()

    # ─────── background paint ───────
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        bg = QLinearGradient(0, 0, 0, self.height())
        bg.setColorAt(0.0, QColor(15, 23, 42))
        bg.setColorAt(1.0, QColor(10, 15, 30))
        p.fillRect(self.rect(), QBrush(bg))
        p.end()

    # ─────── UI ───────
    def _setup_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        # ── main area (left) ──
        main_col = QVBoxLayout()
        main_col.setSpacing(8)

        # 1. stat cards row
        stats_row = QHBoxLayout()
        stats_row.setSpacing(10)

        self._card_total, self._val_total = _stat_card(
            "📦", "إجمالي المواد", "0", "#38bdf8", "#0c4a6e40")
        self._card_low, self._val_low = _stat_card(
            "🛒", "طلبات الشراء النشطة", "0", "#34d399", "#064e3b40")
        self._card_near, self._val_near = _stat_card(
            "⚠", "مواد أوشكت على النفاد", "0", "#f59e0b", "#78350f40")
        self._card_exp, self._val_exp = _stat_card(
            "⏰", "مواد منتهية الصلاحية", "0", "#f87171", "#7f1d1d40")

        for c in [self._card_total, self._card_low, self._card_near, self._card_exp]:
            stats_row.addWidget(c)

        main_col.addLayout(stats_row)

        # 2. toolbar row
        tool_row = QHBoxLayout()
        tool_row.setSpacing(8)

        self.add_btn = QPushButton("＋  إضافة مادة جديدة")
        self.add_btn.setFixedHeight(42)
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.setStyleSheet(
            "QPushButton{font-size:14px;font-weight:700;padding:0 18px;"
            "background:#059669;color:white;border:none;border-radius:10px}"
            "QPushButton:hover{background:#047857}"
            "QPushButton:pressed{background:#065f46}"
        )
        self.add_btn.clicked.connect(self._show_add_dialog)
        tool_row.addWidget(self.add_btn)

        self.bulk_btn = QPushButton("️فاتورة مجمعة")
        self.bulk_btn.setFixedHeight(42)
        self.bulk_btn.setCursor(Qt.PointingHandCursor)
        self.bulk_btn.setStyleSheet(
            "QPushButton{font-size:14px;font-weight:700;padding:0 18px;"
            "background:#7c3aed;color:white;border:none;border-radius:10px}"
            "QPushButton:hover{background:#6d28d9}"
            "QPushButton:pressed{background:#5b21b6}"
        )
        self.bulk_btn.clicked.connect(self._show_bulk_dialog)
        tool_row.addWidget(self.bulk_btn)

        tool_row.addStretch()

        # search
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍  ابحث عن مادة أو باركود...")
        self.search_input.setFixedHeight(42)
        self.search_input.setFixedWidth(320)
        self.search_input.setStyleSheet(
            "QLineEdit{font-size:14px;padding:0 14px;"
            "background:#1e293b;border:1.5px solid #334155;"
            "border-radius:10px;color:#f1f5f9}"
            "QLineEdit:focus{border-color:#38bdf8}"
        )
        self.search_input.textChanged.connect(self._apply_filters)
        tool_row.addWidget(self.search_input)

        # category filter
        self.cat_combo = QComboBox()
        self.cat_combo.setFixedHeight(42)
        self.cat_combo.setMinimumWidth(130)
        self.cat_combo.setStyleSheet(
            "QComboBox{font-size:13px;font-weight:600;padding:0 12px;"
            "background:#1e293b;border:1.5px solid #334155;"
            "border-radius:10px;color:#f1f5f9}"
            "QComboBox:focus{border-color:#38bdf8}"
            "QComboBox::drop-down{border:none;width:22px}"
            "QComboBox QAbstractItemView{background:#1e293b;color:#f1f5f9;"
            "font-size:13px;selection-background-color:#38bdf840}"
        )
        self.cat_combo.addItem("كل الأقسام", None)
        cats = self.db.fetchall("SELECT id, name FROM categories ORDER BY name")
        for c in cats:
            self.cat_combo.addItem(c["name"], c["id"])
        self.cat_combo.currentIndexChanged.connect(self._apply_filters)
        tool_row.addWidget(self.cat_combo)

        # status filter
        self.status_combo = QComboBox()
        self.status_combo.setFixedHeight(42)
        self.status_combo.setMinimumWidth(130)
        self.status_combo.setStyleSheet(self.cat_combo.styleSheet())
        self.status_combo.addItem("فحص الحالة", None)
        self.status_combo.addItem("✅  آمن", "ok")
        self.status_combo.addItem("⚠  منخفض", "low")
        self.status_combo.addItem("❌  منتهي", "expired")
        self.status_combo.currentIndexChanged.connect(self._apply_filters)
        tool_row.addWidget(self.status_combo)

        main_col.addLayout(tool_row)

        # 3. table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "كود المادة", "اسم المادة/المحلول", "القسم",
            "الكمية الحالية", "وحدة القياس",
            "تاريخ انتهاء الصلاحية", "حالة المخزون"
        ])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        for col in [2, 3, 4, 5, 6]:
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(False)
        self.table.doubleClicked.connect(self._on_edit_product)
        self.table.setStyleSheet(
            "QTableWidget{"
            "background:#1e293b;border:1px solid #334155;"
            "border-radius:12px;color:#f1f5f9;outline:none"
            "}"
            "QHeaderView::section{"
            "background:#0f172a;color:#94a3b8;padding:12px 10px;"
            "border:none;border-bottom:1px solid #334155;"
            "font-size:15px;font-weight:700"
            "}"
            "QTableWidget::item{"
            "padding:12px 10px;border-bottom:1px solid #0f172a50;"
            "font-size:15px"
            "}"
            "QTableWidget::item:selected{"
            "background:#38bdf820;color:#f1f5f9"
            "}"
        )
        main_col.addWidget(self.table, 1)

        # assemble
        root.addLayout(main_col, 1)

    # ─────── data loading ───────
    def _load_products(self):
        self._all_products = self.db.fetchall(
            """SELECT p.*, c.name as category_name
               FROM products p
               LEFT JOIN categories c ON p.category_id = c.id
               WHERE p.is_active = 1
               ORDER BY p.name"""
        )
        self._update_stats()
        self._apply_filters()
        self._refresh_alerts()

    def _product_status(self, p):
        today = datetime.date.today()
        name = dict(p).get("name", "")
        bc = dict(p).get("barcode", "")
        exp = dict(p).get("expiry_date")
        if exp:
            try:
                exp_date = datetime.date.fromisoformat(str(exp))
                if exp_date <= today:
                    return "expired"
            except Exception:
                pass
        qty = dict(p).get("stock_quantity") or 0
        mn = dict(p).get("min_stock") or 0
        if qty <= 0:
            return "expired"
        if qty <= mn:
            return "low"
        return "ok"

    def _update_stats(self):
        total = len(self._all_products)
        low = sum(1 for p in self._all_products if self._product_status(p) == "low")
        expired = sum(1 for p in self._all_products if self._product_status(p) == "expired")
        # طلبات الشراء النشطة = منتجات منخفضة (تحتاج إعادة طلب)
        need_order = low
        self._val_total.setText(str(total))
        self._val_low.setText(str(need_order))
        self._val_near.setText(str(low))
        self._val_exp.setText(str(expired))

    def _apply_filters(self):
        text = self.search_input.text().strip().lower()
        cat_id = self.cat_combo.currentData()
        status_key = self.status_combo.currentData()

        filtered = []
        for p in self._all_products:
            # text filter
            if text:
                name = (dict(p).get("name") or "").lower()
                bc = (dict(p).get("barcode") or "").lower()
                if text not in name and text not in bc:
                    continue
            # category filter
            if cat_id is not None:
                if dict(p).get("category_id") != cat_id:
                    continue
            # status filter
            if status_key:
                if self._product_status(p) != status_key:
                    continue
            filtered.append(p)

        self._populate_table(filtered)

    def _populate_table(self, products):
        self.table.setRowCount(len(products))
        today = datetime.date.today()

        for i, p in enumerate(products):
            status = self._product_status(p)

            # كود المادة (barcode)
            bc_item = QTableWidgetItem(dict(p).get("barcode") or "")
            bc_item.setForeground(QColor("#94a3b8"))
            bc_item.setFont(QFont("Courier New", 14, QFont.Bold))
            self.table.setItem(i, 0, bc_item)

            # اسم المادة
            name_item = QTableWidgetItem(dict(p).get("name") or "")
            name_item.setForeground(QColor("#f1f5f9"))
            name_item.setFont(QFont("Segoe UI", 15, QFont.Bold))
            self.table.setItem(i, 1, name_item)

            # القسم
            cat_item = QTableWidgetItem(dict(p).get("category_name") or "—")
            cat_item.setForeground(QColor("#cbd5e1"))
            self.table.setItem(i, 2, cat_item)

            # الكمية الحالية
            qty = dict(p).get("stock_quantity") or 0
            qty_item = QTableWidgetItem(str(qty))
            qty_item.setTextAlignment(Qt.AlignCenter)
            if status == "expired":
                qty_item.setForeground(QColor("#f87171"))
            elif status == "low":
                qty_item.setForeground(QColor("#f59e0b"))
            else:
                qty_item.setForeground(QColor("#34d399"))
            qty_item.setFont(QFont("Segoe UI", 15, QFont.Bold))
            self.table.setItem(i, 3, qty_item)

            # وحدة القياس (scientific_name كبديل أو "مهلي")
            unit = dict(p).get("scientific_name") or "—"
            unit_item = QTableWidgetItem(unit)
            unit_item.setTextAlignment(Qt.AlignCenter)
            unit_item.setForeground(QColor("#94a3b8"))
            self.table.setItem(i, 4, unit_item)

            # تاريخ الصلاحية
            exp = dict(p).get("expiry_date") or "—"
            exp_item = QTableWidgetItem(str(exp))
            exp_item.setTextAlignment(Qt.AlignCenter)
            if exp != "—":
                try:
                    exp_date = datetime.date.fromisoformat(str(exp))
                    if exp_date <= today:
                        exp_item.setForeground(QColor("#f87171"))
                    elif (exp_date - today).days <= 30:
                        exp_item.setForeground(QColor("#f59e0b"))
                    else:
                        exp_item.setForeground(QColor("#94a3b8"))
                except Exception:
                    exp_item.setForeground(QColor("#94a3b8"))
            self.table.setItem(i, 5, exp_item)

            # حالة المخزون - widget مع أيقونة ولون
            status_widget = self._make_status_badge(status)
            self.table.setCellWidget(i, 6, status_widget)

            self.table.setRowHeight(i, 60)

            # تلوين خفيف للصف بأكمله
            row_bg = None
            if status == "expired":
                row_bg = QColor("#7f1d1d18")
            elif status == "low":
                row_bg = QColor("#78350f18")
            if row_bg:
                for col in range(6):
                    item = self.table.item(i, col)
                    if item:
                        item.setBackground(row_bg)

    def _make_status_badge(self, status):
        w = QWidget()
        w.setStyleSheet("background:transparent")
        h = QHBoxLayout(w)
        h.setContentsMargins(6, 4, 6, 4)
        h.setAlignment(Qt.AlignCenter)

        if status == "ok":
            icon, text, color, bg = "✅", "آمن", "#34d399", "#064e3b50"
        elif status == "low":
            icon, text, color, bg = "⚠", "منخفض", "#f59e0b", "#78350f50"
        else:
            icon, text, color, bg = "❌", "منتهي", "#f87171", "#7f1d1d50"

        badge = QFrame()
        badge.setStyleSheet(
            f"QFrame{{background:{bg};border:1px solid {color}50;"
            f"border-radius:8px;padding:0}}"
        )
        bl = QHBoxLayout(badge)
        bl.setContentsMargins(8, 3, 10, 3)
        bl.setSpacing(4)

        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet("font-size:13px;background:transparent;border:none")
        bl.addWidget(icon_lbl)

        text_lbl = QLabel(text)
        text_lbl.setStyleSheet(
            f"font-size:13px;font-weight:700;color:{color};"
            f"background:transparent;border:none"
        )
        bl.addWidget(text_lbl)

        h.addWidget(badge)
        return w

    def _refresh_alerts(self):
        alerts = []
        for p in self._all_products:
            p_dict = dict(p)
            status = self._product_status(p_dict)
            name = p_dict.get("name") or ""
            qty = p_dict.get("stock_quantity") or 0
            if status == "expired":
                alerts.append(f"{name} - {qty} - منتهية الصلاحية")
            elif status == "low":
                alerts.append(f"{name} - {qty} - منخفضة في المخزن")
                
            if len(alerts) >= 15:
                break
                
        if alerts:
            from utils.toast import ToastNotification
            ToastNotification.show_message("\n".join(alerts), 50000, self.window())

    # ─────── actions ───────
    def _on_edit_product(self, index):
        row = index.row()
        # get barcode from column 0 to find product
        bc_item = self.table.item(row, 0)
        if not bc_item:
            return
        barcode = bc_item.text()
        product = self.db.fetchone(
            "SELECT * FROM products WHERE barcode = ? AND is_active = 1", (barcode,)
        )
        if product:
            self._show_edit_dialog(product)

    def _show_add_dialog(self):
        dialog = ProductDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self._load_products()

    def _show_bulk_dialog(self):
        try:
            dialog = BulkPurchaseDialog(self)
            dialog.exec_()
            self._load_products()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"تعذر فتح الفاتورة المجمعة:\n{e}")

    def _show_edit_dialog(self, product):
        dialog = ProductDialog(self, product)
        if dialog.exec_() == QDialog.Accepted:
            self._load_products()


# ═══════════════════════════════════════════════════════════════
# ProductDialog - نافذة إضافة/تعديل المادة
# ═══════════════════════════════════════════════════════════════
class ProductDialog(QDialog):
    def __init__(self, parent=None, product=None, bulk_mode=False):
        super().__init__(parent)
        self.product = product
        self._existing_product = None   # filled by barcode lookup
        self._new_batch_mode = False    # True → add stock to existing
        self.product_ctrl = ProductController()
        self.supplier_ctrl = SupplierController()
        self.db = DatabaseManager()
        self.printer_manager = PrinterManager()
        self.setWindowTitle("تعديل المادة" if product else "إضافة مادة جديدة")
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.CustomizeWindowHint)
        self.setMinimumSize(960, 600)
        self.setStyleSheet(
            "QDialog{background:#1e293b;color:#f1f5f9}"
            "QLabel{color:#cbd5e1;font-size:14px;background:transparent}"
            "QLineEdit,QDoubleSpinBox,QSpinBox,QComboBox,QDateEdit{"
            "background:#0f172a;border:1.5px solid #334155;border-radius:8px;"
            "color:#f1f5f9;font-size:15px;padding:6px 12px;min-height:38px"
            "}"
            "QLineEdit:focus,QDoubleSpinBox:focus,QSpinBox:focus,"
            "QComboBox:focus,QDateEdit:focus{border-color:#38bdf8}"
            "QComboBox::drop-down{border:none;width:26px}"
            "QComboBox QAbstractItemView{background:#1e293b;color:#f1f5f9;"
            "font-size:15px;selection-background-color:#38bdf840}"
        )
        self._setup_ui()
        if product:
            self._load_data(product)

    def showEvent(self, event):
        super().showEvent(event)
        self.showMaximized()

    def _setup_ui(self):
        main = QVBoxLayout(self)
        main.setSpacing(10)
        main.setContentsMargins(16, 12, 16, 12)

        title_lbl = QLabel("تعديل المادة" if self.product else "إضافة مادة جديدة")
        title_lbl.setStyleSheet("font-size:22px;font-weight:800;color:#f1f5f9;background:transparent")
        main.addWidget(title_lbl)

        locale_iqd = QLocale(QLocale.English, QLocale.UnitedStates)

        def _card(title_icon, title_text, body_setup):
            c = QFrame()
            c.setStyleSheet("QFrame{background:#141d2e;border-radius:12px;padding:0}")
            cl = QVBoxLayout(c)
            cl.setContentsMargins(18, 14, 18, 16)
            cl.setSpacing(10)
            ct = QLabel(f"{title_icon}  {title_text}")
            ct.setStyleSheet("font-size:16px;font-weight:700;color:#f1f5f9;background:transparent")
            cl.addWidget(ct)
            body_setup(cl)
            return c

        def _fl(text):
            l = QLabel(text)
            l.setStyleSheet("font-size:14px;font-weight:600;color:#8899bb;background:transparent")
            return l

        body = QHBoxLayout()
        body.setSpacing(14)

        inp = (
            "QLineEdit,QSpinBox,QDoubleSpinBox,QDateEdit,QComboBox{"
            "background:transparent;border:none;border-bottom:1px solid #2a3f5f;"
            "color:#f1f5f9;font-size:15px;font-weight:600;padding:6px 2px}"
            "QLineEdit:focus,QSpinBox:focus,QDoubleSpinBox:focus,QComboBox:focus{"
            "border-bottom:1px solid #4a8fe7}"
        )

        # ═══ LEFT ═══
        lc = QVBoxLayout()
        lc.setSpacing(10)

        def _setup_basic(cl):
            cl.addWidget(_fl("🔳  الباركود"))
            bc_row = QHBoxLayout()
            bc_row.setSpacing(6)
            self.barcode_input = QLineEdit()
            self.barcode_input.setPlaceholderText("امسح الباركود أو اكتبه…")
            self.barcode_input.setFixedHeight(54)
            self.barcode_input.setStyleSheet(
                "QLineEdit{background:transparent;border:none;border-bottom:2px solid #2a3f5f;"
                "color:#f1f5f9;font-size:20px;font-weight:700;padding:8px 4px;font-family:monospace}"
                "QLineEdit:focus{border-bottom:2px solid #4a8fe7}"
            )
            self.barcode_input.editingFinished.connect(self._on_barcode_finished)
            bc_row.addWidget(self.barcode_input, 1)

            self.print_bc_btn = QPushButton("🖨️")
            self.print_bc_btn.setToolTip("طباعة باركود")
            self.print_bc_btn.setFixedSize(54, 54)
            self.print_bc_btn.setStyleSheet(
                "QPushButton{background:#2a3f5f;color:#7ba3ff;border:none;"
                "border-radius:10px;font-size:20px}"
                "QPushButton:hover{background:#3a5580;}"
            )
            self.print_bc_btn.clicked.connect(self._generate_and_print_barcode)
            bc_row.addWidget(self.print_bc_btn)

            self._barcode_status_lbl = QLabel("")
            self._barcode_status_lbl.setStyleSheet("font-size:11px;color:#4a6580;background:transparent;padding:0 4px")
            bc_row.addWidget(self._barcode_status_lbl)
            cl.addLayout(bc_row)

            cl.addWidget(_fl("💊  اسم المادة"))
            self.name_input = QLineEdit()
            self.name_input.setPlaceholderText("اسم المادة / المحلول")
            self.name_input.setFixedHeight(54)
            self.name_input.setStyleSheet(
                "QLineEdit{background:transparent;border:none;border-bottom:2px solid #2a3f5f;"
                "color:#f1f5f9;font-size:20px;font-weight:700;padding:8px 4px}"
                "QLineEdit:focus{border-bottom:2px solid #4a8fe7}"
            )
            cl.addWidget(self.name_input)

            cl.addWidget(_fl("⚖️  وحدة القياس"))
            self.sci_name_input = QLineEdit()
            self.sci_name_input.setPlaceholderText("مهلي، جرام، أمبولة، …")
            self.sci_name_input.setFixedHeight(54)
            self.sci_name_input.setStyleSheet(
                "QLineEdit{background:transparent;border:none;border-bottom:2px solid #2a3f5f;"
                "color:#94a3b8;font-size:18px;font-weight:600;padding:8px 4px}"
                "QLineEdit:focus{border-bottom:2px solid #4a8fe7}"
            )
            cl.addWidget(self.sci_name_input)

            cl.addWidget(_fl("📂  القسم"))
            categories = self.db.fetchall("SELECT id, name FROM categories ORDER BY name")
            self._cat_items = [("-- اختر القسم --", None)] + [(c["name"], c["id"]) for c in categories]
            self.category_combo = self._make_editable_combo(self._cat_items)
            self.category_combo.setFixedHeight(54)
            self.category_combo.setStyleSheet(
                "QComboBox{background:transparent;border:none;border-bottom:2px solid #2a3f5f;"
                "color:#f1f5f9;font-size:18px;font-weight:600;padding:8px 4px}"
                "QComboBox:focus{border-bottom:2px solid #4a8fe7}"
                "QComboBox::drop-down{border:none;width:28px}"
            )
            cl.addWidget(self.category_combo)

            cl.addWidget(_fl("🏪  المورد"))
            suppliers = self.supplier_ctrl.get_all()
            self._sup_items = [("-- اختر المورد --", None)] + [(s["name"], s["id"]) for s in suppliers]
            self.supplier_combo = self._make_editable_combo(self._sup_items)
            self.supplier_combo.setFixedHeight(54)
            self.supplier_combo.setStyleSheet(
                "QComboBox{background:transparent;border:none;border-bottom:2px solid #2a3f5f;"
                "color:#f1f5f9;font-size:18px;font-weight:600;padding:8px 4px}"
                "QComboBox:focus{border-bottom:2px solid #4a8fe7}"
                "QComboBox::drop-down{border:none;width:28px}"
            )
            cl.addWidget(self.supplier_combo)

        lc.addWidget(_card("📋", "المعلومات الأساسية", _setup_basic))

        def _setup_inv(cl):
            cl.addWidget(_fl("📦  الكمية الحالية"))
            self.stock_input = QSpinBox()
            self.stock_input.setRange(0, 999999)
            self.stock_input.setFixedHeight(54)
            self.stock_input.setLocale(locale_iqd)
            self.stock_input.setGroupSeparatorShown(True)
            self.stock_input.setStyleSheet(
                "QSpinBox{background:transparent;border:none;border-bottom:2px solid #2a3f5f;"
                "color:#7ba3ff;font-size:20px;font-weight:700;padding:8px 4px;min-width:140px}"
                "QSpinBox:focus{border-bottom:2px solid #4a8fe7}"
                "QSpinBox::up-button,QSpinBox::down-button{border:none;width:0px}"
            )
            cl.addWidget(self.stock_input)

            cl.addWidget(_fl("⚠️  حد التنبيه (أدنى)"))
            self.min_stock_input = QSpinBox()
            self.min_stock_input.setRange(0, 99999)
            self.min_stock_input.setValue(10)
            self.min_stock_input.setFixedHeight(54)
            self.min_stock_input.setLocale(locale_iqd)
            self.min_stock_input.setGroupSeparatorShown(True)
            self.min_stock_input.setStyleSheet(
                "QSpinBox{background:transparent;border:none;border-bottom:2px solid #2a3f5f;"
                "color:#7ba3ff;font-size:20px;font-weight:700;padding:8px 4px;min-width:140px}"
                "QSpinBox:focus{border-bottom:2px solid #4a8fe7}"
                "QSpinBox::up-button,QSpinBox::down-button{border:none;width:0px}"
            )
            cl.addWidget(self.min_stock_input)

            cl.addWidget(_fl("📅  تاريخ انتهاء الصلاحية"))
            self.expiry_input = QDateEdit()
            self.expiry_input.setCalendarPopup(True)
            self.expiry_input.setDate(QDate.currentDate())
            self.expiry_input.setDisplayFormat("yyyy-MM-dd")
            self.expiry_input.setFixedHeight(54)
            self.expiry_input.setStyleSheet(
                "QDateEdit{background:transparent;border:none;border-bottom:2px solid #2a3f5f;"
                "color:#f4848f;font-size:20px;font-weight:700;padding:8px 4px}"
                "QDateEdit:focus{border-bottom:2px solid #4a8fe7}"
                "QCalendarWidget{background:#141d2e;color:#f1f5f9;border:none}"
                "QCalendarWidget QAbstractItemView{color:#f1f5f9;background:#141d2e;selection-background-color:#4a8fe7}"
            )
            cl.addWidget(self.expiry_input)

        lc.addWidget(_card("📦", "المخزون", _setup_inv))
        lc.addStretch()

        # ═══ RIGHT ═══
        rc = QVBoxLayout()
        rc.setSpacing(10)

        def _setup_pricing(cl):
            cl.addWidget(_fl("سعر الشراء — للباكيت / العبوة"))
            self.purchase_price_input = QDoubleSpinBox()
            self.purchase_price_input.setRange(0, 99999999)
            self.purchase_price_input.setDecimals(2)
            self.purchase_price_input.setLocale(locale_iqd)
            self.purchase_price_input.setGroupSeparatorShown(True)
            self.purchase_price_input.setFixedHeight(54)
            self.purchase_price_input.setStyleSheet(
                "QDoubleSpinBox{background:transparent;border:none;border-bottom:2px solid #2a3f5f;"
                "color:#7ba3ff;font-size:26px;font-weight:800;padding:8px 4px}"
                "QDoubleSpinBox:focus{border-bottom:2px solid #4a8fe7}"
            )
            self.purchase_price_input.valueChanged.connect(self._update_auto_prices)
            cl.addWidget(self.purchase_price_input)

            # 2. Qty
            cl.addWidget(_fl("📦  الكمية في العبوة"))
            qty_row = QHBoxLayout()
            qty_row.setSpacing(8)
            self.qty_in_pack_input = QSpinBox()
            self.qty_in_pack_input.setRange(1, 99999)
            self.qty_in_pack_input.setValue(6)
            self.qty_in_pack_input.setFixedHeight(50)
            self.qty_in_pack_input.setLocale(locale_iqd)
            self.qty_in_pack_input.setGroupSeparatorShown(True)
            self.qty_in_pack_input.setStyleSheet(
                "QSpinBox{background:#0b1120;border:none;border-radius:8px;"
                "color:#7ba3ff;font-size:22px;font-weight:800;padding:4px 14px;min-width:80px}"
                "QSpinBox:focus{background:#162035}"
            )
            self.qty_in_pack_input.valueChanged.connect(self._update_auto_prices)
            qty_row.addWidget(self.qty_in_pack_input)

            for qval in [1, 6, 10, 12, 24, 50]:
                qb = QPushButton(str(qval))
                qb.setFixedSize(48, 48)
                qb.setCursor(Qt.PointingHandCursor)
                is_def = qval == 6
                bg = "#2a4a7a" if is_def else "#1e2d45"
                fc = "#8ab4ff" if is_def else "#7a8fb0"
                qb.setStyleSheet(
                    f"QPushButton{{background:{bg};color:{fc};border:none;"
                    f"border-radius:10px;font-size:17px;font-weight:700}}"
                    f"QPushButton:hover{{background:#2a4a7a;color:#b0ccff}}"
                )
                qb.clicked.connect(lambda checked, v=qval: self.qty_in_pack_input.setValue(v))
                qty_row.addWidget(qb)
            qty_row.addStretch()
            cl.addLayout(qty_row)

            # 3. Per-unit cost (auto)
            sep1 = QFrame()
            sep1.setFixedHeight(1)
            sep1.setStyleSheet("background:#1e2d45")
            cl.addWidget(sep1)

            cost_f = QFrame()
            cost_f.setStyleSheet("QFrame{background:#0b1120;border-radius:8px;padding:0}")
            cf_lay = QHBoxLayout(cost_f)
            cf_lay.setContentsMargins(14, 12, 14, 12)
            ci = QLabel("💊")
            ci.setStyleSheet("font-size:24px;background:transparent")
            cf_lay.addWidget(ci)
            cf_lay.addWidget(QLabel("تكلفة القطعة / الشريط"))
            cf_lay.itemAt(1).widget().setStyleSheet("font-size:14px;color:#4a6580;background:transparent")
            cf_lay.addStretch()
            self._per_unit_cost_lbl = QLabel("— د.ع")
            self._per_unit_cost_lbl.setStyleSheet("font-size:26px;font-weight:800;color:#7ba3ff;background:transparent")
            cf_lay.addWidget(self._per_unit_cost_lbl)
            cl.addWidget(cost_f)

            # 4. Profit %
            cl.addWidget(_fl("📈  نسبة الربح % — يحتسب تلقائياً"))
            pct_row = QHBoxLayout()
            pct_row.setSpacing(8)
            self.profit_pct_input = QDoubleSpinBox()
            self.profit_pct_input.setRange(0, 999)
            self.profit_pct_input.setDecimals(1)
            self.profit_pct_input.setValue(30.0)
            self.profit_pct_input.setSuffix(" %")
            self.profit_pct_input.setFixedHeight(50)
            self.profit_pct_input.setLocale(locale_iqd)
            self.profit_pct_input.setGroupSeparatorShown(True)
            self.profit_pct_input.setStyleSheet(
                "QDoubleSpinBox{background:#0b1120;border:none;border-radius:8px;"
                "color:#7ba3ff;font-size:22px;font-weight:800;padding:4px 14px;min-width:100px}"
                "QDoubleSpinBox:focus{background:#162035}"
            )
            self.profit_pct_input.valueChanged.connect(self._on_profit_pct_changed)
            pct_row.addWidget(self.profit_pct_input)
            pct_row.addStretch()
            cl.addLayout(pct_row)

            # 5. Sell price
            cl.addWidget(_fl("💵  سعر البيع — للقطعة / الشريط"))
            self.sale_price_input = QDoubleSpinBox()
            self.sale_price_input.setRange(0, 99999999)
            self.sale_price_input.setDecimals(2)
            self.sale_price_input.setLocale(locale_iqd)
            self.sale_price_input.setGroupSeparatorShown(True)
            self.sale_price_input.setFixedHeight(54)
            self.sale_price_input.setStyleSheet(
                "QDoubleSpinBox{background:transparent;border:none;border-bottom:2px solid #2a3f5f;"
                "color:#7ba3ff;font-size:26px;font-weight:800;padding:8px 4px}"
                "QDoubleSpinBox:focus{border-bottom:2px solid #4a8fe7}"
            )
            self.sale_price_input.valueChanged.connect(self._on_sell_price_changed)
            cl.addWidget(self.sale_price_input)

            # Summary
            sf = QFrame()
            sf.setStyleSheet("QFrame{background:#0b1120;border-radius:8px;padding:0}")
            sr = QHBoxLayout(sf)
            sr.setContentsMargins(16, 12, 16, 12)
            self._lbl_pack_price = QLabel("💼 سعر الباكيت")
            self._lbl_pack_price.setStyleSheet("font-size:15px;font-weight:600;color:#8899bb;background:transparent")
            sr.addWidget(self._lbl_pack_price)
            vsp = QFrame()
            vsp.setFixedWidth(1)
            vsp.setFixedHeight(24)
            vsp.setStyleSheet("background:#1e2d45")
            sr.addWidget(vsp)
            self._lbl_margin = QLabel("📈 هامش الربح")
            self._lbl_margin.setStyleSheet("font-size:15px;font-weight:600;color:#8899bb;background:transparent")
            sr.addWidget(self._lbl_margin)
            sr.addStretch()
            cl.addWidget(sf)

        rc.addWidget(_card("💰", "التسعير", _setup_pricing))
        rc.addStretch()

        body.addLayout(lc, 1)
        body.addLayout(rc, 1)
        main.addLayout(body, 1)

        # ── Buttons ──
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        save_btn = QPushButton("💾  حفظ")
        save_btn.setFixedHeight(50)
        save_btn.setStyleSheet(
            "QPushButton{font-size:18px;font-weight:700;background:#059669;"
            "color:white;border:none;border-radius:10px;padding:0 36px}"
            "QPushButton:hover{background:#047857}"
        )
        save_btn.clicked.connect(self._save)
        cancel_btn = QPushButton("إلغاء")
        cancel_btn.setFixedHeight(50)
        cancel_btn.setStyleSheet(
            "QPushButton{font-size:18px;font-weight:600;background:#334155;"
            "color:#94a3b8;border:none;border-radius:10px;padding:0 36px}"
            "QPushButton:hover{background:#475569;color:#f1f5f9}"
        )
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()
        main.addLayout(btn_row)

    # ── helpers ──────────────────────────────────────────────────
    @staticmethod
    def _make_editable_combo(items):
        """Return an editable QComboBox with autocomplete."""
        cb = QComboBox()
        cb.setEditable(True)
        cb.setInsertPolicy(QComboBox.NoInsert)
        cb.lineEdit().setPlaceholderText("اكتب للبحث…")
        for text, data in items:
            cb.addItem(text, data)
        texts = [t for t, _ in items]
        model = QStringListModel(texts, cb)
        comp = QCompleter(model, cb)
        comp.setCaseSensitivity(Qt.CaseInsensitive)
        comp.setFilterMode(Qt.MatchContains)
        comp.setCompletionMode(QCompleter.PopupCompletion)
        cb.setCompleter(comp)
        return cb

    def _update_auto_prices(self):
        """Recalculate cost + sell price from purchase/qty/profit%."""
        if getattr(self, '_updating', False):
            return
        self._updating = True

        purchase = to_decimal(self.purchase_price_input.value())
        qty = self.qty_in_pack_input.value() or 1
        pct = to_decimal(self.profit_pct_input.value())

        per_unit_cost = purchase / qty if qty else DECIMAL_ZERO
        sell_price = per_unit_cost * (Decimal("1") + pct / 100)
        pack_sell_price = sell_price * qty
        margin = ((sell_price * qty - purchase) / purchase * 100) if purchase else DECIMAL_ZERO

        self._per_unit_cost_lbl.setText(f"{format_currency(per_unit_cost)} د.ع")
        self.sale_price_input.setValue(float(sell_price))
        self._lbl_pack_price.setText(f"💼 سعر الباكيت: {format_currency(pack_sell_price)} د.ع")
        self._lbl_margin.setText(f"📈 هامش الربح: {format_currency(margin)} %")

        self._updating = False

    def _on_profit_pct_changed(self):
        if getattr(self, '_updating', False):
            return
        self._update_auto_prices()

    def _on_sell_price_changed(self):
        if getattr(self, '_updating', False):
            return
        self._updating = True

        purchase = to_decimal(self.purchase_price_input.value())
        qty = self.qty_in_pack_input.value() or 1
        sell_price = to_decimal(self.sale_price_input.value())

        per_unit_cost = purchase / qty if qty else DECIMAL_ZERO
        pct = ((sell_price - per_unit_cost) / per_unit_cost * 100) if per_unit_cost else DECIMAL_ZERO
        pack_sell_price = sell_price * qty
        margin = ((sell_price * qty - purchase) / purchase * 100) if purchase else DECIMAL_ZERO

        self.profit_pct_input.setValue(float(pct))
        self._per_unit_cost_lbl.setText(f"{format_currency(per_unit_cost)} د.ع")
        self._lbl_pack_price.setText(f"💼 سعر الباكيت: {format_currency(pack_sell_price)} د.ع")
        self._lbl_margin.setText(f"📈 هامش الربح: {format_currency(margin)} %")

        self._updating = False

    def _on_barcode_finished(self):
        """Silently check the DB for the barcode; fill fields if found."""
        if self.product:          # edit mode – skip lookup
            return
        # Guard against re-entrant calls (QMessageBox steals focus → fires editingFinished again)
        if getattr(self, '_barcode_checking', False):
            return
        barcode = self.barcode_input.text().strip()
        if not barcode:
            return
        # Don't re-check if we already processed this barcode
        if self._new_batch_mode and self._existing_product and self._existing_product.get("barcode") == barcode:
            return

        self._barcode_checking = True
        try:
            existing = self.product_ctrl.search_by_barcode(barcode)
            if not existing:
                self._barcode_status_lbl.setText("✅ جديد")
                self._barcode_status_lbl.setStyleSheet(
                    "font-size:13px;color:#10b981;background:transparent;padding:0 6px"
                )
                self._existing_product = None
                self._new_batch_mode = False
                return

            # ── Product found in DB ──
            existing = dict(existing)
            stock_qty = existing.get("stock_quantity", 0)

            self._barcode_status_lbl.setText(f"⚠️ موجود ({stock_qty} وحدة)")
            self._barcode_status_lbl.setStyleSheet(
                "font-size:13px;color:#f59e0b;background:transparent;padding:0 6px"
            )

            # Ask the user
            answer = QMessageBox.question(
                self,
                "مادة موجودة",
                f"الباركود مسجل مسبقاً:\n"
                f"  • الاسم : {existing.get('name', '')}\n"
                f"  • المخزون الحالي : {stock_qty} وحدة\n\n"
                "هل تريد إضافة وجبة جديدة (زيادة المخزون) ؟",
                QMessageBox.Yes | QMessageBox.No,
            )

            if answer == QMessageBox.Yes:
                self._existing_product = existing
                self._new_batch_mode = True
                # Pre-fill all fields from existing product silently
                self.name_input.setText(existing.get("name") or "")
                self.sci_name_input.setText(existing.get("scientific_name") or "")
                self.sale_price_input.setValue(float(existing.get("sale_price") or 0))
                self.purchase_price_input.setValue(float(existing.get("purchase_price") or 0))
                self.qty_in_pack_input.setValue(int(dict(existing).get("strips_per_pack", 6)))
                self.min_stock_input.setValue(int(existing.get("min_stock") or 10))
                self.stock_input.setValue(0)   # user enters only the NEW batch quantity
                self._update_auto_prices()
                # select category
                cat_id = existing.get("category_id")
                if cat_id:
                    idx = self.category_combo.findData(cat_id)
                    if idx >= 0:
                        self.category_combo.setCurrentIndex(idx)
                # select supplier
                sup_id = existing.get("supplier_id")
                if sup_id:
                    idx = self.supplier_combo.findData(sup_id)
                    if idx >= 0:
                        self.supplier_combo.setCurrentIndex(idx)
                # focus on the quantity field so the user enters new batch qty
                self.stock_input.setFocus()
                self._barcode_status_lbl.setText(f"📦 إضافة وجبة – مخزون حالي: {stock_qty}")
            else:
                self._existing_product = None
                self._new_batch_mode = False
                # Clear all fields so user can enter new product data
                self.barcode_input.clear()
                self._barcode_status_lbl.setText("")
                self.barcode_input.setFocus()
        finally:
            self._barcode_checking = False

    def _load_data(self, product):
        self.barcode_input.setText(product["barcode"] or "")
        self.name_input.setText(product["name"] or "")
        self.sci_name_input.setText(dict(product).get("scientific_name") or "")
        if dict(product).get("category_id"):
            idx = self.category_combo.findData(product["category_id"])
            if idx >= 0:
                self.category_combo.setCurrentIndex(idx)
        if dict(product).get("supplier_id"):
            idx = self.supplier_combo.findData(product["supplier_id"])
            if idx >= 0:
                self.supplier_combo.setCurrentIndex(idx)
        self.sale_price_input.setValue(float(product["sale_price"] or 0))
        self.purchase_price_input.setValue(float(product["purchase_price"] or 0))
        p = dict(product)
        self.qty_in_pack_input.setValue(int(p.get("strips_per_pack", 6)))
        self.stock_input.setValue(product["stock_quantity"] or 0)
        self.min_stock_input.setValue(product["min_stock"] or 10)
        self._update_auto_prices()
        if dict(product).get("expiry_date"):
            self.expiry_input.setDate(
                QDate.fromString(str(product["expiry_date"]), "yyyy-MM-dd")
            )

    def _generate_and_print_barcode(self):
        from PyQt5.QtWidgets import QInputDialog
        
        bc_text = self.barcode_input.text().strip()
        if not bc_text:
            bc_text = self.printer_manager.generate_random_barcode()
            self.barcode_input.setText(bc_text)
            
        prod_name = self.name_input.text().strip() or "مادة جديدة"
        
        copies, ok = QInputDialog.getInt(
            self, "طباعة الباركود", 
            "كم عدد الملصقات التي ترغب بطباعتها؟\n\n(للكارتون الكامل: 1، أو للعلب الفردية: حدد العدد)",
            1, 1, 1000, 1
        )
        
        if ok:
            printer_name = self.printer_manager.get_default_barcode_printer()
            if not printer_name:
                QMessageBox.warning(self, "تنبيه", "لم يتم تحديد طابعة الباركود في الإعدادات!")
                return
                
            success, msg = self.printer_manager.print_barcode(printer_name, bc_text, prod_name, copies)
            if success:
                QMessageBox.success(self, "نجاح", msg)
            else:
                QMessageBox.critical(self, "خطأ", msg)

    @safe_operation("عذراً، حدث خطأ أثناء حفظ المادة.")
    def _save(self):
        barcode = self.barcode_input.text().strip()
        name = self.name_input.text().strip()

        if not barcode:
            QMessageBox.warning(self, "خطأ", "يرجى إدخال الباركود")
            return
        if not name:
            QMessageBox.warning(self, "خطأ", "يرجى إدخال اسم المادة")
            return

        try:
            if self._new_batch_mode and self._existing_product:
                # ── New Batch: add stock to existing product ──
                batch_qty = self.stock_input.value()
                if batch_qty <= 0:
                    QMessageBox.warning(self, "تنبيه", "يرجى إدخال كمية الوجبة الجديدة (أكبر من صفر)")
                    self.stock_input.setFocus()
                    return
                existing_id = self._existing_product["id"]
                # Update stock quantity
                self.product_ctrl.update_stock(existing_id, batch_qty)
                # Also update purchase price / expiry if changed
                self.product_ctrl.update(existing_id, {
                    "purchase_price": to_decimal(self.purchase_price_input.value()),
                    "sale_price": to_decimal(self.sale_price_input.value()),
                    "strips_per_pack": self.qty_in_pack_input.value(),
                    "pieces_per_strip": 1,
                    "expiry_date": self.expiry_input.date().toString("yyyy-MM-dd"),
                    "min_stock": self.min_stock_input.value(),
                })
                # ── حذف تلقائي من الطلبية (في الخلفية) ──
                try:
                    OrderController().remove_by_name(existing.get("name", ""))
                except Exception:
                    pass
                self.accept()

            elif self.product:
                # ── Edit mode ──
                data = {
                    "barcode": barcode,
                    "name": name,
                    "scientific_name": self.sci_name_input.text().strip() or None,
                    "category_id": self.category_combo.currentData(),
                    "supplier_id": self.supplier_combo.currentData(),
                    "sale_price": to_decimal(self.sale_price_input.value()),
                    "purchase_price": to_decimal(self.purchase_price_input.value()),
                    "strips_per_pack": self.qty_in_pack_input.value(),
                    "pieces_per_strip": 1,
                    "stock_quantity": self.stock_input.value(),
                    "min_stock": self.min_stock_input.value(),
                    "expiry_date": self.expiry_input.date().toString("yyyy-MM-dd"),
                }
                self.product_ctrl.update(self.product["id"], data)
                self.accept()

            else:
                # ── New product ──
                data = {
                    "barcode": barcode,
                    "name": name,
                    "scientific_name": self.sci_name_input.text().strip() or None,
                    "category_id": self.category_combo.currentData(),
                    "supplier_id": self.supplier_combo.currentData(),
                    "sale_price": to_decimal(self.sale_price_input.value()),
                    "purchase_price": to_decimal(self.purchase_price_input.value()),
                    "strips_per_pack": self.qty_in_pack_input.value(),
                    "pieces_per_strip": 1,
                    "stock_quantity": self.stock_input.value(),
                    "min_stock": self.min_stock_input.value(),
                    "expiry_date": self.expiry_input.date().toString("yyyy-MM-dd"),
                }
                self.product_ctrl.create(data)
                # ── حذف تلقائي من الطلبية (في الخلفية) ──
                try:
                    OrderController().remove_by_name(name)
                except Exception:
                    pass
                self.accept()

        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"فشل الحفظ:\n{str(e)}")
