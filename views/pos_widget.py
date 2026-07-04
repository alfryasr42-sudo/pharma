from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QComboBox, QDoubleSpinBox, QSpinBox,
    QAbstractItemView, QApplication, QFrame, QGraphicsDropShadowEffect,
    QSizePolicy, QCompleter,
)
from PyQt5.QtCore import (
    Qt, QTimer, pyqtSignal, QEvent, QStringListModel, QLocale,
)
from PyQt5.QtGui import (
    QFont, QKeySequence, QColor, QPainter, QLinearGradient, QBrush,
)
from PyQt5.QtWidgets import QShortcut
from utils.modern_msgbox import ModernMessageBox as QMessageBox

from controllers.product_controller import ProductController
from controllers.sale_controller import SaleController
from controllers.customer_controller import CustomerController
from controllers.doctor_controller import DoctorController
from utils.decimal_handler import to_decimal, from_decimal, format_currency, DECIMAL_ZERO
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
        for d in self.doc_ctrl.get_all():
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
        self._sum_total_lbl = _label("0.00", "#10b981", 26, True)
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
        unit_row.setSpacing(10)
        unit_row.setAlignment(Qt.AlignCenter)
        unit_row.addWidget(_label("نوع البيع:", "#94a3b8", 15, True))
        self._btn_pack = QPushButton("📦  علبة")
        self._btn_pack.setCheckable(True)
        self._btn_pack.setFixedSize(120, 48)
        self._btn_pack.setCursor(Qt.PointingHandCursor)
        self._btn_unit = QPushButton("💊  مفرد")
        self._btn_unit.setCheckable(True)
        self._btn_unit.setChecked(True)
        self._btn_unit.setFixedSize(120, 48)
        self._btn_unit.setCursor(Qt.PointingHandCursor)
        btn_style = (
            "QPushButton{background:#1e293b;color:#94a3b8;border:2px solid #334155;"
            "border-radius:10px;font-size:16px;font-weight:700}"
            "QPushButton:hover{background:#334155;color:#f1f5f9;border-color:#60a5fa}"
            "QPushButton:checked{background:#1e3a5f;color:#38bdf8;border-color:#38bdf8}"
        )
        self._btn_pack.setStyleSheet(btn_style)
        self._btn_unit.setStyleSheet(btn_style)
        self._btn_pack.clicked.connect(lambda: self._set_sell_unit(False))
        self._btn_unit.clicked.connect(lambda: self._set_sell_unit(True))
        unit_row.addWidget(self._btn_pack)
        unit_row.addWidget(self._btn_unit)
        unit_row.addStretch()
        l_main.addLayout(unit_row)

        # ── Deal/Discount Info Frame ──
        self._deal_frame = QFrame()
        self._deal_frame.setStyleSheet(
            "QFrame{background:#1a1a2e;border:1.5px solid #7c3aed50;border-radius:10px;padding:6px}"
        )
        self._deal_frame.setVisible(False)
        dl = QVBoxLayout(self._deal_frame)
        dl.setContentsMargins(10, 6, 10, 6)
        dl.setSpacing(3)

        self._deal_title_lbl = _label("", "#a78bfa", 14, True)
        self._deal_title_lbl.setAlignment(Qt.AlignCenter)
        dl.addWidget(self._deal_title_lbl)

        deal_prices_row = QHBoxLayout()
        deal_prices_row.setSpacing(12)
        deal_prices_row.setAlignment(Qt.AlignCenter)

        self._deal_orig_lbl = _label("", "#94a3b8", 14)
        self._deal_orig_lbl.setAlignment(Qt.AlignCenter)
        deal_prices_row.addWidget(self._deal_orig_lbl)

        self._deal_arrow_lbl = _label("←", "#64748b", 16, True)
        self._deal_arrow_lbl.setAlignment(Qt.AlignCenter)
        deal_prices_row.addWidget(self._deal_arrow_lbl)

        self._deal_new_lbl = _label("", "#f1f5f9", 16, True)
        self._deal_new_lbl.setAlignment(Qt.AlignCenter)
        deal_prices_row.addWidget(self._deal_new_lbl)

        dl.addLayout(deal_prices_row)

        self._deal_cost_lbl = _label("", "#fbbf24", 14, True)
        self._deal_cost_lbl.setAlignment(Qt.AlignCenter)
        dl.addWidget(self._deal_cost_lbl)

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
            lbl = QLabel("0.00")
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
            box.setDecimals(2)
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
        self.paid_input.setDecimals(2)
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
        self.clear_btn.setStyleSheet(_btn_style("#d97706", "white", 19, 44))
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
        # إذا لم يكن التركيز على أي حقل إدخال، أو كان على عنصر غير تفاعلي
        editable_types = (QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox)
        if focused is None or not isinstance(focused, editable_types):
            self._focus_barcode()
        elif focused is self.barcode_input:
            pass  # already on barcode

    def mousePressEvent(self, event):
        """عند النقر على منطقة فارغة يعود التركيز للباركود"""
        focused = QApplication.focusWidget()
        if focused and focused is not self.barcode_input:
            # تأخير صغير لإتاحة معالجة حدث النقر أولاً
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
                stk_item.setForeground(QColor("#f59e0b"))
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
        self._is_pack = not is_unit
        if self._last_scanned_product:
            self._show_product_price(self._last_scanned_product)

    def _show_product_price(self, product):
        strip_price = to_decimal(product["sale_price"])
        qty = int(dict(product).get("strips_per_pack", 1))
        if self._is_pack:
            price = strip_price * qty
            unit_name = "للعلبة"
        else:
            price = strip_price
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

    def _add_product_by_barcode(self, barcode):
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
            self._product_stock_lbl.setStyleSheet("font-size:22px;font-weight:700;color:#f59e0b;background:transparent")
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
        sell_unit = self._get_unit_name()
        unit_price = self._get_unit_price(product)
        for item in self.current_items:
            if item["product_id"] == product["id"] and item.get("sell_unit") == sell_unit:
                existing = item
                break

        original_strip_price = to_decimal(product["sale_price"])
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
                    deal_info = {
                        "type": "deal",
                        "original": original_strip_price,
                        "modified": unit_price,
                        "cost": reward_val,
                        "purchase": to_decimal(product.get("purchase_price", "0")),
                    }
                elif deal_type == "discount":
                    unit_price = max(unit_price - reward_val, DECIMAL_ZERO)
                    deal_info = {
                        "type": "discount",
                        "original": original_strip_price,
                        "modified": unit_price,
                        "cost": reward_val,
                        "purchase": to_decimal(product.get("purchase_price", "0")),
                    }

        # ── Show deal info frame ──
        if deal_info and getattr(self, '_show_deal_cost', False):
            self._deal_frame.setVisible(True)
            if deal_info["type"] == "deal":
                profit = deal_info["modified"] - deal_info["purchase"] - deal_info["cost"]
                self._deal_title_lbl.setText(f"🏷 ديل — د. {self.selected_doctor['name']}")
                self._deal_title_lbl.setStyleSheet("font-size:14px;font-weight:700;color:#a78bfa;background:transparent")
                self._deal_frame.setStyleSheet(
                    "QFrame{background:#1a1a2e;border:1.5px solid #7c3aed50;border-radius:10px;padding:6px}"
                )
                self._deal_cost_lbl.setText(f"حصة الطبيب: {format_currency(deal_info['cost'])}")
                self._deal_cost_lbl.setStyleSheet("font-size:14px;font-weight:700;color:#fbbf24;background:transparent")
                self._deal_orig_lbl.setText(f"الكلفة: {format_currency(deal_info['purchase'])}")
                self._deal_new_lbl.setText(f"صافي الربح: {format_currency(profit)}")
                self._deal_new_lbl.setStyleSheet("font-size:14px;font-weight:700;color:#38bdf8;background:transparent")
            else:
                self._deal_title_lbl.setText(f"🏷 تخفيض — د. {self.selected_doctor['name']}")
                self._deal_title_lbl.setStyleSheet("font-size:14px;font-weight:700;color:#34d399;background:transparent")
                self._deal_frame.setStyleSheet(
                    "QFrame{background:#0a1a1a;border:1.5px solid #10b98150;border-radius:10px;padding:6px}"
                )
                self._deal_cost_lbl.setText(f"قيمة الخصم: {format_currency(deal_info['cost'])}")
                self._deal_cost_lbl.setStyleSheet("font-size:14px;font-weight:700;color:#34d399;background:transparent")
                self._deal_orig_lbl.setText(f"الأصلي: {format_currency(deal_info['original'])}")
                self._deal_new_lbl.setText(f"الجديد: {format_currency(deal_info['modified'])}")
                self._deal_new_lbl.setStyleSheet("font-size:16px;font-weight:700;color:#f1f5f9;background:transparent")
        else:
            self._deal_frame.setVisible(False)

        if existing:
            existing["quantity"] += 1
            existing["unit_price"] = unit_price
            existing["original_price"] = original_strip_price
            existing["total_price"] = existing["quantity"] * existing["unit_price"]
            existing["deal_type"] = deal_info["type"] if deal_info else None
        else:
            self.current_items.append({
                "product_id": product["id"],
                "barcode": product["barcode"],
                "name": product["name"],
                "quantity": 1,
                "unit_price": unit_price,
                "original_price": original_strip_price,
                "total_price": unit_price,
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
            price_spin.setDecimals(2)
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
        self._sum_remain_lab_lbl.setText("0.00")
        self._sum_remain_patient_lbl.setText("0.00")
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
        finally:
            self._is_calculating = False

    def _update_totals_from_paid(self):
        pass  # paid is now auto-filled, no manual update needed

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
        finally:
            self._is_calculating = False

    def _on_payment_method_changed(self, method):
        self._on_pay_btn(method)

    # ──────────────────────────────────────────
    # Save / Clear
    # ──────────────────────────────────────────
    @safe_operation("عذراً، حدث خطأ أثناء حفظ الفاتورة.")
    def _save_invoice(self):
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
                        deal_type = reward.get("deal_type", "deal")
                        reward_val = to_decimal(reward.get("reward_value", "0"))
                        if deal_type == "deal":
                            new_strip_price = strip_price
                        elif deal_type == "discount":
                            new_strip_price = max(strip_price - reward_val, DECIMAL_ZERO)
                        else:
                            new_strip_price = strip_price
                        # Convert back to sell unit price
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
