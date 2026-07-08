from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QComboBox, QDoubleSpinBox, QSpinBox,
    QAbstractItemView, QApplication, QFrame, QGraphicsDropShadowEffect,
    QSizePolicy, QCompleter, QDialog, QListWidget, QListWidgetItem,
    QScrollArea,
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QEvent, QStringListModel, QLocale, QPropertyAnimation, QEasingCurve, QRect
from PyQt5.QtGui import (
    QFont, QKeySequence, QColor, QPainter, QLinearGradient, QBrush,
)
from PyQt5.QtWidgets import QShortcut
from utils.modern_msgbox import ModernMessageBox as QMessageBox

from controllers.product_controller import ProductController
from controllers.sale_controller import SaleController
from controllers.customer_controller import CustomerController
from controllers.doctor_controller import DoctorController
from controllers.return_controller import ReturnController
from decimal import Decimal
from utils.decimal_handler import to_decimal, from_decimal, format_currency, DECIMAL_ZERO, round_up_to_250, round_down_to_250, round_to_nearest_250
from utils.logger import safe_operation


# ─── Helper: solid card frame with title and content layout ───
def _card(title, parent=None):
    f = QFrame(parent)
    f.setObjectName("posCard")
    f.setStyleSheet(
        "QFrame#posCard{background:#1e293b;border:1px solid #334155;border-radius:10px}"
    )
    layout = QVBoxLayout(f)
    layout.setContentsMargins(8, 6, 8, 6)
    layout.setSpacing(3)
    if title:
        lbl = QLabel(title)
        lbl.setStyleSheet("font-size:13px;font-weight:700;color:#cbd5e1;letter-spacing:0.5px")
        layout.addWidget(lbl)
    return f, layout


def _label(text, color="#cbd5e1", size=14, bold=False):
    lbl = QLabel(text)
    w = "700" if bold else "400"
    lbl.setStyleSheet(f"font-size:{size}px;font-weight:{w};color:{color};background:transparent")
    return lbl



def _inp_style(border="#334155", focus="#10b981", fs=15):
    return (
        f"QLineEdit{{"
        f"font-size:{fs}px;font-weight:600;padding:6px 10px;"
        f"background:#0f172a;border:2px solid {border};border-radius:10px;color:#f1f5f9;"
        f"selection-background-color:#10b98160"
        f"}}"
        f"QLineEdit:focus{{border-color:{focus}}}"
    )


def _combo_style(fs=14):
    return (
        f"QComboBox{{font-size:{fs}px;font-weight:600;padding:4px 8px;"
        f"background:#0f172a;border:2px solid #334155;border-radius:10px;color:#f1f5f9}}"
        f"QComboBox:focus{{border-color:#10b981}}"
        f"QComboBox::drop-down{{border:none;width:24px}}"
        f"QComboBox QAbstractItemView{{background:#1e293b;color:#f1f5f9;"
        f"font-size:{fs}px;selection-background:#10b98160}}"
    )


def _btn_style(bg="#059669", color="white", fs=16, h=44):
    return (
        f"QPushButton{{font-size:{fs}px;font-weight:700;padding:6px 14px;"
        f"background:{bg};color:{color};border:none;border-radius:10px;min-height:{h}px}}"
        f"QPushButton:hover{{background:{bg}dd}}"
        f"QPushButton:pressed{{background:{bg}aa}}"
    )


def _spin_style():
    return (
        "QSpinBox, QDoubleSpinBox{"
        "font-size:13px;font-weight:600;padding:2px 6px;"
        "background:#0f172a;border:2px solid #334155;border-radius:10px;color:#f1f5f9"
        "} QSpinBox:focus, QDoubleSpinBox:focus{border-color:#10b981}"
        "QSpinBox::up-button, QSpinBox::down-button,"
        "QDoubleSpinBox::up-button, QDoubleSpinBox::down-button{"
        "background:#1e293b;border:none;width:20px;subcontrol-position:right;"
        "} QSpinBox::up-arrow, QDoubleSpinBox::up-arrow{width:8px;height:8px}"
        "QSpinBox::down-arrow, QDoubleSpinBox::down-arrow{width:8px;height:8px}"
    )


def _pay_btn_style(color="#43e97b", fs=14):
    return (
        f"QPushButton{{font-size:{fs}px;font-weight:700;padding:4px 0;"
        f"background:#0f172a;border:2px solid {color}50;border-radius:10px;color:#f1f5f9;"
        f"min-height:30px}}"
        f"QPushButton:checked{{background:{color};border-color:{color};color:#0f172a}}"
        f"QPushButton:hover{{background:{color}40}}"
    )


# ═══════════════════════════════════════════════
# نافذة البيع الرئيسية - تصميم شاشة اللمس
# ═══════════════════════════════════════════════
class POSWidget(QWidget):
    sale_completed = pyqtSignal(int)
    print_sale = pyqtSignal(int)

    _PAY_COLORS = {"نقداً": "#43e97b", "بطاقة": "#667eea", "آجل": "#f093fb"}

    def __init__(self, user_data: dict, parent=None):
        super().__init__(parent)
        self.user_data = user_data
        self.product_ctrl = ProductController()
        self.sale_ctrl = SaleController()
        self.customer_ctrl = CustomerController()
        self.doc_ctrl = DoctorController()

        self.current_items = []
        self._last_scanned_product = None
        self._is_pack = False
        self.selected_customer = None
        self.selected_doctor = None
        self._doctor_discount = 0.0
        self._ignore_text_change = False
        self._last_added_item = None
        self._invoice_note = ""
        self._print_after_save = False
        self._payment_method = "نقداً"
        self._barcode_timer = None
        self._sp_cart_items = []
        self._return_mode = False
        self._return_sale_id = None
        self._return_panel_visible = False
        self.return_ctrl = ReturnController()

        self._setup_ui()
        self._load_doctors()
        self._setup_hotkeys()
        self._focus_barcode()
        # مؤقت دوري: يعيد التركيز للباركود كل 3 ثوانٍ إذا لم يكن أي حقل نصي محرر
        self._idle_timer = QTimer(self)
        self._idle_timer.setInterval(3000)
        self._idle_timer.timeout.connect(self._idle_focus_check)
        self._idle_timer.start()

    def _load_doctors(self):
        self.doctor_combo.clear()
        self.doctor_combo.addItem("— اختر طبيب —", 0)
        self._doctor_names = ["— اختر طبيب —"]
        for d in self.doc_ctrl.get_doctors_with_rules():
            self.doctor_combo.addItem(d["name"], d["id"])
            self._doctor_names.append(d["name"])
        # Make combo editable + searchable
        self.doctor_combo.setEditable(True)
        self.doctor_combo.setInsertPolicy(QComboBox.NoInsert)
        self.doctor_combo.lineEdit().setPlaceholderText("اكتب اسم الطبيب…")
        model = QStringListModel(self._doctor_names, self.doctor_combo)
        comp = QCompleter(model, self.doctor_combo)
        comp.setCaseSensitivity(Qt.CaseInsensitive)
        comp.setFilterMode(Qt.MatchContains)
        comp.setCompletionMode(QCompleter.PopupCompletion)
        self.doctor_combo.setCompleter(comp)

    def showEvent(self, event):
        super().showEvent(event)
        from database.connection import DatabaseManager
        db = DatabaseManager()
        deal_cost_setting = db.fetchone("SELECT setting_value FROM settings WHERE setting_key = 'show_doctor_deal_cost'")
        self._show_deal_cost = True if (deal_cost_setting and deal_cost_setting["setting_value"] == '1') else False
        # Auto-delete held invoices from previous days
        db.execute("DELETE FROM held_invoices WHERE date(created_at) < date('now')")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if getattr(self, '_search_panel', None) and self._search_panel_visible:
            pw = self.width()
            panel_w = int(pw * 0.7)
            self._search_panel.setGeometry(pw - panel_w, 0, panel_w, self.height())
            self._search_panel.raise_()

    # ─────────── paintEvent ───────────
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        bg = QLinearGradient(0, 0, 0, self.height())
        bg.setColorAt(0.0, QColor(15, 23, 42))
        bg.setColorAt(0.5, QColor(12, 19, 36))
        bg.setColorAt(1.0, QColor(10, 15, 30))
        p.fillRect(self.rect(), QBrush(bg))
        p.end()

    # ─────────── UI Construction ───────────
    def _setup_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(4)

        # ═══════════ Column 1: Cart ═══════════
        c1 = QVBoxLayout()
        c1.setSpacing(4)

        hdr1 = QHBoxLayout()
        hdr1.setContentsMargins(0, 0, 0, 0)
        hdr1.addWidget(_label("سلة المريض", "#e2e8f0", 18, True))
        hdr1.addStretch()
        self._sum_count_lbl = _label("0", "#94a3b8", 16)
        hdr1.addWidget(self._sum_count_lbl)
        c1.addLayout(hdr1)

        # Return mode banner (hidden by default)
        self._return_banner = QFrame()
        self._return_banner.setFixedHeight(40)
        self._return_banner.setStyleSheet(
            "QFrame{background:#134e4a;border:1px solid #14b8a6;border-radius:6px;}"
        )
        rbl = QHBoxLayout(self._return_banner)
        rbl.setContentsMargins(10, 0, 10, 0)
        self._return_label = QLabel("🔄 إرجاع فاتورة")
        self._return_label.setStyleSheet("font-size:14px;font-weight:700;color:#14b8a6;background:transparent;border:none;")
        rbl.addWidget(self._return_label)
        rbl.addStretch()
        self._return_exit_btn = QPushButton("✕")
        self._return_exit_btn.setFixedSize(30, 30)
        self._return_exit_btn.setCursor(Qt.PointingHandCursor)
        self._return_exit_btn.setStyleSheet(
            "QPushButton{font-size:16px;font-weight:700;color:#14b8a6;background:#134e4a;border:none;border-radius:15px;}"
            "QPushButton:hover{background:#115e59;color:white;}"
        )
        self._return_exit_btn.clicked.connect(self._exit_return_mode)
        rbl.addWidget(self._return_exit_btn)
        self._return_banner.setVisible(False)
        c1.addWidget(self._return_banner)

        self.invoice_table = QTableWidget()
        self.invoice_table.setColumnCount(8)
        self.invoice_table.setHorizontalHeaderLabels(["المنتج", "الوحدة", "الكمية", "السعر", "الإجمالي", "🏷", "خصم%", ""])
        self.invoice_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.invoice_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        for col in range(2, 8):
            self.invoice_table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self.invoice_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.invoice_table.verticalHeader().setVisible(False)
        self.invoice_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.invoice_table.setShowGrid(False)
        self.invoice_table.setStyleSheet(
            "QTableWidget{background:#1e293b;border:1px solid #334155;border-radius:8px;color:#f1f5f9}"
            "QHeaderView::section{background:#0f172a;color:#94a3b8;padding:8px;border:none;font-size:13px;font-weight:700}"
            "QTableWidget::item{padding:8px;border-bottom:1px solid #0f172a30;font-size:14px}"
            "QTableWidget::item:selected{background:#10b98130}"
        )
        c1.addWidget(self.invoice_table, 1)

        sf = QFrame()
        sf.setStyleSheet("QFrame{background:#064e3b20;border:1px solid #10b98140;border-radius:8px}")
        sl = QHBoxLayout(sf)
        sl.setContentsMargins(14, 8, 14, 8)
        sl.addStretch()
        sl.addWidget(_label("الإجمالي", "#94a3b8", 16))
        self._sum_total_lbl = _label("0", "#10b981", 26, True)
        sl.addWidget(self._sum_total_lbl)
        c1.addWidget(sf)

        sbr = QHBoxLayout()
        sbr.setSpacing(8)
        self._stat_items_lbl = _label("الأصناف: 0", "#64748b", 13)
        sbr.addWidget(self._stat_items_lbl)
        self._stat_qty_lbl = _label("الكميات: 0", "#64748b", 13)
        sbr.addWidget(self._stat_qty_lbl)
        self._stat_avg_lbl = _label("المتوسط: 0.00", "#64748b", 13)
        sbr.addWidget(self._stat_avg_lbl)
        sbr.addStretch()
        c1.addLayout(sbr)

        w1 = QWidget()
        w1.setLayout(c1)
        w1.setStyleSheet("QWidget{background:#0f172a40;border-radius:8px}")

        # ═══════════ Column 2: Control, Scanner, and Finance ═══════════
        c2 = QVBoxLayout()
        c2.setSpacing(0)
        c2.setContentsMargins(0, 0, 0, 0)

        # Single card panel for all control inputs
        f_main, l_main = _card(None)
        l_main.setSpacing(3)
        l_main.setContentsMargins(12, 8, 12, 8)

        # 1. Top: Patient Selectors
        pc_row = QHBoxLayout()
        pc_row.setSpacing(4)
        pc_row.addWidget(_label("طبيب", "#cbd5e1", 14, True))
        self.doctor_combo = QComboBox()
        self.doctor_combo.setStyleSheet(_combo_style())
        self.doctor_combo.setFixedHeight(42)
        self.doctor_combo.currentIndexChanged.connect(self._on_doctor_combo_changed)
        pc_row.addWidget(self.doctor_combo, 3)
        pc_row.addSpacing(6)
        pc_row.addWidget(_label("عميل", "#cbd5e1", 14, True))
        self.customer_input = QLineEdit()
        self.customer_input.setPlaceholderText("بحث...")
        self.customer_input.setStyleSheet(_inp_style())
        self.customer_input.setFixedHeight(42)
        self.customer_input.returnPressed.connect(self._on_customer_search)
        pc_row.addWidget(self.customer_input, 2)
        self.customer_clear_btn = QPushButton("✕")
        self.customer_clear_btn.setFixedSize(36, 36)
        self.customer_clear_btn.setStyleSheet(
            "QPushButton{background:#7f1d1d;color:#fca5a5;border:none;border-radius:6px;font-size:15px;font-weight:700}"
            "QPushButton:hover{background:#991b1b}"
        )
        self.customer_clear_btn.clicked.connect(self._clear_customer)
        pc_row.addWidget(self.customer_clear_btn)
        l_main.addLayout(pc_row)

        sel_row = QHBoxLayout()
        sel_row.setContentsMargins(2, 0, 2, 0)
        self.doctor_label = _label("", "#94a3b8", 12)
        sel_row.addWidget(self.doctor_label)
        sel_row.addStretch()
        self.customer_label = _label("", "#94a3b8", 12)
        sel_row.addWidget(self.customer_label)
        l_main.addLayout(sel_row)

        # خط فاصل بمسافة صفرية
        div1 = QFrame()
        div1.setFixedHeight(1)
        div1.setStyleSheet("background:#334155")
        l_main.addWidget(div1)
        l_main.setSpacing(2)  # تضييق المسافة فقط لمنطقة بيانات العلاج

        # 2. Middle: Barcode Scanner & Product Details (بيانات العلاج)
        lbl_title = _label("بيانات العلاج", "#cbd5e1", 13, True)
        lbl_title.setAlignment(Qt.AlignCenter)
        lbl_title.setContentsMargins(0, 1, 0, 1)
        l_main.addWidget(lbl_title)
        
        self.barcode_input = QLineEdit()
        self.barcode_input.setPlaceholderText("امسح الباركود...")
        self.barcode_input.setStyleSheet(_inp_style(fs=18))
        self.barcode_input.setFixedHeight(50)
        self.barcode_input.returnPressed.connect(self._on_barcode_scanned)
        self.barcode_input.textChanged.connect(self._on_barcode_changed)
        l_main.addWidget(self.barcode_input)

        self.search_results = QTableWidget()
        self.search_results.setColumnCount(4)
        self.search_results.setHorizontalHeaderLabels(["باركود", "الاسم", "السعر", "المخزون"])
        self.search_results.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.search_results.setMaximumHeight(120)
        self.search_results.setVisible(False)
        self.search_results.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.search_results.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.search_results.itemClicked.connect(self._on_search_result_click)
        self.search_results.verticalHeader().setVisible(False)
        self.search_results.setStyleSheet(
            "QTableWidget{background:#0f172a;border:1px solid #334155;border-radius:6px;color:#f1f5f9}"
            "QHeaderView::section{background:#1e293b;color:#94a3b8;padding:4px;border:none;font-size:12px}"
            "QTableWidget::item{padding:6px;font-size:13px}"
            "QTableWidget::item:selected{background:#10b98140}"
        )
        l_main.addWidget(self.search_results)

        self._product_name_lbl = _label("—", "#f1f5f9", 22, True)
        self._product_name_lbl.setAlignment(Qt.AlignCenter)
        l_main.addWidget(self._product_name_lbl)

        pr_row = QHBoxLayout()
        pr_row.setSpacing(8)
        pr_row.setAlignment(Qt.AlignCenter)
        self._product_price_lbl = _label("—", "#60a5fa", 24, True)
        pr_row.addWidget(self._product_price_lbl)
        pr_row.addWidget(_label("السعر:", "#94a3b8", 15, True))
        l_main.addLayout(pr_row)

        st_row = QHBoxLayout()
        st_row.setSpacing(8)
        st_row.setAlignment(Qt.AlignCenter)
        self._product_stock_lbl = _label("—", "#ef4444", 24, True)
        st_row.addWidget(self._product_stock_lbl)
        st_row.addWidget(_label("المخزون:", "#94a3b8", 15, True))
        l_main.addLayout(st_row)

        # ── Unit Selector ──
        unit_row = QHBoxLayout()
        unit_row.setSpacing(6)
        unit_row.setAlignment(Qt.AlignCenter)
        unit_row.addWidget(_label("نوع البيع:", "#94a3b8", 14, True))
        self._btn_pack = QPushButton("📦  علبة")
        self._btn_pack.setCheckable(True)
        self._btn_pack.setFixedSize(90, 44)
        self._btn_pack.setCursor(Qt.PointingHandCursor)
        self._btn_unit = QPushButton("💊  مفرد")
        self._btn_unit.setCheckable(True)
        self._btn_unit.setChecked(True)
        self._btn_unit.setFixedSize(90, 44)
        self._btn_unit.setCursor(Qt.PointingHandCursor)
        btn_style = (
            "QPushButton{background:#1e293b;color:#94a3b8;border:2px solid #334155;"
            "border-radius:10px;font-size:15px;font-weight:700}"
            "QPushButton:hover{background:#334155;color:#f1f5f9;border-color:#60a5fa}"
            "QPushButton:checked{background:#1e3a5f;color:#38bdf8;border-color:#38bdf8}"
        )
        self._btn_pack.setStyleSheet(btn_style)
        self._btn_unit.setStyleSheet(btn_style)
        self._btn_pack.clicked.connect(lambda: self._set_sell_unit(False))
        self._btn_unit.clicked.connect(lambda: self._set_sell_unit(True))
        unit_row.addWidget(self._btn_pack)
        unit_row.addWidget(self._btn_unit)

        self._unit_qty_label = QLabel("1")
        self._unit_qty_label.setFixedSize(60, 44)
        self._unit_qty_label.setAlignment(Qt.AlignCenter)
        self._unit_qty_label.setStyleSheet(
            "QLabel{font-size:18px;font-weight:900;color:#38bdf8;"
            "background:#0f172a;border:2px solid #38bdf8;border-radius:8px;}"
        )
        self._unit_qty_label.setVisible(True)
        self._unit_qty_minus = QPushButton("−")
        self._unit_qty_minus.setFixedSize(36, 44)
        self._unit_qty_minus.setCursor(Qt.PointingHandCursor)
        self._unit_qty_minus.setStyleSheet(
            "QPushButton{font-size:20px;font-weight:900;color:#f1f5f9;"
            "background:#1e293b;border:2px solid #38bdf8;border-radius:8px;}"
            "QPushButton:hover{background:#334155;}"
        )
        self._unit_qty_minus.setVisible(True)
        self._unit_qty_plus = QPushButton("+")
        self._unit_qty_plus.setFixedSize(36, 44)
        self._unit_qty_plus.setCursor(Qt.PointingHandCursor)
        self._unit_qty_plus.setStyleSheet(
            "QPushButton{font-size:20px;font-weight:900;color:#f1f5f9;"
            "background:#1e293b;border:2px solid #38bdf8;border-radius:8px;}"
            "QPushButton:hover{background:#334155;}"
        )
        self._unit_qty_plus.setVisible(True)
        self._unit_qty_minus.clicked.connect(self._unit_qty_dec)
        self._unit_qty_plus.clicked.connect(self._unit_qty_inc)
        unit_row.addWidget(self._unit_qty_minus)
        unit_row.addWidget(self._unit_qty_label)
        unit_row.addWidget(self._unit_qty_plus)
        self._manual_search_btn = QPushButton("🔍 بحث يدوي")
        self._manual_search_btn.setFixedHeight(48)
        self._manual_search_btn.setCursor(Qt.PointingHandCursor)
        self._manual_search_btn.setStyleSheet(
            "QPushButton{font-size:14px;font-weight:800;padding:0 18px;"
            "background:#7c3aed;color:white;border:2px solid #a855f7;border-radius:10px;}"
            "QPushButton:hover{background:#6d28d9;border-color:#c084fc;}"
        )
        self._manual_search_btn.clicked.connect(self._open_manual_search)
        unit_row.addWidget(self._manual_search_btn)

        # Hold button (next to search)
        self.hold_btn = QPushButton("⏸ تعليق")
        self.hold_btn.setFixedHeight(48)
        self.hold_btn.setCursor(Qt.PointingHandCursor)
        self.hold_btn.setStyleSheet(
            "QPushButton{font-size:14px;font-weight:800;padding:0 14px;"
            "background:#0d9488;color:white;border:2px solid #14b8a6;border-radius:10px;margin:0 4px;}"
            "QPushButton:hover{background:#0f766e;border-color:#0d9488;}"
        )
        self.hold_btn.setToolTip("تعليق الفاتورة لحين عودة الزبون")
        self.hold_btn.clicked.connect(self._hold_invoice)
        unit_row.addWidget(self.hold_btn)

        self.held_btn = QPushButton("📋")
        self.held_btn.setFixedHeight(48)
        self.held_btn.setCursor(Qt.PointingHandCursor)
        self.held_btn.setStyleSheet(
            "QPushButton{font-size:16px;font-weight:800;padding:0 12px;"
            "background:#0d9488;color:white;border:2px solid #14b8a6;border-radius:10px;}"
            "QPushButton:hover{background:#0f766e;border-color:#0d9488;}"
        )
        self.held_btn.setToolTip("الفواتير المعلقة")
        self.held_btn.clicked.connect(self._show_held_invoices)
        unit_row.addWidget(self.held_btn)

        unit_row.addStretch()
        l_main.addLayout(unit_row)

        # ── Deal/Discount Info Frame ──
        self._deal_frame = QFrame()
        self._deal_frame.setVisible(False)
        dl = QVBoxLayout(self._deal_frame)
        dl.setContentsMargins(10, 4, 10, 4)
        dl.setSpacing(2)

        self._deal_title_lbl = _label("", "#a78bfa", 14, True)
        self._deal_title_lbl.setAlignment(Qt.AlignCenter)
        dl.addWidget(self._deal_title_lbl)

        self._deal_new_lbl = _label("", "#f1f5f9", 18, True)
        self._deal_new_lbl.setAlignment(Qt.AlignCenter)
        dl.addWidget(self._deal_new_lbl)

        l_main.addWidget(self._deal_frame)

        self.undo_btn = QPushButton("↩ تراجع")
        self.undo_btn.setStyleSheet(_btn_style("#334155", "#94a3b8", 15, 42))
        self.undo_btn.setEnabled(False)
        self.undo_btn.clicked.connect(self._undo_last_item)
        l_main.addWidget(self.undo_btn)

        # Space divider
        div2 = QFrame()
        div2.setFixedHeight(1)
        div2.setStyleSheet("background:#334155")
        l_main.addWidget(div2)

        # 3. Bottom: Finance fields
        l_main.addWidget(_label("المالية", "#cbd5e1", 15, True))

        def _display_box(color="#f1f5f9", border_color="#334155", bg="#0f172a", size=19):
            lbl = QLabel("0")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(
                f"QLabel{{"
                f"font-size:{size}px;font-weight:800;color:{color};"
                f"background:{bg};border:2px solid {border_color};border-radius:12px;padding:4px;"
                f"}}"
            )
            lbl.setFixedHeight(48)
            return lbl

        def _editable_box(color="#f1f5f9", border_color="#334155", bg="#0f172a", size=19):
            box = QDoubleSpinBox()
            box.setRange(0, 9999999)
            box.setDecimals(0)
            box.setAlignment(Qt.AlignCenter)
            box.setButtonSymbols(QDoubleSpinBox.NoButtons)
            box.setLocale(QLocale(QLocale.English, QLocale.UnitedStates))
            box.setStyleSheet(
                f"QDoubleSpinBox{{"
                f"font-size:{size}px;font-weight:800;color:{color};"
                f"background:{bg};border:2px solid {border_color};border-radius:12px;padding:4px;"
                f"}}"
                f"QDoubleSpinBox:focus{{border-color:#10b981;background:#111827;}}"
            )
            box.setFixedHeight(48)
            return box

        # Create two-column layout inside the card
        fin_cols = QHBoxLayout()
        fin_cols.setSpacing(16)

        left_col = QVBoxLayout()
        left_col.setSpacing(10)

        right_col = QVBoxLayout()
        right_col.setSpacing(10)

        # Helper to align layouts of rows
        def _add_row(layout, label_text, widget):
            r = QHBoxLayout()
            r.setSpacing(6)
            lbl = _label(label_text, "#cbd5e1", 15, True)
            lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            r.addWidget(widget, 1)
            r.addWidget(lbl)
            layout.addLayout(r)

        # Right Column Widgets:
        # 1. إجمالي العلاج
        self._sum_subtotal_lbl = _editable_box("#38bdf8", "#334155", "#0f172a", 19)
        self._sum_subtotal_lbl.valueChanged.connect(self._update_totals_from_subtotal)
        self._sum_subtotal_lbl.editingFinished.connect(self._focus_barcode)
        _add_row(right_col, "إجمالي العلاج", self._sum_subtotal_lbl)

        # 2. الخصم
        discount_layout = QHBoxLayout()
        discount_layout.setSpacing(4)

        self.discount_amount_input = _editable_box("#fda4af", "#334155", "#0f172a", 19)
        self.discount_amount_input.valueChanged.connect(self._update_totals_from_discount_amt)
        self.discount_amount_input.editingFinished.connect(self._focus_barcode)
        discount_layout.addWidget(self.discount_amount_input, 1)

        self._discount_pct_lbl = _label("% 0.0", "#94a3b8", 14, True)
        self._discount_pct_lbl.setAlignment(Qt.AlignCenter)
        discount_layout.addWidget(self._discount_pct_lbl)

        discount_container = QWidget()
        discount_container.setLayout(discount_layout)
        discount_container.setStyleSheet("background:transparent;border:none;padding:0;")
        _add_row(right_col, "الخصم", discount_container)

        # 3. صافي القيمة (الكلي)
        self._card3_total_lbl = _editable_box("#34d399", "#334155", "#0f172a", 21)
        self._card3_total_lbl.valueChanged.connect(self._update_totals_from_total)
        self._card3_total_lbl.editingFinished.connect(self._focus_barcode)
        _add_row(right_col, "صافي القيمة", self._card3_total_lbl)

        # Left Column Widgets:
        # 1. الباقي للصيدلية
        self._sum_remain_lab_lbl = _display_box("#f87171", "#334155", "#0f172a", 19)
        _add_row(left_col, "الباقي للصيدلية", self._sum_remain_lab_lbl)

        # 2. الباقي للمريض
        self._sum_remain_patient_lbl = _display_box("#2dd4bf", "#334155", "#0f172a", 19)
        _add_row(left_col, "الباقي للمريض", self._sum_remain_patient_lbl)

        # 3. المدفوع (auto-fill = net total, read-only)
        self.paid_input = QDoubleSpinBox()
        self.paid_input.setRange(0, 9999999)
        self.paid_input.setDecimals(0)
        self.paid_input.setReadOnly(True)
        self.paid_input.setButtonSymbols(QDoubleSpinBox.NoButtons)
        self.paid_input.setLocale(QLocale(QLocale.English, QLocale.UnitedStates))
        self.paid_input.setStyleSheet(
            "QDoubleSpinBox{"
            "font-size:18px;font-weight:800;padding:4px;text-align:center;"
            "background:#0f172a;border:2px solid #10b98140;border-radius:8px;color:#10b981;"
            "}"
            "QDoubleSpinBox::up-button, QDoubleSpinBox::down-button{width:0;height:0;}"
        )
        self.paid_input.setFixedHeight(48)
        _add_row(left_col, "المدفوع ✓", self.paid_input)

        # 4. Buttons Layout inside Left Column
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)
        btn_layout.setContentsMargins(0, 8, 0, 0)

        # Checkmark Button (Save and Print)
        self.save_print_btn = QPushButton("✓")
        self.save_print_btn.setStyleSheet(_btn_style("#dc2626", "white", 19, 44))
        self.save_print_btn.setToolTip("حفظ وطباعة (Ctrl+P)")
        self.save_print_btn.setCursor(Qt.PointingHandCursor)
        self.save_print_btn.clicked.connect(self._save_and_print)

        # Return Arrow Button (Clear)
        self.clear_btn = QPushButton("↩")
        self.clear_btn.setStyleSheet(_btn_style("#0d9488", "white", 19, 44))
        self.clear_btn.setToolTip("تفريغ (F6)")
        self.clear_btn.setCursor(Qt.PointingHandCursor)
        self.clear_btn.clicked.connect(self._clear_invoice)

        # Floppy Disk Button (Save Only)
        self.save_btn = QPushButton("💾")
        self.save_btn.setStyleSheet(_btn_style("#2563eb", "white", 19, 44))
        self.save_btn.setToolTip("حفظ الفاتورة (F5)")
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.clicked.connect(self._save_invoice)

        btn_layout.addWidget(self.save_print_btn)
        btn_layout.addWidget(self.clear_btn)
        btn_layout.addWidget(self.save_btn)

        # Return button
        self.return_btn = QPushButton("🔄 إرجاع")
        self.return_btn.setStyleSheet(_btn_style("#0d9488", "white", 14, 44))
        self.return_btn.setToolTip("إرجاع فاتورة")
        self.return_btn.setCursor(Qt.PointingHandCursor)
        self.return_btn.clicked.connect(self._toggle_return_panel)
        btn_layout.addWidget(self.return_btn)
        left_col.addLayout(btn_layout)

        # Assemble columns inside card
        fin_cols.addLayout(left_col, 1)
        fin_cols.addLayout(right_col, 1)
        l_main.addLayout(fin_cols)

        # Payment methods buttons below the two columns
        pb = QHBoxLayout()
        pb.setSpacing(4)
        pb.setContentsMargins(0, 8, 0, 0)
        self._pay_btns = {}
        for m, c in self._PAY_COLORS.items():
            btn = QPushButton(m)
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(_pay_btn_style(c, 14))
            btn.clicked.connect(lambda ch, mm=m: self._on_pay_btn(mm))
            self._pay_btns[m] = btn
            pb.addWidget(btn)
        self._pay_btns["نقداً"].setChecked(True)
        l_main.addLayout(pb)

        c2.addWidget(f_main)

        w2 = QWidget()
        w2.setLayout(c2)

        root.addWidget(w1, 55)
        root.addWidget(w2, 45)

        # ═══════════ Column 3: Search Panel (glass slide overlay, NOT in layout) ═══════════
        self._search_panel = QFrame(self)
        self._search_panel.setGeometry(0, 0, 0, 0)
        self._search_panel.setStyleSheet("""
            QFrame{
                background:qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 rgba(88,28,135,240), stop:0.5 rgba(76,29,149,235),
                    stop:1 rgba(107,33,168,230));
                border-left:3px solid #a855f7;
            }
        """)
        sp_lay = QVBoxLayout(self._search_panel)
        sp_lay.setContentsMargins(0, 0, 0, 0)
        sp_lay.setSpacing(0)

        # Header
        sp_hdr = QFrame()
        sp_hdr.setFixedHeight(64)
        sp_hdr.setStyleSheet("""
            QFrame{
                background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 rgba(126,34,206,200), stop:1 rgba(147,51,234,180));
                border-bottom:2px solid #a855f7;
            }
        """)
        sp_hdr_lay = QHBoxLayout(sp_hdr)
        sp_hdr_lay.setContentsMargins(18, 10, 18, 10)
        sp_title = QLabel("🔮 بحث المواد غير المكودة")
        sp_title.setStyleSheet("font-size:22px;font-weight:900;color:#f1f5f9;background:transparent;border:none;letter-spacing:1px;")
        sp_hdr_lay.addWidget(sp_title)
        sp_hdr_lay.addStretch()
        self._sp_close = QPushButton("✕")
        self._sp_close.setFixedSize(44, 44)
        self._sp_close.setCursor(Qt.PointingHandCursor)
        self._sp_close.setStyleSheet("""
            QPushButton{
                background:qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 #dc2626, stop:1 #b91c1c);
                color:white;border:none;border-radius:12px;
                font-size:22px;font-weight:900;
            }
            QPushButton:hover{
                background:qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 #ef4444, stop:1 #dc2626);
            }
        """)
        self._sp_close.clicked.connect(self._toggle_search_panel)
        sp_hdr_lay.addWidget(self._sp_close)
        sp_lay.addWidget(sp_hdr)

        # Search input
        search_frame = QFrame()
        search_frame.setStyleSheet("QFrame{background:transparent;margin:0 14px;}")
        sf_lay = QVBoxLayout(search_frame)
        sf_lay.setContentsMargins(0, 10, 0, 4)
        sf_lay.setSpacing(0)
        self._sp_search = QLineEdit()
        self._sp_search.setPlaceholderText("🔍 اكتب اسم المادة للبحث...")
        self._sp_search.setStyleSheet("""
            QLineEdit{
                font-size:20px;padding:14px 18px;
                background:rgba(30,27,75,230);
                border:2px solid #7c3aed;
                border-radius:14px;
                color:#f1f5f9;
            }
            QLineEdit:focus{
                border-color:#a855f7;
                background:rgba(30,27,75,250);
            }
        """)
        self._sp_search.setFixedHeight(58)
        self._sp_search.textChanged.connect(self._sp_filter_cards)
        sf_lay.addWidget(self._sp_search)
        sp_lay.addWidget(search_frame)

        # Cart header
        sp_cart_hdr = QHBoxLayout()
        sp_cart_hdr.setContentsMargins(18, 4, 18, 4)
        self._sp_cart_title = QLabel("🛒 السلة (0)")
        self._sp_cart_title.setStyleSheet("font-size:17px;font-weight:800;color:#c084fc;background:transparent;border:none;")
        sp_cart_hdr.addWidget(self._sp_cart_title)
        sp_cart_hdr.addStretch()
        sp_clear = QPushButton("🗑️ تفريغ")
        sp_clear.setFixedSize(100, 36)
        sp_clear.setCursor(Qt.PointingHandCursor)
        sp_clear.setStyleSheet("""
            QPushButton{
                font-size:13px;font-weight:800;
                background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #0d9488, stop:1 #0f766e);
                color:white;border:none;border-radius:9px;
            }
            QPushButton:hover{
                background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #0d9488, stop:1 #0d9488);
            }
        """)
        sp_clear.clicked.connect(self._sp_clear_cart)
        sp_cart_hdr.addWidget(sp_clear)
        sp_lay.addLayout(sp_cart_hdr)

        self._sp_cart = QListWidget()
        self._sp_cart.setMinimumHeight(90)
        self._sp_cart.setMaximumHeight(140)
        self._sp_cart.setStyleSheet("""
            QListWidget{
                background:rgba(30,27,75,220);
                border:2px solid #6d28d9;
                border-radius:10px;
                color:#f1f5f9;
                font-size:14px;
                margin:0 18px;
                padding:4px;
            }
            QListWidget::item{
                padding:8px 14px;
                border-bottom:1px solid rgba(107,33,168,150);
                border-radius:6px;
            }
            QListWidget::item:hover{
                background:rgba(124,58,237,100);
            }
        """)
        sp_lay.addWidget(self._sp_cart)

        # Scrollable cards
        sp_scroll = QScrollArea()
        sp_scroll.setWidgetResizable(True)
        sp_scroll.viewport().setStyleSheet("background:transparent;")
        sp_scroll.setStyleSheet("""
            QScrollArea{background:transparent;border:none;}
            QScrollBar:vertical{width:6px;background:transparent;}
            QScrollBar::handle:vertical{background:#6d28d9;border-radius:3px;}
            QScrollBar::handle:vertical:hover{background:#a855f7;}
            QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}
        """)
        self._sp_cards_widget = QWidget()
        self._sp_cards_widget.setStyleSheet("background:transparent;")
        self._sp_cards_widget.setMinimumHeight(200)
        self._sp_cards_layout = QGridLayout(self._sp_cards_widget)
        self._sp_cards_layout.setSpacing(6)
        self._sp_cards_layout.setContentsMargins(14, 6, 14, 6)
        sp_scroll.setWidget(self._sp_cards_widget)
        sp_lay.addWidget(sp_scroll, 1)

        # Status bar
        sp_status = QFrame()
        sp_status.setFixedHeight(36)
        sp_status.setStyleSheet("QFrame{background:rgba(88,28,135,180);border-top:1px solid #6d28d9;}")
        st_lay = QHBoxLayout(sp_status)
        st_lay.setContentsMargins(18, 0, 18, 0)
        self._sp_count_lbl = QLabel("0 مادة")
        self._sp_count_lbl.setStyleSheet("font-size:13px;font-weight:600;color:#c084fc;background:transparent;border:none;")
        st_lay.addWidget(self._sp_count_lbl)
        st_lay.addStretch()
        sp_lay.addWidget(sp_status)

        # Bottom buttons
        sp_btns = QHBoxLayout()
        sp_btns.setContentsMargins(18, 10, 18, 16)
        sp_confirm = QPushButton("✅ إرسال للسلة")
        sp_confirm.setFixedHeight(52)
        sp_confirm.setCursor(Qt.PointingHandCursor)
        sp_confirm.setStyleSheet("""
            QPushButton{
                font-size:17px;font-weight:900;
                background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #7c3aed, stop:1 #6d28d9);
                color:white;border:2px solid #a855f7;border-radius:12px;
            }
            QPushButton:hover{
                background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #8b5cf6, stop:1 #7c3aed);
                border-color:#c084fc;
            }
        """)
        sp_confirm.clicked.connect(self._sp_confirm)
        sp_btns.addWidget(sp_confirm)
        sp_cancel = QPushButton("✖️ إلغاء")
        sp_cancel.setFixedHeight(52)
        sp_cancel.setCursor(Qt.PointingHandCursor)
        sp_cancel.setStyleSheet("""
            QPushButton{
                font-size:17px;font-weight:900;
                background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #4b5563, stop:1 #374151);
                color:white;border:2px solid #6b7280;border-radius:12px;
            }
            QPushButton:hover{
                background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #6b7280, stop:1 #4b5563);
                border-color:#9ca3af;
            }
        """)
        sp_cancel.clicked.connect(self._toggle_search_panel)
        sp_btns.addWidget(sp_cancel)
        sp_lay.addLayout(sp_btns)

        # NOTE: _search_panel is an overlay child (no layout), positioned via _toggle_search_panel
        self._search_panel.raise_()
        self._search_panel_visible = False

        # ═══════════ Return Panel (overlay, shows today's invoices) ═══════════
        self._return_panel = QFrame(self)
        self._return_panel.setGeometry(0, 0, 0, 0)
        self._return_panel.setStyleSheet("""
            QFrame{
                background:qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 rgba(19,78,74,240), stop:0.5 rgba(15,118,110,235),
                    stop:1 rgba(13,148,136,230));
                border-left:3px solid #14b8a6;
            }
        """)
        rp_lay = QVBoxLayout(self._return_panel)
        rp_lay.setContentsMargins(0, 0, 0, 0)
        rp_lay.setSpacing(0)

        # Header
        rp_hdr = QFrame()
        rp_hdr.setFixedHeight(64)
        rp_hdr.setStyleSheet("""
            QFrame{
                background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 rgba(13,148,136,200), stop:1 rgba(15,118,110,180));
                border-bottom:2px solid #14b8a6;
            }
        """)
        rp_hdr_lay = QHBoxLayout(rp_hdr)
        rp_hdr_lay.setContentsMargins(18, 10, 18, 10)
        rp_title = QLabel("🔄 إرجاع فاتورة - فواتير اليوم")
        rp_title.setStyleSheet("font-size:22px;font-weight:900;color:#f1f5f9;background:transparent;border:none;")
        rp_hdr_lay.addWidget(rp_title)
        rp_hdr_lay.addStretch()
        self._rp_close = QPushButton("✕")
        self._rp_close.setFixedSize(44, 44)
        self._rp_close.setCursor(Qt.PointingHandCursor)
        self._rp_close.setStyleSheet(
            "QPushButton{font-size:20px;font-weight:700;color:#14b8a6;background:#134e4a;border:none;border-radius:22px;}"
            "QPushButton:hover{background:#115e59;color:white;}"
        )
        self._rp_close.clicked.connect(self._toggle_return_panel)
        rp_hdr_lay.addWidget(self._rp_close)
        rp_lay.addWidget(rp_hdr)

        # Search input
        self._rp_search = QLineEdit()
        self._rp_search.setPlaceholderText("🔍 ابحث عن فاتورة...")
        self._rp_search.setFixedHeight(48)
        self._rp_search.setStyleSheet("""
            QLineEdit{font-size:18px;font-weight:600;padding:8px 16px;
                background:rgba(255,255,255,0.1);color:#f1f5f9;border:2px solid #14b8a660;
                border-radius:10px;margin:10px 14px;}
            QLineEdit:focus{border-color:#14b8a6;}
        """)
        self._rp_search.textChanged.connect(self._rp_filter_invoices)
        rp_lay.addWidget(self._rp_search)

        # Scroll area for invoice cards
        self._rp_scroll = QScrollArea()
        self._rp_scroll.setWidgetResizable(True)
        self._rp_scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        self._rp_container = QWidget()
        self._rp_container.setStyleSheet("background:transparent;")
        self._rp_grid = QVBoxLayout(self._rp_container)
        self._rp_grid.setContentsMargins(14, 10, 14, 10)
        self._rp_grid.setSpacing(8)
        self._rp_scroll.setWidget(self._rp_container)
        rp_lay.addWidget(self._rp_scroll)

        # Admin delete invoice button
        if self.user_data.get("role") == "admin":
            self._rp_delete_btn = QPushButton("🗑️ حذف فاتورة (مدير فقط)")
            self._rp_delete_btn.setFixedHeight(48)
            self._rp_delete_btn.setCursor(Qt.PointingHandCursor)
            self._rp_delete_btn.setStyleSheet("""
                QPushButton{font-size:16px;font-weight:700;
                    background:#134e4a;color:#14b8a6;border:2px solid #14b8a660;
                    border-radius:10px;margin:6px 14px;}
                QPushButton:hover{background:#115e59;color:white;}
            """)
            self._rp_delete_btn.clicked.connect(self._admin_delete_invoice)
            rp_lay.addWidget(self._rp_delete_btn)

        self._return_panel.raise_()
        self._return_panel_visible = False

    # ──────────────────────────────────────────
    # Payment method
    # ──────────────────────────────────────────
    def _on_pay_btn(self, method):
        self._payment_method = method
        for m, btn in self._pay_btns.items():
            btn.setChecked(m == method)
        is_credit = method == "آجل"
        self.paid_input.setEnabled(not is_credit)
        if is_credit:
            self.paid_input.setValue(0)
        self._update_totals()

    def _setup_hotkeys(self):
        QShortcut(QKeySequence("F5"), self, self._save_invoice)
        QShortcut(QKeySequence("F6"), self, self._clear_invoice)
        QShortcut(QKeySequence("F2"), self, self._focus_barcode)
        QShortcut(QKeySequence("Escape"), self, self._clear_search)
        QShortcut(QKeySequence("Ctrl+Z"), self, self._undo_last_item)
        QShortcut(QKeySequence("Ctrl+P"), self, self._save_and_print)

    def _focus_barcode(self):
        self.barcode_input.setFocus()
        self.barcode_input.selectAll()

    def _idle_focus_check(self):
        """يعيد التركيز لحقل الباركود إذا لم يكن المستخدم يُحرّر حقلاً آخر"""
        focused = QApplication.focusWidget()
        editable_types = (QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox, QListWidget, QAbstractItemView)
        if focused is None or not isinstance(focused, editable_types):
            self._focus_barcode()
        elif focused is self.barcode_input:
            pass  # already on barcode

    def mousePressEvent(self, event):
        focused = QApplication.focusWidget()
        editable_types = (QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox, QListWidget, QAbstractItemView)
        if focused and focused is not self.barcode_input and not isinstance(focused, editable_types):
            QTimer.singleShot(50, self._focus_barcode)
        super().mousePressEvent(event)

    # ──────────────────────────────────────────
    # Barcode / Search
    # ──────────────────────────────────────────
    @safe_operation("عذراً، حدث خطأ أثناء البحث.")
    def _on_barcode_changed(self, text):
        if self._ignore_text_change:
            return
        if len(text) >= 2:
            results = self.product_ctrl.search_by_name(text)
            self._show_search_results(results)
        elif len(text) == 0:
            self.search_results.setVisible(False)

    def _show_search_results(self, results):
        if not results:
            self.search_results.setVisible(False)
            return
        self.search_results.setRowCount(len(results))
        for i, row in enumerate(results):
            self.search_results.setItem(i, 0, QTableWidgetItem(row["barcode"]))
            self.search_results.setItem(i, 1, QTableWidgetItem(row["name"]))
            self.search_results.setItem(i, 2, QTableWidgetItem(format_currency(row["sale_price"])))
            stk = row["stock_quantity"]
            stk_item = QTableWidgetItem(str(stk))
            if stk <= 0:
                stk_item.setForeground(QColor("#ef4444"))
            elif stk <= 5:
                stk_item.setForeground(QColor("#0d9488"))
            self.search_results.setItem(i, 3, stk_item)
        self.search_results.setVisible(True)

    def _on_search_result_click(self, item):
        row = item.row()
        barcode = self.search_results.item(row, 0).text()
        self._ignore_text_change = True
        self.barcode_input.setText(barcode)
        self._ignore_text_change = False
        self.search_results.setVisible(False)
        self._add_product_by_barcode(barcode)

    def _set_sell_unit(self, is_unit):
        self._btn_unit.setChecked(is_unit)
        self._btn_pack.setChecked(not is_unit)
        old_is_pack = self._is_pack
        self._is_pack = not is_unit
        self._unit_qty_label.setVisible(is_unit)
        self._unit_qty_minus.setVisible(is_unit)
        self._unit_qty_plus.setVisible(is_unit)
        if old_is_pack != self._is_pack and self.current_items:
            self._convert_items_unit(old_is_pack)
        if is_unit and self._last_scanned_product:
            self._unit_qty_label.setText("1")
        if self._last_scanned_product:
            self._show_product_price(self._last_scanned_product)

    def _convert_items_unit(self, was_pack):
        now_pack = self._is_pack
        for item in self.current_items:
            pid = item["product_id"]
            prod = self.product_ctrl.search_by_barcode(item["barcode"])
            if not prod:
                continue
            strip_price = to_decimal(prod["sale_price"])
            pstrips = int(dict(prod).get("strips_per_pack", 1))
            ppieces = int(dict(prod).get("pieces_per_strip", 1))
            if was_pack and not now_pack:
                item["sell_unit"] = "مفرد"
                item["unit_price"] = strip_price
                item["quantity"] = item["quantity"] * ppieces
            elif not was_pack and now_pack:
                item["sell_unit"] = "علبة"
                item["unit_price"] = strip_price * pstrips
                item["quantity"] = max(1, item["quantity"] // ppieces)
            item["total_price"] = item["quantity"] * item["unit_price"]
        self._refresh_invoice_table()
        self._update_totals()

    def _unit_qty_dec(self):
        val = int(self._unit_qty_label.text() or "1")
        if val > 1:
            self._unit_qty_label.setText(str(val - 1))
            if self._last_scanned_product:
                self._show_product_price(self._last_scanned_product)
            self._update_last_item_qty()

    def _unit_qty_inc(self):
        val = int(self._unit_qty_label.text() or "1")
        if val < 999:
            self._unit_qty_label.setText(str(val + 1))
            if self._last_scanned_product:
                self._show_product_price(self._last_scanned_product)
            self._update_last_item_qty()

    def _update_last_item_qty(self):
        if not self.current_items or self._is_pack:
            return
        item = self.current_items[-1]
        new_qty = int(self._unit_qty_label.text() or "1")
        item["quantity"] = new_qty
        item["total_price"] = item["quantity"] * item["unit_price"]
        self._refresh_invoice_table()
        self._update_totals()

    def _open_manual_search(self):
        try:
            self._sp_cart_items = []
            self._sp_refresh_cart()
            rows = self.product_ctrl.db.fetchall("SELECT * FROM products WHERE is_active = 1 AND is_barcoded = 0 ORDER BY name")
            self._sp_all_products = [dict(r) for r in rows]
            self._toggle_search_panel(on_open=self._sp_populate_cards)
        except Exception as e:
            QMessageBox.warning(self, "خطأ", f"فشل تحميل المواد:\n{str(e)}")

    def _sp_populate_cards(self):
        try:
            try:
                self._sp_anim.finished.disconnect(self._sp_populate_cards)
            except TypeError:
                pass
            self._sp_filter_cards()
        except Exception:
            pass

    def _toggle_search_panel(self, on_open=None):
        self._search_panel_visible = not self._search_panel_visible
        pw = self.width()
        ph = self.height()
        if pw < 100:
            pw = 1200
            ph = 800
        if not self._search_panel_visible:
            start = self._search_panel.geometry()
            end = QRect(pw, 0, 0, ph)
            self._manual_search_btn.setStyleSheet(
                "QPushButton{font-size:14px;font-weight:800;padding:0 18px;"
                "background:#7c3aed;color:white;border:2px solid #a855f7;border-radius:10px;}"
                "QPushButton:hover{background:#6d28d9;border-color:#c084fc;}"
            )
        else:
            panel_w = int(pw * 0.7)
            start = self._search_panel.geometry()
            if start.width() == 0:
                start = QRect(pw, 0, 0, ph)
            end = QRect(pw - panel_w, 0, panel_w, ph)
            self._manual_search_btn.setStyleSheet(
                "QPushButton{font-size:14px;font-weight:800;padding:0 18px;"
                "background:#dc2626;color:white;border:2px solid #ef4444;border-radius:10px;}"
                "QPushButton:hover{background:#b91c1c;border-color:#fca5a5;}"
            )
            self._sp_search.setFocus()
        self._search_panel.raise_()
        self._sp_anim = QPropertyAnimation(self._search_panel, b"geometry")
        self._sp_anim.setDuration(200)
        self._sp_anim.setStartValue(start)
        self._sp_anim.setEndValue(end)
        self._sp_anim.setEasingCurve(QEasingCurve.OutCubic)
        if on_open and self._search_panel_visible:
            try:
                self._sp_anim.finished.disconnect()
            except TypeError:
                pass
            self._sp_anim.finished.connect(on_open)
        self._sp_anim.start()

    def _sp_filter_cards(self):
        try:
            text = self._sp_search.text().strip().lower()
            for i in reversed(range(self._sp_cards_layout.count())):
                w = self._sp_cards_layout.itemAt(i).widget()
                if w:
                    w.setParent(None)
                    w.deleteLater()
            filtered = []
            for p in self._sp_all_products:
                name = (p.get("name") or "").lower()
                if not text or text in name:
                    filtered.append(p)
            cols = 4
            for i, p in enumerate(filtered):
                card = self._sp_make_card(p)
                self._sp_cards_layout.addWidget(card, i // cols, i % cols)
            if not filtered:
                no_items = QLabel("🚫 لا توجد مواد غير مكودة\nقم بإضافة مواد واختيار 'بدون باركود'")
                no_items.setAlignment(Qt.AlignCenter)
                no_items.setWordWrap(True)
                no_items.setStyleSheet("font-size:18px;font-weight:600;color:#a78bfa;background:transparent;border:none;padding:40px;")
                self._sp_cards_layout.addWidget(no_items, 0, 0, 1, cols)
            self._sp_count_lbl.setText(f"{len(filtered)} مادة")
        except Exception:
            pass

    def _sp_make_card(self, product):
        try:
            card = QFrame()
            stock = int(product.get("stock_quantity", 0))
            bc = product.get("is_barcoded", 1)
            if bc == 0:
                accent = "#a855f7"
            elif stock <= 0:
                accent = "#ef4444"
            elif stock <= 5:
                accent = "#0d9488"
            else:
                accent = "#22c55e"
            card.setFixedSize(180, 155)
            card.setCursor(Qt.PointingHandCursor)
            card.setStyleSheet(
                f"QFrame{{"
                f"background:#1e1b4b;"
                f"border:1px solid #374151;"
                f"border-top:4px solid {accent};"
                f"border-radius:12px;"
                f"}}"
                f"QFrame:hover{{"
                f"background:#312e81;"
                f"border-color:#6366f1;"
                f"border-top:4px solid {accent};"
                f"}}"
            )
            cl = QVBoxLayout(card)
            cl.setContentsMargins(10, 6, 10, 8)
            cl.setSpacing(2)
            nm = QLabel(product.get("name", ""))
            nm.setWordWrap(True)
            nm.setAlignment(Qt.AlignCenter)
            nm.setStyleSheet("font-size:13px;font-weight:800;color:#f1f5f9;background:transparent;border:none;")
            cl.addWidget(nm)
            price = float(product.get("sale_price", 0))
            pr = QLabel(f"{format_currency(str(price))} د.ع")
            pr.setAlignment(Qt.AlignCenter)
            pr.setStyleSheet("font-size:18px;font-weight:900;color:#c084fc;background:transparent;border:none;")
            cl.addWidget(pr)
            sc = "#86efac" if stock > 5 else ("#14b8a6" if stock > 0 else "#fca5a5")
            sl = QLabel(f"المخزون: {stock}")
            sl.setAlignment(Qt.AlignCenter)
            sl.setStyleSheet(f"font-size:13px;font-weight:700;color:{sc};background:transparent;border:none;")
            cl.addWidget(sl)
            if bc == 0:
                tag = QLabel("🚫 غير مكود")
                tag.setAlignment(Qt.AlignCenter)
                tag.setStyleSheet("font-size:11px;font-weight:700;color:#a855f7;background:#3b0764;border-radius:5px;padding:2px 6px;margin:0 10px;")
                cl.addWidget(tag)
            card.mousePressEvent = lambda e, p=product: self._sp_add_to_cart(p)
            return card
        except Exception:
            return QFrame()

    def _sp_add_to_cart(self, product):
        if not hasattr(self, '_sp_cart_items'):
            self._sp_cart_items = []
        pid = product["id"]
        existing = [it for it in self._sp_cart_items if it["id"] == pid]
        if existing:
            reply = QMessageBox.question(
                self, "منتج مكرر",
                f"المنتج {product['name']} موجود مسبقاً.\nهل تود إضافة كمية إضافية؟",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        item = dict(product)
        item["_sp_qty"] = int(self._unit_qty_label.text() or "1")
        item["_sp_is_pack"] = self._is_pack
        self._sp_cart_items.append(item)
        self._sp_refresh_cart()

    def _sp_refresh_cart(self):
        if not hasattr(self, '_sp_cart_items'):
            self._sp_cart_items = []
        self._sp_cart.clear()
        for it in self._sp_cart_items:
            price = float(it.get("sale_price", 0))
            qty = it.get("_sp_qty", 1)
            unit = "علبة" if it.get("_sp_is_pack", True) else "مفرد"
            self._sp_cart.addItem(QListWidgetItem(
                f'{it.get("name", "")} | {qty} {unit} — {format_currency(str(price))} د.ع'
            ))
        self._sp_cart_title.setText(f"🛒 السلة ({len(self._sp_cart_items)})")

    def _sp_clear_cart(self):
        self._sp_cart_items = []
        self._sp_refresh_cart()

    def _sp_confirm(self):
        try:
            if not hasattr(self, '_sp_cart_items'):
                self._sp_cart_items = []
            for it in self._sp_cart_items:
                bc = it.get("barcode")
                if bc:
                    sp_qty = it.get("_sp_qty", 1)
                    sp_pack = it.get("_sp_is_pack", True)
                    self._add_product_by_barcode(bc, override_qty=sp_qty, override_is_pack=sp_pack)
            self._sp_cart_items = []
            self._sp_refresh_cart()
            self._toggle_search_panel()
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "خطأ", f"فشل تأكيد السلة:\n{str(e)}")

    def _show_product_price(self, product):
        strip_price = round_to_nearest_250(to_decimal(product["sale_price"]))
        qty = int(dict(product).get("strips_per_pack", 1))
        if self._is_pack:
            price = strip_price * qty
            unit_name = "للعلبة"
        else:
            unit_qty = int(self._unit_qty_label.text() or "1")
            price = strip_price * unit_qty
            unit_name = "للمفرد"
        self._product_price_lbl.setText(f"{format_currency(price)} {unit_name}")

    def _get_unit_price(self, product):
        strip_price = to_decimal(product["sale_price"])
        qty = int(dict(product).get("strips_per_pack", 1))
        if self._is_pack:
            return strip_price * qty
        return strip_price

    def _get_unit_name(self):
        return "علبة" if self._is_pack else "مفرد"

    @safe_operation("عذراً، حدث خطأ أثناء مسح الباركود.")
    def _on_barcode_scanned(self):
        barcode = self.barcode_input.text().strip()
        if not barcode:
            return
        self._add_product_by_barcode(barcode)
        self.barcode_input.clear()

    def _add_product_by_barcode(self, barcode, override_qty=None, override_is_pack=None):
        try:
            return self._add_product_by_barcode_impl(barcode, override_qty, override_is_pack)
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "خطأ", f"فشل إضافة المنتج:\n{str(e)}")
            return None

    def _add_product_by_barcode_impl(self, barcode, override_qty=None, override_is_pack=None):
        product = self.product_ctrl.search_by_barcode(barcode)
        if not product:
            QMessageBox.warning(self, "خطأ", f"لم يتم العثور على منتج بالباركود: {barcode}")
            self._focus_barcode()
            return

        self._last_scanned_product = product
        self._product_name_lbl.setText(product["name"])
        self._show_product_price(product)
        stk = product["stock_quantity"]
        self._product_stock_lbl.setText(str(stk))
        if stk <= 0:
            self._product_stock_lbl.setStyleSheet("font-size:22px;font-weight:700;color:#ef4444;background:transparent")
        elif stk <= 5:
            self._product_stock_lbl.setStyleSheet("font-size:22px;font-weight:700;color:#0d9488;background:transparent")
        else:
            self._product_stock_lbl.setStyleSheet("font-size:22px;font-weight:700;color:#60a5fa;background:transparent")

        if product["stock_quantity"] <= 0:
            reply = QMessageBox.question(
                self, "تنبيه",
                f"المنتج {product['name']} غير متوفر في المخزون!\nهل تريد إضافته للفاتورة؟",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                self._focus_barcode()
                return

        existing = None
        sp_pack = override_is_pack if override_is_pack is not None else self._is_pack
        sell_unit = "علبة" if sp_pack else "مفرد"
        strip_price = round_to_nearest_250(to_decimal(product["sale_price"]))
        pstrips = int(dict(product).get("strips_per_pack", 1))
        unit_price = strip_price * pstrips if sp_pack else strip_price
        for item in self.current_items:
            if item["product_id"] == product["id"] and item.get("sell_unit") == sell_unit:
                existing = item
                break

        original_strip_price = round_to_nearest_250(to_decimal(product["sale_price"]))
        deal_info = None

        # ── Check for doctor deal/discount ──
        if self.selected_doctor:
            product_dict = dict(product)
            cat_id = product_dict.get("category_id")
            reward = self.doc_ctrl.calculate_reward_for_doctor(
                self.selected_doctor["id"],
                product["id"],
                from_decimal(original_strip_price),
                cat_id,
            )
            if reward:
                deal_type = reward.get("deal_type", "deal")
                reward_val = to_decimal(reward.get("reward_value", "0"))
                if deal_type == "deal":
                    unit_price = round_up_to_250(unit_price + reward_val)
                    deal_info = {
                        "type": "deal",
                        "original": original_strip_price,
                        "modified": unit_price,
                        "cost": reward_val,
                        "purchase": to_decimal(product["purchase_price"] if product["purchase_price"] else "0"),
                    }
                elif deal_type == "discount":
                    unit_price = round_down_to_250(max(unit_price - reward_val, DECIMAL_ZERO))
                    deal_info = {
                        "type": "discount",
                        "original": original_strip_price,
                        "modified": unit_price,
                        "cost": reward_val,
                        "purchase": to_decimal(product["purchase_price"] if product["purchase_price"] else "0"),
                    }

        # ── Show deal info frame ──
        if deal_info:
            self._deal_frame.setVisible(True)
            if deal_info["type"] == "deal":
                self._deal_title_lbl.setText(f"🏷 ديل ↑  د. {self.selected_doctor['name']}")
                self._deal_title_lbl.setStyleSheet("font-size:14px;font-weight:700;color:#a78bfa;background:transparent")
                self._deal_frame.setStyleSheet(
                    "QFrame{background:#1a1a2e;border:1.5px solid #7c3aed50;border-radius:10px;padding:6px}"
                )
                self._deal_new_lbl.setText(f"{format_currency(deal_info['original'])} → {format_currency(deal_info['modified'])} د.ع")
                self._deal_new_lbl.setStyleSheet("font-size:18px;font-weight:800;color:#f1f5f9;background:transparent")
            else:
                self._deal_title_lbl.setText(f"🏷 تخفيض ↓  د. {self.selected_doctor['name']}")
                self._deal_title_lbl.setStyleSheet("font-size:14px;font-weight:700;color:#34d399;background:transparent")
                self._deal_frame.setStyleSheet(
                    "QFrame{background:#0a1a1a;border:1.5px solid #10b98150;border-radius:10px;padding:6px}"
                )
                self._deal_new_lbl.setText(f"{format_currency(deal_info['original'])} → {format_currency(deal_info['modified'])} د.ع")
                self._deal_new_lbl.setStyleSheet("font-size:18px;font-weight:800;color:#f1f5f9;background:transparent")
        else:
            self._deal_frame.setVisible(False)

        add_qty = override_qty if override_qty is not None else (int(self._unit_qty_label.text() or "1") if not self._is_pack else 1)

        if existing:
            existing["quantity"] += add_qty
            existing["unit_price"] = unit_price
            existing["original_price"] = original_strip_price
            existing["total_price"] = existing["quantity"] * existing["unit_price"]
            existing["deal_type"] = deal_info["type"] if deal_info else None
        else:
            self.current_items.append({
                "product_id": product["id"],
                "barcode": product["barcode"],
                "name": product["name"],
                "quantity": add_qty,
                "unit_price": unit_price,
                "original_price": original_strip_price,
                "total_price": unit_price * add_qty,
                "sell_unit": sell_unit,
                "deal_type": deal_info["type"] if deal_info else None,
            })

        self._refresh_invoice_table()
        self._update_totals()
        self._last_added_item = self.current_items[-1] if self.current_items else None
        self.undo_btn.setEnabled(self._last_added_item is not None)

        self.barcode_input.setStyleSheet(
            "QLineEdit{font-size:17px;font-weight:600;padding:10px 12px;"
            "background:#064e3b;border:2px solid #10b981;border-radius:8px;color:#a7f3d0}"
        )
        QTimer.singleShot(400, lambda: self.barcode_input.setStyleSheet(_inp_style()))

        self.barcode_input.setPlaceholderText(f"✓ تمت الإضافة: {product['name']}")
        QTimer.singleShot(3000, lambda: self.barcode_input.setPlaceholderText("امسح الباركود..."))
        self._focus_barcode()

    # ──────────────────────────────────────────
    # Customer
    # ──────────────────────────────────────────
    def _on_customer_search(self):
        query = self.customer_input.text().strip()
        if not query:
            return
        customers = self.customer_ctrl.search(query)
        if not customers:
            QMessageBox.information(self, "بحث", "لم يتم العثور على عميل")
            return
        if len(customers) == 1:
            self._select_customer(customers[0])
        else:
            names = "\n".join(f"{c['id']}: {c['name']} - {c.get('phone', '')}" for c in customers)
            QMessageBox.information(self, "اختر عميلاً", names)

    def _select_customer(self, customer):
        self.selected_customer = customer
        self.customer_label.setText(f"✓ {customer['name']}")
        self.customer_input.setText(customer.get("phone", ""))

    def _clear_customer(self):
        self.selected_customer = None
        self.customer_label.setText("")
        self.customer_input.clear()

    # ──────────────────────────────────────────
    # Invoice table
    # ──────────────────────────────────────────
    def _refresh_invoice_table(self):
        self.invoice_table.setRowCount(len(self.current_items))
        for i, item in enumerate(self.current_items):
            name_item = QTableWidgetItem(item["name"])
            name_item.setForeground(QColor("#f1f5f9"))
            name_item.setFont(QFont("Segoe UI", 16))
            self.invoice_table.setItem(i, 0, name_item)

            unit_item = QTableWidgetItem(item.get("sell_unit", "مفرد"))
            unit_item.setForeground(QColor("#38bdf8"))
            unit_item.setFont(QFont("Segoe UI", 13, QFont.Bold))
            unit_item.setTextAlignment(Qt.AlignCenter)
            self.invoice_table.setItem(i, 1, unit_item)

            qty_spin = QSpinBox()
            qty_spin.setRange(1, 99999)
            qty_spin.setValue(item["quantity"])
            qty_spin.setStyleSheet(_spin_style() + " QSpinBox{font-size:15px;}")
            qty_spin.setFixedHeight(44)
            qty_spin.setLocale(QLocale(QLocale.English, QLocale.UnitedStates))
            qty_spin.valueChanged.connect(lambda v, idx=i: self._on_quantity_changed(idx, v))
            qty_spin.editingFinished.connect(self._focus_barcode)
            self.invoice_table.setCellWidget(i, 2, qty_spin)

            price_spin = QDoubleSpinBox()
            price_spin.setRange(0, 99999999)
            price_spin.setDecimals(0)
            price_spin.setLocale(QLocale(QLocale.English, QLocale.UnitedStates))
            price_spin.setValue(float(item["unit_price"]))
            price_spin.setStyleSheet(_spin_style() + " QDoubleSpinBox{font-size:15px;}")
            price_spin.setFixedHeight(44)
            price_spin.valueChanged.connect(lambda v, idx=i: self._on_price_changed(idx, v))
            price_spin.editingFinished.connect(self._focus_barcode)
            self.invoice_table.setCellWidget(i, 3, price_spin)

            total_item = QTableWidgetItem(format_currency(item["total_price"]))
            total_item.setForeground(QColor("#43e97b"))
            total_item.setFont(QFont("Segoe UI", 14, QFont.Bold))
            self.invoice_table.setItem(i, 4, total_item)

            # Deal badge column
            dt = item.get("deal_type")
            if dt == "deal":
                badge = QTableWidgetItem("ديل ↑")
                badge.setForeground(QColor("#a78bfa"))
                badge.setFont(QFont("Segoe UI", 12, QFont.Bold))
            elif dt == "discount":
                badge = QTableWidgetItem("خصم ↓")
                badge.setForeground(QColor("#34d399"))
                badge.setFont(QFont("Segoe UI", 12, QFont.Bold))
            else:
                badge = QTableWidgetItem("—")
                badge.setForeground(QColor("#475569"))
            badge.setTextAlignment(Qt.AlignCenter)
            self.invoice_table.setItem(i, 5, badge)

            disc_spin = QDoubleSpinBox()
            disc_spin.setRange(0, 100)
            disc_spin.setDecimals(1)
            disc_spin.setSuffix("%")
            disc_spin.setValue(0)
            disc_spin.setStyleSheet(_spin_style() + " QDoubleSpinBox{font-size:15px;}")
            disc_spin.setFixedHeight(44)
            disc_spin.valueChanged.connect(lambda v, idx=i: self._on_item_discount_changed(idx, v))
            disc_spin.editingFinished.connect(self._focus_barcode)
            self.invoice_table.setCellWidget(i, 6, disc_spin)

            del_btn = QPushButton("✕")
            del_btn.setFixedSize(44, 44)
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setStyleSheet(
                "QPushButton{background:#7f1d1d40;color:#fca5a5;border:1px solid #7f1d1d60;"
                "border-radius:8px;font-size:18px;font-weight:700}"
                "QPushButton:hover{background:#7f1d1d;color:white}"
            )
            del_btn.clicked.connect(lambda checked, idx=i: self._remove_item(idx))
            self.invoice_table.setCellWidget(i, 7, del_btn)

            self.invoice_table.setRowHeight(i, 58)

        n = len(self.current_items)
        self._sum_count_lbl.setText(f"{n} صنف" if n != 1 else "صنف واحد")

    def _on_quantity_changed(self, idx, value):
        if 0 <= idx < len(self.current_items):
            self.current_items[idx]["quantity"] = value
            self.current_items[idx]["total_price"] = (
                to_decimal(value) * self.current_items[idx]["unit_price"]
            )
            total_item = QTableWidgetItem(format_currency(self.current_items[idx]["total_price"]))
            total_item.setForeground(QColor("#43e97b"))
            total_item.setFont(QFont("Segoe UI", 14, QFont.Bold))
            self.invoice_table.setItem(idx, 4, total_item)
            self._update_totals()

    def _on_price_changed(self, idx, value):
        if 0 <= idx < len(self.current_items):
            self.current_items[idx]["unit_price"] = to_decimal(value)
            self.current_items[idx]["total_price"] = (
                self.current_items[idx]["unit_price"]
                * to_decimal(self.current_items[idx]["quantity"])
            )
            total_item = QTableWidgetItem(format_currency(self.current_items[idx]["total_price"]))
            total_item.setForeground(QColor("#43e97b"))
            total_item.setFont(QFont("Segoe UI", 14, QFont.Bold))
            self.invoice_table.setItem(idx, 4, total_item)
            self._update_totals()

    def _on_item_discount_changed(self, idx, value):
        self._update_totals()

    def _remove_item(self, idx):
        if 0 <= idx < len(self.current_items):
            self.current_items.pop(idx)
            self._refresh_invoice_table()
            self._update_totals()

    # ──────────────────────────────────────────
    # Totals
    # ──────────────────────────────────────────
    def _update_remainders(self, total):
        # Auto-fill paid = total (full payment by default)
        if not (self._payment_method == "آجل"):
            self.paid_input.setValue(float(total))
        self._sum_remain_lab_lbl.setText("0")
        self._sum_remain_patient_lbl.setText("0")
        self._update_stats_bar()

    def _update_totals_from_subtotal(self):
        if hasattr(self, '_is_calculating') and self._is_calculating:
            return
        self._is_calculating = True
        try:
            subtotal = to_decimal(self._sum_subtotal_lbl.value())
            discount_amt = to_decimal(self.discount_amount_input.value())
            if subtotal > DECIMAL_ZERO:
                discount_pct = (discount_amt / subtotal * to_decimal("100")).quantize(to_decimal("0.1"))
            else:
                discount_pct = DECIMAL_ZERO
            total = (subtotal - discount_amt).quantize(to_decimal("0.01"))
            
            self._discount_pct_lbl.setText(f"% {discount_pct:.1f}")
            self._card3_total_lbl.setValue(float(total))
            self._sum_total_lbl.setText(format_currency(total))
            self._update_remainders(total)
        finally:
            self._is_calculating = False

    def _update_totals_from_discount_amt(self):
        if hasattr(self, '_is_calculating') and self._is_calculating:
            return
        self._is_calculating = True
        try:
            subtotal = to_decimal(self._sum_subtotal_lbl.value())
            discount_amt = to_decimal(self.discount_amount_input.value())
            if subtotal > DECIMAL_ZERO:
                discount_pct = (discount_amt / subtotal * to_decimal("100")).quantize(to_decimal("0.1"))
            else:
                discount_pct = DECIMAL_ZERO
            total = (subtotal - discount_amt).quantize(to_decimal("0.01"))
            
            self._discount_pct_lbl.setText(f"% {discount_pct:.1f}")
            self._card3_total_lbl.setValue(float(total))
            self._sum_total_lbl.setText(format_currency(total))
            self._update_remainders(total)
            self._check_discount_warning()
        finally:
            self._is_calculating = False

    def _update_totals_from_total(self):
        if hasattr(self, '_is_calculating') and self._is_calculating:
            return
        self._is_calculating = True
        try:
            subtotal = to_decimal(self._sum_subtotal_lbl.value())
            total = to_decimal(self._card3_total_lbl.value())
            discount_amt = subtotal - total
            if subtotal > DECIMAL_ZERO:
                discount_pct = (discount_amt / subtotal * to_decimal("100")).quantize(to_decimal("0.1"))
            else:
                discount_pct = DECIMAL_ZERO
                
            self.discount_amount_input.setValue(float(discount_amt))
            self._discount_pct_lbl.setText(f"% {discount_pct:.1f}")
            self._sum_total_lbl.setText(format_currency(total))
            self._update_remainders(total)
            self._check_discount_warning()
        finally:
            self._is_calculating = False

    def _update_totals_from_paid(self):
        pass  # paid is now auto-filled, no manual update needed

    # ──────────────────────────────────────────
    # Cost / Discount Warning
    # ──────────────────────────────────────────
    def _calc_cart_cost(self) -> Decimal:
        """Calculate total purchase cost of all items in cart."""
        if not self.current_items:
            return DECIMAL_ZERO
        pids = list({item["product_id"] for item in self.current_items})
        if not pids:
            return DECIMAL_ZERO
        placeholders = ",".join("?" for _ in pids)
        rows = self.product_ctrl.db.fetchall(
            f"SELECT id, sale_price, purchase_price, strips_per_pack FROM products WHERE id IN ({placeholders})",
            tuple(pids),
        )
        prod_map = {}
        for r in rows:
            prod_map[r["id"]] = {
                "sale_price": to_decimal(r["sale_price"]),
                "purchase_price": to_decimal(r["purchase_price"]),
                "strips_per_pack": int(r["strips_per_pack"] or 1),
            }
        total_cost = DECIMAL_ZERO
        for item in self.current_items:
            pid = item["product_id"]
            p = prod_map.get(pid)
            if not p:
                continue
            sp = p["sale_price"]
            pp = p["purchase_price"]
            spp = p["strips_per_pack"]
            if not sp:
                continue
            total_cost += item["total_price"] / (sp * spp) * pp
        return total_cost.quantize(Decimal("0.01"))

    def _check_discount_warning(self):
        """Show red flash on discount input if profit would be ≤ 0."""
        subtotal = sum((item["total_price"] for item in self.current_items), DECIMAL_ZERO)
        if subtotal <= DECIMAL_ZERO:
            return
        discount_amt = to_decimal(self.discount_amount_input.value())
        cost = self._calc_cart_cost()
        profit = subtotal - discount_amt - cost
        if profit <= DECIMAL_ZERO:
            self.discount_amount_input.setStyleSheet(
                "QDoubleSpinBox{font-size:19px;font-weight:700;padding:4px 3px;"
                "background:#1a0a0a;border:2px solid #ef4444;border-radius:6px;color:#ef4444}"
            )
        else:
            self.discount_amount_input.setStyleSheet(
                "QDoubleSpinBox{font-size:19px;font-weight:700;padding:4px 3px;"
                "background:#0b1120;border:none;border-bottom:2px solid #2a3f5f;border-radius:6px;color:#f1f5f9}"
            )

    def _update_totals(self):
        if hasattr(self, '_is_calculating') and self._is_calculating:
            return
        self._is_calculating = True
        try:
            subtotal = sum((item["total_price"] for item in self.current_items), DECIMAL_ZERO)
            self._sum_subtotal_lbl.setValue(float(subtotal))
            
            discount_amt = to_decimal(self.discount_amount_input.value())
            if subtotal > DECIMAL_ZERO:
                discount_pct = (discount_amt / subtotal * to_decimal("100")).quantize(to_decimal("0.1"))
            else:
                discount_pct = DECIMAL_ZERO
            total = (subtotal - discount_amt).quantize(to_decimal("0.01"))
            
            self._discount_pct_lbl.setText(f"% {discount_pct:.1f}")
            self.discount_amount_input.setValue(float(discount_amt))
            self._card3_total_lbl.setValue(float(total))
            self._sum_total_lbl.setText(format_currency(total))
            
            self._update_remainders(total)
            self._check_discount_warning()
        finally:
            self._is_calculating = False

    def _on_payment_method_changed(self, method):
        self._on_pay_btn(method)

    # ──────────────────────────────────────────
    # Save / Clear
    # ──────────────────────────────────────────
    @safe_operation("عذراً، حدث خطأ أثناء حفظ الفاتورة.")
    def _save_invoice(self):
        if self._return_mode:
            self._save_edited_invoice()
            return
        if not self.current_items:
            QMessageBox.warning(self, "تنبيه", "الفاتورة فارغة. أضف منتجات قبل الحفظ.")
            return

        payment_map = {"نقداً": "cash", "بطاقة": "card", "آجل": "credit"}
        method = payment_map.get(self._payment_method, "cash")
        
        subtotal = sum((item["total_price"] for item in self.current_items), DECIMAL_ZERO)
        discount_amt = to_decimal(self.discount_amount_input.value())
        if subtotal > DECIMAL_ZERO:
            discount_pct = (discount_amt / subtotal * to_decimal("100")).quantize(to_decimal("0.1"))
        else:
            discount_pct = DECIMAL_ZERO

        items_data = [
            {
                "product_id": item["product_id"],
                "quantity": item["quantity"],
                "unit_price": from_decimal(item["unit_price"]),
                "total_price": from_decimal(item["total_price"]),
                "original_price": from_decimal(item.get("original_price", item["unit_price"])),
            }
            for item in self.current_items
        ]

        net_total = (subtotal - discount_amt).quantize(to_decimal("0.01"))
        # Auto-pay: paid = net_total (full payment)
        paid = net_total

        try:
            customer_id = self.selected_customer["id"] if self.selected_customer else None
            doctor_id = self.selected_doctor["id"] if self.selected_doctor else None
            sale_id = self.sale_ctrl.create_sale(
                user_id=self.user_data["id"],
                items=items_data,
                discount=from_decimal(discount_pct),
                customer_id=customer_id,
                payment_method=method,
                paid_amount=from_decimal(paid),
                doctor_id=doctor_id,
            )
            self.sale_completed.emit(sale_id)
            if self._print_after_save:
                self.print_sale.emit(sale_id)
            self._clear_invoice()

            if method == "credit":
                QMessageBox.information(
                    self, "✓ تم الحفظ",
                    f"تم حفظ الفاتورة رقم {sale_id}\nتم تسجيل الدين في حساب العميل.",
                )
            else:
                msg = f"تم حفظ الفاتورة بنجاح!\nرقم الفاتورة: {sale_id}"
                if discount_amt > DECIMAL_ZERO:
                    msg += f"\nالخصم: {format_currency(discount_amt)}"
                msg += f"\nالمدفوع: {format_currency(paid)}"
                QMessageBox.information(self, "✓ تم الحفظ", msg)
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"حدث خطأ أثناء حفظ الفاتورة:\n{str(e)}")

    def _clear_invoice(self):
        if self._return_mode:
            self._exit_return_mode()
            return
        self.current_items.clear()
        self.selected_customer = None
        self.customer_label.setText("")
        self.customer_input.clear()
        self._clear_doctor()
        self.discount_amount_input.setValue(0)
        self._discount_pct_lbl.setText("% 0.0")
        self.paid_input.setValue(0)
        self._on_pay_btn("نقداً")
        self.invoice_table.setRowCount(0)
        self._product_name_lbl.setText("—")
        self._product_price_lbl.setText("—")
        self._product_stock_lbl.setText("—")
        self._deal_frame.setVisible(False)
        self._last_added_item = None
        self.undo_btn.setEnabled(False)
        self._update_totals()
        self._update_stats_bar()
        self._focus_barcode()

    def _clear_search(self):
        self.search_results.setVisible(False)
        self._focus_barcode()

    # ─────────────────────────────────────
    # Doctor
    # ─────────────────────────────────────
    def _on_doctor_combo_changed(self, idx):
        if idx <= 0:
            self.selected_doctor = None
            self.doctor_label.setText("")
            self._deal_frame.setVisible(False)
            self._recalculate_deals()
            return
        doc_id = self.doctor_combo.itemData(idx)
        if doc_id:
            doctor = self.doc_ctrl.get_by_id(doc_id)
            self._select_doctor(doctor)

    def _select_doctor(self, doctor):
        self.selected_doctor = doctor
        doc_dict = dict(doctor)
        comm = doc_dict.get("commission_rate", "0.00")
        try:
            comm_f = float(comm)
        except Exception:
            comm_f = 0.0
        if comm_f > 0:
            self.doctor_label.setText(f"✓ {doctor['name']}  •  عمولة {comm_f:.1f}%")
        else:
            self.doctor_label.setText(f"✓ {doctor['name']}")
        # Recalculate all cart prices for this doctor
        self._recalculate_deals()

    def _recalculate_deals(self):
        """Recalculate prices for all cart items based on selected doctor's deals."""
        if not self.current_items:
            return
        has_any_deal = False
        for item in self.current_items:
            strip_price = item.get("original_price", item["unit_price"])
            sell_unit = item.get("sell_unit", "مفرد")
            if self.selected_doctor:
                product = self.product_ctrl.get_by_id(item["product_id"])
                if product:
                    prod_dict = dict(product)
                    cat_id = prod_dict.get("category_id")
                    reward = self.doc_ctrl.calculate_reward_for_doctor(
                        self.selected_doctor["id"],
                        item["product_id"],
                        from_decimal(strip_price),
                        cat_id,
                    )
                    if reward:
                        has_any_deal = True
                        deal_type = reward.get("deal_type", "deal")
                        reward_val = to_decimal(reward.get("reward_value", "0"))
                        if deal_type == "deal":
                            new_strip_price = round_up_to_250(strip_price + reward_val)
                        elif deal_type == "discount":
                            new_strip_price = round_down_to_250(max(strip_price - reward_val, DECIMAL_ZERO))
                        else:
                            new_strip_price = strip_price
                        qty = int(prod_dict.get("strips_per_pack", 1))
                        if sell_unit == "علبة":
                            item["unit_price"] = new_strip_price * qty
                        else:
                            item["unit_price"] = new_strip_price
                        item["deal_type"] = deal_type
                    else:
                        item["deal_type"] = None
                        qty = int(dict(product).get("strips_per_pack", 1))
                        if sell_unit == "علبة":
                            item["unit_price"] = strip_price * qty
                        else:
                            item["unit_price"] = strip_price
                else:
                    item["deal_type"] = None
                    item["unit_price"] = strip_price
            else:
                item["deal_type"] = None
                item["unit_price"] = strip_price
            item["total_price"] = item["quantity"] * item["unit_price"]
        self._refresh_invoice_table()
        self._update_totals()
        # Update deal frame for first item if doctor is selected
        if self.selected_doctor and self.current_items:
            first = self.current_items[0]
            if first.get("deal_type"):
                self._deal_frame.setVisible(True)
                is_deal = first["deal_type"] == "deal"
                self._deal_title_lbl.setText(
                    f"🏷 ديل ↑  د. {self.selected_doctor['name']}" if is_deal
                    else f"🏷 تخفيض ↓  د. {self.selected_doctor['name']}"
                )
                self._deal_title_lbl.setStyleSheet(
                    "font-size:14px;font-weight:700;color:#a78bfa;background:transparent" if is_deal
                    else "font-size:14px;font-weight:700;color:#34d399;background:transparent"
                )
                self._deal_frame.setStyleSheet(
                    "QFrame{background:#1a1a2e;border:1.5px solid #7c3aed50;border-radius:10px;padding:6px}" if is_deal
                    else "QFrame{background:#0a1a1a;border:1.5px solid #10b98150;border-radius:10px;padding:6px}"
                )
                orig = first.get("original_price", first["unit_price"])
                self._deal_new_lbl.setText(f"{format_currency(orig)} → {format_currency(first['unit_price'])} د.ع")
                self._deal_new_lbl.setStyleSheet("font-size:18px;font-weight:800;color:#f1f5f9;background:transparent")
            else:
                self._deal_frame.setVisible(False)
        else:
            self._deal_frame.setVisible(False)

    def _clear_doctor(self):
        self.selected_doctor = None
        self.doctor_label.setText("")
        self._deal_frame.setVisible(False)
        if self.doctor_combo.count() > 0:
            self.doctor_combo.setCurrentIndex(0)
        self._recalculate_deals()

    # ─────────────────────────────────────
    # Undo last item
    # ─────────────────────────────────────
    def _undo_last_item(self):
        if not self.current_items:
            return
        removed = self.current_items.pop()
        self._last_added_item = None
        self.undo_btn.setEnabled(False)
        self._refresh_invoice_table()
        self._update_totals()
        self.barcode_input.setPlaceholderText(f"↩ تم حذف: {removed['name']}")
        QTimer.singleShot(2500, lambda: self.barcode_input.setPlaceholderText("امسح الباركود..."))
        self._focus_barcode()

    # ─────────────────────────────────────
    # Stats bar
    # ─────────────────────────────────────
    def _update_stats_bar(self):
        n = len(self.current_items)
        if n > 0:
            total_qty = sum(item["quantity"] for item in self.current_items)
            subtotal = sum((item["total_price"] for item in self.current_items), DECIMAL_ZERO)
            avg = subtotal / n
            self._stat_items_lbl.setText(f"الأصناف: {n}")
            self._stat_qty_lbl.setText(f"الكميات: {total_qty}")
            self._stat_avg_lbl.setText(f"المتوسط: {format_currency(avg)}")
            self._stat_items_lbl.setStyleSheet("font-size:13px;font-weight:600;color:#60a5fa;background:transparent")
            self._stat_qty_lbl.setStyleSheet("font-size:13px;font-weight:600;color:#a78bfa;background:transparent")
            self._stat_avg_lbl.setStyleSheet("font-size:13px;font-weight:600;color:#34d399;background:transparent")
        else:
            self._stat_items_lbl.setText("الأصناف: 0")
            self._stat_qty_lbl.setText("الكميات: 0")
            self._stat_avg_lbl.setText("المتوسط: 0.00")
            for lbl in [self._stat_items_lbl, self._stat_qty_lbl, self._stat_avg_lbl]:
                lbl.setStyleSheet("font-size:13px;color:#64748b;background:transparent")

    # ─────────────────────────────────────
    # Save and print
    # ─────────────────────────────────────
    def _save_and_print(self):
        if not self.current_items:
            QMessageBox.warning(self, "تنبيه", "الفاتورة فارغة. أضف منتجات قبل الحفظ.")
            return
        self._print_after_save = True
        self._save_invoice()
        self._print_after_save = False

    # ─────────────────────────────────────
    # Hold / Resume Invoice
    # ─────────────────────────────────────
    def _hold_invoice(self):
        if not self.current_items:
            QMessageBox.warning(self, "تنبيه", "الفاتورة فارغة. أضف منتجات قبل التعليق.")
            return
        if self._return_mode:
            QMessageBox.warning(self, "تنبيه", "لا يمكن تعليق فاتورة في وضع الإرجاع.")
            return

        import json
        from database.connection import DatabaseManager
        db = DatabaseManager()

        items_json = []
        for item in self.current_items:
            items_json.append({
                "product_id": item["product_id"],
                "name": item.get("name", ""),
                "quantity": item["quantity"],
                "unit_price": str(item["unit_price"]),
                "total_price": str(item["total_price"]),
            })

        customer_id = self.selected_customer["id"] if self.selected_customer else None
        customer_name = self.selected_customer["name"] if self.selected_customer else None
        doctor_id = self.selected_doctor["id"] if self.selected_doctor else None
        doctor_name = self.selected_doctor["name"] if self.selected_doctor else None

        subtotal = sum((item["total_price"] for item in self.current_items), DECIMAL_ZERO)
        discount = to_decimal(self.discount_amount_input.value())
        payment_method = self._payment_method

        try:
            db.execute(
                "INSERT INTO held_invoices (user_id, items_json, subtotal, discount, payment_method, customer_id, customer_name, doctor_id, doctor_name) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (self.user_data["id"], json.dumps(items_json, ensure_ascii=False),
                 from_decimal(subtotal), from_decimal(discount), payment_method,
                 customer_id, customer_name, doctor_id, doctor_name),
            )
            from utils.toast import ToastNotification
            ToastNotification.show_message("تم تعليق الفاتورة بنجاح.\nيمكنك استرجاعها من قائمة المعلقات.", 5000, self, "⏸ تعليق")
            self._clear_invoice()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"فشل تعليق الفاتورة:\n{str(e)}")

    def _show_held_invoices(self):
        from database.connection import DatabaseManager
        db = DatabaseManager()
        rows = db.fetchall(
            "SELECT * FROM held_invoices WHERE user_id = ? ORDER BY created_at DESC",
            (self.user_data["id"],),
        )
        if not rows:
            QMessageBox.information(self, "📋 المعلقات", "لا توجد فواتير معلقة.")
            return

        import json
        from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QScrollArea, QFrame, QHBoxLayout,
                                     QPushButton, QLabel)
        from PyQt5.QtCore import Qt

        dialog = QDialog(self)
        dialog.setWindowTitle("📋 الفواتير المعلقة")
        dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        dialog.setStyleSheet("QDialog{background:#0b1120;border:1px solid #1e293b;border-radius:12px;}")
        dialog.resize(800, 650)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 12, 20, 20)
        layout.setSpacing(10)

        # ── Top bar ──
        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        title = QLabel("📋 الفواتير المعلقة")
        title.setStyleSheet("font-size:20px;font-weight:700;color:#14b8a6;background:transparent;border:none;padding:4px 0;")
        top.addWidget(title)
        top.addStretch()
        cx = QPushButton("✕")
        cx.setFixedSize(34, 34)
        cx.setCursor(Qt.PointingHandCursor)
        cx.setStyleSheet("QPushButton{font-size:16px;font-weight:700;color:#94a3b8;background:#1e293b;border:none;border-radius:17px;}QPushButton:hover{background:#ef4444;color:white;}")
        cx.clicked.connect(dialog.reject)
        top.addWidget(cx)
        layout.addLayout(top)

        # ── Scroll area ──
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        sc.setStyleSheet("""
            QScrollArea{background:transparent;border:none;}
            QScrollBar:vertical{background:#1e293b;width:8px;border-radius:4px;}
            QScrollBar::handle:vertical{background:#475569;border-radius:4px;min-height:24px;}
            QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}
        """)
        cont = QWidget()
        cont.setStyleSheet("background:transparent;")
        cv = QVBoxLayout(cont)
        cv.setSpacing(10)

        for r in rows:
            items = json.loads(r["items_json"])
            item_count = len(items)
            time_str = r["created_at"][:19] if r["created_at"] else ""
            customer = r["customer_name"] or "—"
            discount = to_decimal(r["discount"])

            # ── Card ──
            card = QFrame()
            card.setStyleSheet("""
                QFrame{background:#141d2e;border:1px solid #14b8a640;border-radius:10px;}
                QFrame:hover{border-color:#14b8a6;}
            """)
            cl = QVBoxLayout(card)
            cl.setContentsMargins(14, 10, 14, 10)
            cl.setSpacing(8)

            # Header row
            h = QHBoxLayout()
            h.setContentsMargins(0, 0, 0, 0)
            hdr_txt = QLabel(f"<b style='font-size:15px;color:#f1f5f9;'>#{r['id']}</b>  "
                             f"<span style='font-size:12px;color:#64748b;'>{time_str}</span>")
            hdr_txt.setTextFormat(Qt.RichText)
            hdr_txt.setStyleSheet("background:transparent;border:none;")
            h.addWidget(hdr_txt)
            h.addStretch()
            resume_btn = QPushButton("▶ استرجاع")
            resume_btn.setStyleSheet("QPushButton{font-size:12px;font-weight:700;background:#0d9488;color:#fff;border:none;border-radius:5px;padding:5px 14px;}QPushButton:hover{background:#0f766e;}")
            resume_btn.clicked.connect(lambda ch, rid=r["id"], d=dialog: self._resume_held_invoice(rid, d))
            h.addWidget(resume_btn)
            del_btn = QPushButton("✕ حذف")
            del_btn.setStyleSheet("QPushButton{font-size:11px;color:#ef4444;background:transparent;border:1px solid #ef4444;border-radius:5px;padding:5px 10px;}QPushButton:hover{background:#ef444420;}")
            del_btn.clicked.connect(lambda ch, rid=r["id"], c=card: self._delete_held_invoice(rid, c))
            h.addWidget(del_btn)
            cl.addLayout(h)

            # Summary
            sum_txt = (f"المواد: {item_count}  |  "
                       f"الإجمالي: <b style='color:#7ba3ff;'>{format_currency(r['subtotal'])} د.ع</b>"
                       + (f"  |  الخصم: <b style='color:#ef4444;'>{format_currency(discount)} د.ع</b>" if discount > DECIMAL_ZERO else "")
                       + f"  |  الزبون: {customer}")
            summary = QLabel(sum_txt)
            summary.setStyleSheet("font-size:12px;color:#94a3b8;background:transparent;border:none;")
            summary.setTextFormat(Qt.RichText)
            cl.addWidget(summary)

            # Items list — compact rows as labels inside a frame with max 12 visible
            items_frame = QFrame()
            items_frame.setStyleSheet("QFrame{background:#0b1120;border:1px solid #1e293b;border-radius:6px;}")
            il = QVBoxLayout(items_frame)
            il.setContentsMargins(10, 6, 10, 6)
            il.setSpacing(2)

            max_show = 12
            show_count = min(item_count, max_show)
            for i in range(show_count):
                it = items[i]
                row_w = QFrame()
                row_w.setStyleSheet("QFrame{background:transparent;}")
                rl = QHBoxLayout(row_w)
                rl.setContentsMargins(0, 2, 0, 2)
                rl.setSpacing(8)
                name_lbl = QLabel(it.get("name", ""))
                name_lbl.setStyleSheet("font-size:12px;color:#e2e8f0;background:transparent;border:none;")
                qty_lbl = QLabel(f"×{it['quantity']}")
                qty_lbl.setStyleSheet("font-size:12px;color:#7ba3ff;background:transparent;border:none;")
                qty_lbl.setFixedWidth(50)
                qty_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                price_lbl = QLabel(f"{format_currency(it['total_price'])} د.ع")
                price_lbl.setStyleSheet("font-size:12px;color:#e2e8f0;background:transparent;border:none;")
                price_lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                rl.addWidget(name_lbl, 1)
                rl.addWidget(qty_lbl)
                rl.addWidget(price_lbl)
                il.addWidget(row_w)

            if item_count > max_show:
                more_lbl = QLabel(f"... و{item_count - max_show} مواد أخرى")
                more_lbl.setStyleSheet("font-size:11px;color:#64748b;background:transparent;border:none;padding:2px 0;")
                il.addWidget(more_lbl)

            cl.addWidget(items_frame)
            cv.addWidget(card)

        sc.setWidget(cont)
        layout.addWidget(sc, 1)

        close_btn = QPushButton("إغلاق")
        close_btn.setStyleSheet("QPushButton{font-size:14px;font-weight:700;background:#334155;color:#f1f5f9;border:none;border-radius:8px;padding:10px 0;}QPushButton:hover{background:#475569;}")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)

        dialog.exec_()
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)

        dialog.exec_()

    def _resume_held_invoice(self, held_id, dialog=None):
        from database.connection import DatabaseManager
        import json
        db = DatabaseManager()
        row = db.fetchone("SELECT * FROM held_invoices WHERE id = ?", (held_id,))
        if not row:
            QMessageBox.warning(self, "خطأ", "الفاتورة غير موجودة")
            return

        if self.current_items:
            reply = QMessageBox.question(self, "فاتورة موجودة",
                "توجد فاتورة حالية. هل تريد مسحها واسترجاع المعلقة؟",
                QMessageBox.Yes | QMessageBox.No)
            if reply != QMessageBox.Yes:
                return
            self._clear_invoice()

        items = json.loads(row["items_json"])
        for item in items:
            self.current_items.append({
                "product_id": item["product_id"],
                "name": item.get("name", ""),
                "quantity": item["quantity"],
                "unit_price": to_decimal(item["unit_price"]),
                "total_price": to_decimal(item["total_price"]),
                "original_price": to_decimal(item["unit_price"]),
                "sell_unit": "مفرد",
                "deal_type": None,
            })

        self.discount_amount_input.setValue(float(to_decimal(row["discount"])))
        if row["customer_name"]:
            self.customer_label.setText(f"👤 {row['customer_name']}")
        self._refresh_invoice_table()
        self._update_totals()
        self._update_stats_bar()
        self._focus_barcode()

        db.execute("DELETE FROM held_invoices WHERE id = ?", (held_id,))
        if dialog:
            dialog.accept()
        QMessageBox.information(self, "✓ تم", "تم استرجاع الفاتورة المعلقة.\nيمكنك متابعة البيع.")

    def _delete_held_invoice(self, held_id, card_widget):
        from database.connection import DatabaseManager
        db = DatabaseManager()
        db.execute("DELETE FROM held_invoices WHERE id = ?", (held_id,))
        card_widget.setParent(None)
        card_widget.deleteLater()

    # ═════════════════════════════════════
    # Return Mode
    # ═════════════════════════════════════

    def _toggle_return_panel(self):
        self._return_panel_visible = not self._return_panel_visible
        pw = self.width()
        panel_w = int(pw * 0.55)
        anim = QPropertyAnimation(self._return_panel, b"geometry")
        anim.setDuration(250)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        if not self._return_panel_visible:
            anim.setStartValue(self._return_panel.geometry())
            anim.setEndValue(QRect(pw, 0, panel_w, self.height()))
        else:
            anim.setStartValue(QRect(pw, 0, panel_w, self.height()))
            anim.setEndValue(QRect(pw - panel_w, 0, panel_w, self.height()))
            self._return_panel.raise_()
            self._load_today_invoices()
        anim.start()
        self._rp_anim = anim

    def _load_today_invoices(self, filter_text=""):
        for i in reversed(range(self._rp_grid.count())):
            w = self._rp_grid.itemAt(i).widget()
            if w:
                w.deleteLater()

        from datetime import date
        today_str = date.today().isoformat()
        rows = self.sale_ctrl.db.fetchall(
            """SELECT s.*, u.full_name as user_name
               FROM sales s
               LEFT JOIN users u ON s.user_id = u.id
               WHERE date(s.created_at) = ?
               ORDER BY s.created_at DESC""",
            (today_str,),
        )

        for r in rows:
            inv_id = r["id"]
            inv_num = r["invoice_number"]
            total = r["total_amount"]
            method = r["payment_method"]
            user = r["user_name"] or ""
            method_map = {"cash": "نقداً", "card": "بطاقة", "credit": "آجل"}
            display_method = method_map.get(method, method)

            # Filter by text if needed
            if filter_text and filter_text.lower() not in str(inv_num).lower() and filter_text not in str(inv_id):
                continue

            card = QFrame()
            card.setFixedHeight(70)
            card.setCursor(Qt.PointingHandCursor)
            card.setStyleSheet("""
                QFrame{
                    background:rgba(255,255,255,0.08);
                    border:1px solid #14b8a660;
                    border-radius:10px;
                }
                QFrame:hover{background:rgba(255,255,255,0.15);border-color:#14b8a6;}
            """)
            cl = QHBoxLayout(card)
            cl.setContentsMargins(14, 8, 14, 8)
            info = QLabel(f"<b>#{inv_id}</b> — {inv_num}<br><span style='font-size:12px;color:#14b8a6;'>{display_method} | {format_currency(total)} | {user}</span>")
            info.setStyleSheet("font-size:15px;color:#f1f5f9;background:transparent;border:none;")
            info.setTextFormat(Qt.RichText)
            cl.addWidget(info)
            cl.addStretch()
            card.mousePressEvent = lambda e, sid=inv_id: self._select_return_invoice(sid)
            self._rp_grid.addWidget(card)

        if not rows:
            empty = QLabel("📭 لا توجد فواتير لليوم")
            empty.setStyleSheet("font-size:18px;color:#14b8a6;background:transparent;border:none;padding:40px;")
            empty.setAlignment(Qt.AlignCenter)
            self._rp_grid.addWidget(empty)

    def _rp_filter_invoices(self, text):
        self._load_today_invoices(text)

    def _select_return_invoice(self, sale_id):
        self._return_sale_id = sale_id
        self._return_mode = True
        self._toggle_return_panel()

        sale = self.sale_ctrl.get_sale_by_id(sale_id)
        if not sale:
            QMessageBox.warning(self, "خطأ", "الفاتورة غير موجودة")
            self._exit_return_mode()
            return

        items = self.sale_ctrl.get_sale_items(sale_id)
        self.current_items = []
        for si in items:
            self.current_items.append({
                "product_id": si["product_id"],
                "sale_item_id": si["id"],
                "quantity": si["quantity"],
                "unit_price": to_decimal(si["unit_price"]),
                "total_price": to_decimal(si["total_price"]),
                "original_price": to_decimal(si["unit_price"]),
                "sell_unit": "مفرد",
                "deal_type": None,
                "name": si["product_name"],
            })

        self._refresh_invoice_table()
        self._update_totals()
        self._update_stats_bar()

        # Restore original discount (stored as absolute amount in DB)
        sale_discount = to_decimal(sale["discount"] if sale["discount"] else "0")
        self.discount_amount_input.setValue(float(sale_discount))

        QMessageBox.information(self, "وضع الإرجاع",
            f"تم تحميل الفاتورة #{sale_id}\n"
            "قلل الكميات للمواد المطلوب إرجاعها ثم احفظ.")

    def _exit_return_mode(self):
        self._return_mode = False
        self._return_sale_id = None
        self._return_banner.setVisible(False)
        self._return_panel_visible = False
        self.current_items.clear()
        self.invoice_table.setRowCount(0)
        self.selected_customer = None
        self.customer_label.setText("")
        self.customer_input.clear()
        self._clear_doctor()
        self.discount_amount_input.setValue(0)
        self._discount_pct_lbl.setText("% 0.0")
        self.paid_input.setValue(0)
        self._on_pay_btn("نقداً")
        self._product_name_lbl.setText("—")
        self._product_price_lbl.setText("—")
        self._product_stock_lbl.setText("—")
        self._deal_frame.setVisible(False)
        self._last_added_item = None
        self.undo_btn.setEnabled(False)
        self._update_totals()
        self._update_stats_bar()
        self._focus_barcode()

    def _save_edited_invoice(self):
        """Full edit: add/remove items, change qty, change discount — with full reversal + re-apply."""
        try:
            if not self._return_mode or not self._return_sale_id:
                return
            if not self.current_items:
                QMessageBox.warning(self, "تنبيه", "الفاتورة فارغة. أضف منتجات قبل الحفظ.")
                return

            sale_id = self._return_sale_id
            original_sale = self.sale_ctrl.get_sale_by_id(sale_id)
            original_items = self.sale_ctrl.get_sale_items(sale_id)
            from database.connection import DatabaseManager
            db = DatabaseManager()
            os_dict = dict(original_sale) if original_sale else {}

            subtotal = sum((item["total_price"] for item in self.current_items), DECIMAL_ZERO)
            discount_amt = to_decimal(self.discount_amount_input.value())
            net_total = (subtotal - discount_amt).quantize(to_decimal("0.01"))

            details = f"<b>فاتورة #{sale_id}</b><br><br>"
            details += "<table style='width:100%;border-collapse:collapse'>"
            details += "<tr style='color:#94a3b8;font-size:13px'><th>المنتج</th><th>الكمية</th><th>الإجمالي</th></tr>"
            for item in self.current_items:
                if item["quantity"] <= 0:
                    continue
                details += f"<tr><td>{item.get('name', '')}</td><td>{item['quantity']}</td><td>{format_currency(item['total_price'])}</td></tr>"
            details += "</table>"
            details += f"<br><b>الإجمالي: {format_currency(subtotal)}</b>"
            if discount_amt > DECIMAL_ZERO:
                details += f"<br>الخصم: {format_currency(discount_amt)}"
            details += f"<br><b>الصافي: {format_currency(net_total)}</b>"
            details += "<br><br>سيتم إرجاع المواد السابقة للمخزن وتطبيق التعديلات."

            confirm = QMessageBox(QMessageBox.Question, "تأكيد التعديل",
                "هل أنت متأكد من حفظ التعديلات على الفاتورة؟",
                QMessageBox.Yes | QMessageBox.No, self)
            confirm.setInformativeText(details)
            confirm.setDetailedText(details.replace("<br>", "\n").replace("<tr>", "\n").replace("<td>", "  ").replace("</td>", "").replace("</tr>", "").replace("</b>", "").replace("<b>", "").replace("<table>", "").replace("</table>", ""))
            if confirm.exec_() != QMessageBox.Yes:
                return

            # 1. Record return transaction for audit trail
            orig_data = [{
                "sale_item_id": si["id"],
                "product_id": si["product_id"],
                "quantity": si["quantity"],
                "unit_price": si["unit_price"],
                "total_price": si["total_price"],
            } for si in original_items]
            if orig_data:
                total_returned = sum(to_decimal(d["total_price"]) for d in orig_data)
                db.execute(
                    "INSERT INTO return_transactions (sale_id, user_id, reason, total_returned) VALUES (?, ?, ?, ?)",
                    (sale_id, self.user_data["id"], "تعديل الفاتورة", from_decimal(total_returned)),
                )
                return_id = db.fetchone("SELECT last_insert_rowid()")[0]
                for d in orig_data:
                    db.execute(
                        "INSERT INTO return_items (return_id, sale_item_id, product_id, quantity, unit_price, total_price) VALUES (?, ?, ?, ?, ?, ?)",
                        (return_id, d["sale_item_id"], d["product_id"], d["quantity"],
                         d["unit_price"], d["total_price"]),
                    )

            # 2. Return ALL original stock
            for si in original_items:
                prod = db.fetchone("SELECT sale_price FROM products WHERE id = ?", (si["product_id"],))
                sp = to_decimal(prod["sale_price"]) if prod else DECIMAL_ZERO
                strip_eq = int(to_decimal(si["total_price"]) / sp) if sp else si["quantity"]
                db.execute("UPDATE products SET stock_quantity = stock_quantity + ? WHERE id = ?",
                           (max(strip_eq, 0), si["product_id"]))

            # 3. Remove old sale_items + doctor_rewards
            db.execute("DELETE FROM sale_items WHERE sale_id = ?", (sale_id,))
            db.execute("DELETE FROM doctor_rewards WHERE sale_id = ?", (sale_id,))

            # 4. Remove old accounting entries
            old_entries = db.fetchall(
                "SELECT id FROM journal_entries WHERE reference_type='sale' AND reference_id=?",
                (sale_id,),
            )
            for e in old_entries:
                db.execute("DELETE FROM journal_lines WHERE journal_id = ?", (e["id"],))
            db.execute("DELETE FROM journal_entries WHERE reference_type='sale' AND reference_id=?", (sale_id,))

            # 5. Remove old debt if credit
            payment_method = os_dict.get("payment_method", "cash")
            customer_id = os_dict.get("customer_id")
            if payment_method == "credit" and customer_id:
                old_debt = db.fetchone("SELECT * FROM debts WHERE sale_id = ?", (sale_id,))
                if old_debt:
                    old_remaining = to_decimal(old_debt["remaining_amount"])
                    cust = db.fetchone("SELECT * FROM customers WHERE id = ?", (customer_id,))
                    if cust:
                        curr = to_decimal(cust["total_debt"])
                        db.execute("UPDATE customers SET total_debt=? WHERE id=?",
                                   (from_decimal(max(curr - old_remaining, DECIMAL_ZERO)), customer_id))
                    db.execute("DELETE FROM debts WHERE sale_id = ?", (sale_id,))

            # 6. Update sale record
            paid = to_decimal(os_dict.get("paid_amount", "0"))
            db.execute(
                "UPDATE sales SET total_amount=?, discount=?, paid_amount=? WHERE id=?",
                (from_decimal(net_total), from_decimal(discount_amt), from_decimal(paid), sale_id),
            )

            # 7. Insert new items + deduct stock + doctor rewards
            for item in self.current_items:
                if item["quantity"] <= 0:
                    continue
                cursor = db.execute(
                    "INSERT INTO sale_items (sale_id, product_id, quantity, unit_price, total_price) VALUES (?, ?, ?, ?, ?)",
                    (sale_id, item["product_id"], item["quantity"],
                     from_decimal(item["unit_price"]), from_decimal(item["total_price"])),
                )
                sale_item_id = cursor.lastrowid
                prod = db.fetchone("SELECT sale_price FROM products WHERE id = ?", (item["product_id"],))
                sp = to_decimal(prod["sale_price"]) if prod else DECIMAL_ZERO
                strip_eq = int(to_decimal(item["total_price"]) / sp) if sp else item["quantity"]
                db.execute("UPDATE products SET stock_quantity = stock_quantity - ? WHERE id = ?",
                           (max(strip_eq, 0), item["product_id"]))
                product = db.fetchone("SELECT category_id FROM products WHERE id = ?", (item["product_id"],))
                cat_id = product["category_id"] if product else None
                if self.selected_doctor:
                    reward = self.doc_ctrl.calculate_reward_for_doctor(
                        self.selected_doctor["id"], item["product_id"],
                        from_decimal(item["unit_price"]), cat_id,
                    )
                    if reward:
                        reward_val = to_decimal(reward["reward_value"])
                        if reward["reward_type"] != "percentage":
                            reward_val *= to_decimal(item["quantity"])
                        self.doc_ctrl.record_reward(
                            sale_id, sale_item_id, item["product_id"],
                            reward["doctor_id"], reward["reward_type"], from_decimal(reward_val),
                            modified_price=reward.get("modified_price", "0.00"),
                            original_price=reward.get("original_price", "0.00"),
                            doctor_share=from_decimal(reward_val),
                        )

            # 8. Create new accounting entry
            self.sale_ctrl.acct.record_sale_transaction(
                sale_id, from_decimal(net_total), from_decimal(paid), payment_method,
            )

            # 9. Create new debt if credit
            if payment_method == "credit" and customer_id:
                remaining = net_total - paid
                if remaining > DECIMAL_ZERO:
                    db.execute(
                        "INSERT INTO debts (sale_id, customer_id, amount, paid_amount, remaining_amount, status) VALUES (?, ?, ?, ?, ?, 'pending')",
                        (sale_id, customer_id, from_decimal(net_total), from_decimal(paid), from_decimal(remaining)),
                    )
                    db.execute(
                        "UPDATE customers SET total_debt = printf('%.2f', CAST(total_debt AS REAL) + ?) WHERE id = ?",
                        (from_decimal(remaining), customer_id),
                    )

            self.sale_completed.emit(sale_id)
            QMessageBox.information(self, "✓ تم التعديل", "تم تعديل الفاتورة بنجاح.\nإرجاع المواد السابقة للمخزن وتطبيق التغييرات.")
            self._exit_return_mode()
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            with open(r"D:\pharma\data\debug_error.txt", "a", encoding="utf-8") as f:
                f.write(f"ERROR in _save_edited_invoice:\n{tb}\n---\n")
            QMessageBox.critical(self, "خطأ", f"حدث خطأ أثناء تعديل الفاتورة:\n{str(e)}\n\nالتفاصيل كُتبت في data/debug_error.txt")
            return

    def _admin_delete_invoice(self):
        """Admin only: fully delete/void an invoice (any date)."""
        from PyQt5.QtWidgets import QInputDialog
        sale_id, ok = QInputDialog.getInt(
            self, "🗑️ حذف فاتورة", "أدخل رقم الفاتورة:", 1, 1, 9999999, 1
        )
        if not ok:
            return
        sale = self.sale_ctrl.get_sale_by_id(sale_id)
        if not sale:
            QMessageBox.warning(self, "خطأ", "الفاتورة غير موجودة")
            return

        items = self.sale_ctrl.get_sale_items(sale_id)
        msg = f"فاتورة #{sale_id}\n"
        msg += f"التاريخ: {sale['created_at']}\n"
        msg += f"الإجمالي: {format_currency(sale['total_amount'])}\n"
        msg += f"طريقة الدفع: {sale['payment_method']}\n"
        msg += f"عدد المواد: {len(items)}\n\n"
        msg += "⚠️ سيتم:\n• إرجاع المواد للمخزن\n• عكس القيود المحاسبية\n• حذف الفاتورة نهائياً"
        confirm = QMessageBox.question(self, "تأكيد الحذف", msg,
                                       QMessageBox.Yes | QMessageBox.No)
        if confirm != QMessageBox.Yes:
            return

        try:
            items_data = []
            for si in items:
                items_data.append({
                    "sale_item_id": si["id"],
                    "product_id": si["product_id"],
                    "quantity": si["quantity"],
                    "unit_price": si["unit_price"],
                    "total_price": si["total_price"],
                })
            self.return_ctrl.create_return(
                sale_id, self.user_data["id"], items_data,
                "حذف فاتورة من المدير",
            )
            self.db.execute("DELETE FROM sale_items WHERE sale_id = ?", (sale_id,))
            self.db.execute("DELETE FROM sales WHERE id = ?", (sale_id,))
            self.sale_completed.emit(sale_id)
            QMessageBox.information(self, "✓ تم", f"تم حذف الفاتورة #{sale_id} وعكس جميع القيود")
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"حدث خطأ أثناء الحذف:\n{str(e)}")
            import traceback
            traceback.print_exc()
