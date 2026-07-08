from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QFormLayout, QDoubleSpinBox, QMessageBox,
    QAbstractItemView, QGroupBox, QComboBox, QTabWidget,
    QFrame, QDateEdit, QSizePolicy,
)
from PyQt5.QtCore import Qt, QDate, QLocale
from PyQt5.QtGui import QColor, QFont, QPainter, QLinearGradient, QBrush
from utils.modern_msgbox import ModernMessageBox as QMessageBox

from controllers.doctor_controller import DoctorController
from controllers.product_controller import ProductController
from utils.decimal_handler import to_decimal, from_decimal, format_currency, DECIMAL_ZERO

# ── palette ────────────────────────────────────────────────────
_BG      = "#0b1120"
_CARD    = "#141d2e"
_BORDER  = "#2a3f5f"
_GREEN   = "#059669"
_BLUE    = "#7ba3ff"
_BLUE2   = "#4a8fe7"
_RED     = "#ef4444"
_AMBER   = "#d4a040"
_PURPLE  = "#8b7cf7"
_TEXT    = "#f1f5f9"
_MUTED   = "#c8d6e5"
_DIM     = "#8899bb"

_TABLE_SS = (
    f"QTableWidget{{background:{_CARD};border:none;border-radius:8px;color:{_TEXT};gridline-color:#1e2d45;font-size:17px}}"
    f"QHeaderView::section{{background:#1e2d45;color:{_MUTED};padding:14px 16px;border:none;font-size:17px;font-weight:700}}"
    f"QTableWidget::item{{padding:12px;border-bottom:1px solid #1e2d4560;font-size:17px}}"
    f"QTableWidget::item:selected{{background:{_BLUE2}40}}"
    f"QTableWidget::item:alternate{{background:#0b112040}}"
)

_BTN_SS = (
    f"QPushButton{{font-size:20px;font-weight:700;padding:14px 36px;"
    f"background:{_GREEN};color:white;border:none;border-radius:12px}}"
    f"QPushButton:hover{{background:#047857}}"
    f"QPushButton:pressed{{background:#065f46}}"
)

_BTN_BLUE_SS = (
    f"QPushButton{{font-size:20px;font-weight:700;padding:14px 36px;"
    f"background:{_BLUE2};color:white;border:none;border-radius:12px}}"
    f"QPushButton:hover{{background:#3a7bd5}}"
)

_INPUT_SS = (
    f"QLineEdit,QDoubleSpinBox,QSpinBox,QComboBox,QDateEdit{{"
    f"background:transparent;border:none;border-bottom:2px solid {_BORDER};"
    f"color:{_TEXT};font-size:20px;font-weight:600;padding:10px 6px}}"
    f"QLineEdit:focus,QDoubleSpinBox:focus,QComboBox:focus{{border-bottom:2px solid {_BLUE2}}}"
)

_TAB_SS = (
    f"QTabWidget::pane{{border:none;border-radius:8px;background:transparent}}"
    f"QTabBar::tab{{background:#1e2d45;color:{_DIM};padding:14px 32px;font-size:19px;font-weight:600;"
    f"border-top-left-radius:8px;border-top-right-radius:8px;margin-right:2px}}"
    f"QTabBar::tab:selected{{background:{_CARD};color:{_TEXT};border-bottom:3px solid {_BLUE2}}}"
    f"QTabBar::tab:hover{{background:{_CARD};color:{_TEXT}}}"
)


def _card_label(text, value, color=_GREEN, parent=None):
    """Create a compact glass stat card."""
    frame = QFrame(parent)
    frame.setFixedSize(200, 72)
    frame.setStyleSheet(
        f"QFrame{{background:{_CARD};border-radius:8px;padding:0}}"
    )
    lay = QVBoxLayout(frame)
    lay.setSpacing(2)
    lay.setContentsMargins(8, 6, 8, 6)
    lbl = QLabel(text)
    lbl.setStyleSheet(f"font-size:13px;color:{_DIM};background:transparent")
    lbl.setAlignment(Qt.AlignCenter)
    val_lbl = QLabel(str(value))
    val_lbl.setStyleSheet(f"font-size:20px;font-weight:800;color:{color};background:transparent")
    val_lbl.setAlignment(Qt.AlignCenter)
    lay.addWidget(lbl)
    lay.addWidget(val_lbl)
    return frame, val_lbl


class DoctorsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.doc_ctrl = DoctorController()
        self.setMinimumWidth(900)
        self._setup_ui()
        self._load_doctors()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QBrush(QColor("#0b1120")))
        p.end()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 14, 20, 14)

        # ── Tabs ──
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(_TAB_SS)

        # ── Tab 1: Doctors (redesigned) ──
        doctors_tab = QWidget()
        doc_lay = QVBoxLayout(doctors_tab)
        doc_lay.setSpacing(8)
        doc_lay.setContentsMargins(0, 4, 0, 4)

        # Top bar: [search + refresh] ... [count] ... [name input + add]
        top_bar = QHBoxLayout()
        top_bar.setSpacing(10)

        # Left side (end in RTL) — search + refresh
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍  ابحث عن طبيب...")
        self.search_input.setFixedWidth(240)
        self.search_input.setFixedHeight(44)
        self.search_input.setStyleSheet(_INPUT_SS)
        self.search_input.textChanged.connect(self._on_search)
        top_bar.addWidget(self.search_input)

        refresh_btn = QPushButton("↻")
        refresh_btn.setFixedSize(44, 44)
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.setStyleSheet(
            f"QPushButton{{background:{_CARD};color:{_MUTED};border:2px solid {_BORDER};"
            f"border-radius:8px;font-size:18px;font-weight:700}}"
            f"QPushButton:hover{{border-color:{_BLUE2};color:{_TEXT}}}"
        )
        refresh_btn.clicked.connect(self._load_doctors)
        top_bar.addWidget(refresh_btn)

        top_bar.addStretch(2)

        # Count badge
        self._doctor_count_lbl = QLabel("عدد الأطباء: 0")
        self._doctor_count_lbl.setStyleSheet(
            f"font-size:15px;font-weight:700;color:{_DIM};background:{_CARD};"
            f"border-radius:8px;padding:6px 16px;border:1px solid {_BORDER}"
        )
        top_bar.addWidget(self._doctor_count_lbl)

        top_bar.addStretch(2)

        # Right side (start in RTL) — name input + add
        self._add_name_input = QLineEdit()
        self._add_name_input.setPlaceholderText("👨‍⚕️  اسم الطبيب الجديد")
        self._add_name_input.setFixedWidth(200)
        self._add_name_input.setFixedHeight(44)
        self._add_name_input.setStyleSheet(_INPUT_SS)
        self._add_name_input.returnPressed.connect(self._show_add_dialog)
        top_bar.addWidget(self._add_name_input)

        add_btn = QPushButton("+ إضافة")
        add_btn.setFixedHeight(44)
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setStyleSheet(_BTN_SS)
        add_btn.clicked.connect(self._show_add_dialog)
        top_bar.addWidget(add_btn)

        doc_lay.addLayout(top_bar)

        self.doctor_table = QTableWidget()
        self.doctor_table.setColumnCount(6)
        self.doctor_table.setHorizontalHeaderLabels(["ID", "الاسم", "التخصص", "نسبة العمولة", "الهاتف", ""])
        self.doctor_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.doctor_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.doctor_table.setAlternatingRowColors(True)
        self.doctor_table.verticalHeader().setVisible(False)
        self.doctor_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.doctor_table.doubleClicked.connect(self._on_doctor_double_click)
        self.doctor_table.setStyleSheet(_TABLE_SS)
        doc_lay.addWidget(self.doctor_table, 1)

        self.tabs.addTab(doctors_tab, "👨‍⚕️ الأطباء")

        # Tab 2: Rules
        rules_tab = QWidget()
        rules_lay = QVBoxLayout(rules_tab)
        rules_lay.setContentsMargins(0, 8, 0, 0)

        self.rules_table = QTableWidget()
        self.rules_table.setColumnCount(6)
        self.rules_table.setHorizontalHeaderLabels(["ID", "\u0627\u0644\u0637\u0628\u064a\u0628", "\u0627\u0644\u0645\u0646\u062a\u062c/\u0627\u0644\u062a\u0635\u0646\u064a\u0641", "\u0627\u0644\u0646\u0648\u0639", "\u0646\u0648\u0639 \u0627\u0644\u062d\u0635\u0629", "\u0627\u0644\u0642\u064a\u0645\u0629"])
        self.rules_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.rules_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.rules_table.setAlternatingRowColors(True)
        self.rules_table.verticalHeader().setVisible(False)
        self.rules_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.rules_table.setStyleSheet(_TABLE_SS)
        rules_lay.addWidget(self.rules_table)

        rules_actions = QHBoxLayout()
        self.add_rule_btn = QPushButton("+ \u0625\u0636\u0627\u0641\u0629 \u0642\u0627\u0639\u062f\u0629 \u062f\u064a\u0644/\u062a\u062e\u0641\u064a\u0636")
        self.add_rule_btn.setStyleSheet(_BTN_SS)
        self.add_rule_btn.setCursor(Qt.PointingHandCursor)
        self.add_rule_btn.clicked.connect(self._show_rule_dialog)
        rules_actions.addWidget(self.add_rule_btn)
        rules_actions.addStretch()
        rules_lay.addLayout(rules_actions)

        self.tabs.addTab(rules_tab, "\U0001f4cb \u0642\u0648\u0627\u0639\u062f \u0627\u0644\u062f\u064a\u0644\u0627\u062a")

        # Tab 3: Earnings + Doctor Details (merged)
        earnings_tab = QWidget()
        earn_lay = QVBoxLayout(earnings_tab)
        earn_lay.setContentsMargins(0, 8, 0, 0)
        earn_lay.setSpacing(10)

        # ── Summary cards ──
        cards_row = QHBoxLayout()
        cards_row.setSpacing(12)
        cards_row.addStretch(1)
        f1, self._earn_total_lbl = _card_label("إجمالي حصص الأطباء", "0", _AMBER)
        cards_row.addWidget(f1)
        f2, self._earn_deals_lbl = _card_label("عدد الديلات", "0", _PURPLE)
        cards_row.addWidget(f2)
        f3, self._earn_doctors_lbl = _card_label("أطباء نشطون", "0", _BLUE)
        cards_row.addWidget(f3)
        cards_row.addStretch(1)
        earn_lay.addLayout(cards_row)

        # ── Date filter ──
        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)
        filter_lbl = QLabel("من:")
        filter_lbl.setStyleSheet(f"color:{_MUTED};font-size:16px;background:transparent")
        filter_row.addWidget(filter_lbl)
        self._earn_from = QDateEdit()
        self._earn_from.setCalendarPopup(True)
        self._earn_from.setDate(QDate.currentDate().addMonths(-1))
        self._earn_from.setDisplayFormat("yyyy-MM-dd")
        self._earn_from.setFixedHeight(48)
        self._earn_from.setLocale(QLocale(QLocale.English, QLocale.UnitedStates))
        self._earn_from.setStyleSheet(_INPUT_SS)
        filter_row.addWidget(self._earn_from)
        filter_lbl2 = QLabel("إلى:")
        filter_lbl2.setStyleSheet(f"color:{_MUTED};font-size:16px;background:transparent")
        filter_row.addWidget(filter_lbl2)
        self._earn_to = QDateEdit()
        self._earn_to.setCalendarPopup(True)
        self._earn_to.setDate(QDate.currentDate())
        self._earn_to.setDisplayFormat("yyyy-MM-dd")
        self._earn_to.setFixedHeight(48)
        self._earn_to.setLocale(QLocale(QLocale.English, QLocale.UnitedStates))
        self._earn_to.setStyleSheet(self._earn_from.styleSheet())
        filter_row.addWidget(self._earn_to)
        filter_btn = QPushButton("عرض")
        filter_btn.setStyleSheet(_BTN_BLUE_SS)
        filter_btn.setCursor(Qt.PointingHandCursor)
        filter_btn.setFixedHeight(52)
        filter_btn.clicked.connect(self._load_earnings)
        filter_row.addWidget(filter_btn)
        filter_row.addStretch()
        earn_lay.addLayout(filter_row)

        # ── Doctor summary table ──
        self.earn_summary_table = QTableWidget()
        self.earn_summary_table.setColumnCount(4)
        self.earn_summary_table.setHorizontalHeaderLabels(["الطبيب", "عدد الفواتير", "إجمالي الحصة", ""])
        self.earn_summary_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.earn_summary_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.earn_summary_table.verticalHeader().setVisible(False)
        self.earn_summary_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.earn_summary_table.setStyleSheet(_TABLE_SS)
        self.earn_summary_table.setMaximumHeight(220)
        self.earn_summary_table.setColumnHidden(3, True)
        self.earn_summary_table.clicked.connect(self._on_earning_summary_click)
        earn_lay.addWidget(self.earn_summary_table)

        # ── Separator ──
        sep = QFrame()
        sep.setFixedHeight(2)
        sep.setStyleSheet(f"background:{_BORDER}")
        earn_lay.addWidget(sep)

        # ── Doctor detail section (hidden initially) ──
        self._detail_frame = QFrame()
        self._detail_frame.setVisible(False)
        df_lay = QVBoxLayout(self._detail_frame)
        df_lay.setContentsMargins(0, 4, 0, 0)
        df_lay.setSpacing(8)

        self._detail_header = QLabel("")
        self._detail_header.setStyleSheet(f"font-size:18px;font-weight:800;color:{_TEXT};background:transparent;padding:4px 0")
        df_lay.addWidget(self._detail_header)

        prod_lbl = QLabel("📦  المنتجات المرتبطة (ديل / تخفيض):")
        prod_lbl.setStyleSheet(f"font-size:14px;font-weight:700;color:{_MUTED};background:transparent")
        df_lay.addWidget(prod_lbl)

        self._detail_products_table = QTableWidget()
        self._detail_products_table.setColumnCount(3)
        self._detail_products_table.setHorizontalHeaderLabels(["المنتج", "ديل %", "تخفيض %"])
        self._detail_products_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._detail_products_table.setAlternatingRowColors(True)
        self._detail_products_table.verticalHeader().setVisible(False)
        self._detail_products_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._detail_products_table.setMaximumHeight(180)
        self._detail_products_table.setStyleSheet(
            f"QTableWidget{{background:{_CARD};border:none;border-radius:6px;color:{_TEXT};gridline-color:#1e2d45;font-size:14px}}"
            f"QHeaderView::section{{background:#1e2d45;color:{_MUTED};padding:8px;border:none;font-size:13px;font-weight:700}}"
            f"QTableWidget::item{{padding:6px;border-bottom:1px solid #1e2d4560;font-size:13px}}"
            f"QTableWidget::item:alternate{{background:#0b112040}}"
        )
        df_lay.addWidget(self._detail_products_table)

        earn_lbl = QLabel("💰  أرباح الطبيب:")
        earn_lbl.setStyleSheet(f"font-size:14px;font-weight:700;color:{_MUTED};background:transparent")
        df_lay.addWidget(earn_lbl)

        self._detail_earn_table = QTableWidget()
        self._detail_earn_table.setColumnCount(5)
        self._detail_earn_table.setHorizontalHeaderLabels(["رقم الفاتورة", "المنتج", "السعر الأصلي", "السعر المعدل", "حصة الطبيب"])
        self._detail_earn_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._detail_earn_table.setAlternatingRowColors(True)
        self._detail_earn_table.verticalHeader().setVisible(False)
        self._detail_earn_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._detail_earn_table.setStyleSheet(_TABLE_SS)
        df_lay.addWidget(self._detail_earn_table, 1)

        earn_lay.addWidget(self._detail_frame, 1)
        self.tabs.addTab(earnings_tab, "💰  الحصص والأرباح")

        layout.addWidget(self.tabs, 1)

    # ── Data loading ──

    def _load_doctors(self):
        doctors = self.doc_ctrl.get_all()
        self._populate_doctors(doctors)
        self._load_rules()
        self._load_earnings()

    def _load_rules(self):
        rules = self.doc_ctrl.get_reward_rules()
        self._populate_rules(rules)

    def _load_earnings(self):
        try:
            summary = self.doc_ctrl.get_all_earnings_summary()
            self.earn_summary_table.setRowCount(len(summary))
            total_share = 0
            total_invoices = 0
            for i, s in enumerate(summary):
                s = dict(s)
                self.earn_summary_table.setItem(i, 0, QTableWidgetItem(s.get("doctor_name", "")))
                invoices = s.get("total_invoices", 0)
                self.earn_summary_table.setItem(i, 1, QTableWidgetItem(str(invoices)))
                share = s.get("total_share", "0.00")
                share_item = QTableWidgetItem(format_currency(share))
                share_item.setForeground(QColor(_AMBER))
                share_item.setFont(QFont("Segoe UI", 14, QFont.Bold))
                self.earn_summary_table.setItem(i, 2, share_item)
                # Store doctor_id
                id_item = QTableWidgetItem(str(s.get("doctor_id", 0)))
                self.earn_summary_table.setItem(i, 3, id_item)
                total_share += float(to_decimal(share))
                total_invoices += invoices

            self._earn_total_lbl.setText(format_currency(to_decimal(str(total_share))))
            self._earn_deals_lbl.setText(str(total_invoices))
            self._earn_doctors_lbl.setText(str(len(summary)))
        except Exception:
            pass

    def _on_earning_summary_click(self, index):
        row = index.row()
        id_item = self.earn_summary_table.item(row, 3)
        if not id_item:
            return
        doctor_id = int(id_item.text())
        doctor = self.doc_ctrl.get_by_id(doctor_id)
        if not doctor:
            return
        # Show detail section
        self._show_doctor_detail(doctor)

    def _show_doctor_detail(self, doctor):
        doc = dict(doctor)
        self._detail_frame.setVisible(True)
        start = self._earn_from.date().toString("yyyy-MM-dd")
        end = self._earn_to.date().toString("yyyy-MM-dd")

        # Header
        self._detail_header.setText(f"👨‍⚕️  {doc['name']}  —  {doc.get('specialization') or '—'}  |  📞 {doc.get('phone') or '—'}")

        # Products
        products = self.doc_ctrl.get_doctor_products(doc["id"])
        prod_map = {}
        for r in products:
            rd = dict(r)
            pid = rd["product_id"]
            if pid not in prod_map:
                prod_map[pid] = {"name": rd["product_name"], "deal_pct": "0", "discount_pct": "0"}
            if rd.get("deal_type") == "discount":
                prod_map[pid]["discount_pct"] = rd["reward_value"]
            else:
                prod_map[pid]["deal_pct"] = rd["reward_value"]
        self._detail_products_table.setRowCount(len(prod_map))
        for i, (pid, info) in enumerate(prod_map.items()):
            self._detail_products_table.setItem(i, 0, QTableWidgetItem(info["name"]))
            deal = QTableWidgetItem(f"{format_currency(info['deal_pct'])} %")
            deal.setForeground(QColor(_PURPLE))
            deal.setFont(QFont("Segoe UI", 12, QFont.Bold))
            self._detail_products_table.setItem(i, 1, deal)
            disc = QTableWidgetItem(f"{format_currency(info['discount_pct'])} %")
            disc.setForeground(QColor(_GREEN))
            disc.setFont(QFont("Segoe UI", 12, QFont.Bold))
            self._detail_products_table.setItem(i, 2, disc)

        # Earnings
        try:
            earnings = self.doc_ctrl.get_doctor_earnings(doc["id"], start, end)
            self._detail_earn_table.setRowCount(len(earnings))
            total_share = DECIMAL_ZERO
            for i, e in enumerate(earnings):
                e = dict(e)
                self._detail_earn_table.setItem(i, 0, QTableWidgetItem(str(e.get("invoice_number", ""))))
                self._detail_earn_table.setItem(i, 1, QTableWidgetItem(e.get("product_name", "")))
                orig = QTableWidgetItem(format_currency(e.get("original_price", "0")))
                orig.setForeground(QColor(_MUTED))
                self._detail_earn_table.setItem(i, 2, orig)
                mod = QTableWidgetItem(format_currency(e.get("modified_price", "0")))
                mod.setForeground(QColor(_BLUE))
                self._detail_earn_table.setItem(i, 3, mod)
                share_val = e.get("doctor_share", "0")
                share = QTableWidgetItem(format_currency(share_val))
                share.setForeground(QColor(_AMBER))
                share.setFont(QFont("Segoe UI", 13, QFont.Bold))
                self._detail_earn_table.setItem(i, 4, share)
                total_share += to_decimal(share_val)
            # Append total to header
            current = self._detail_header.text()
            total_str = format_currency(total_share)
            if "💰" not in current:
                self._detail_header.setText(current + f"  |  💰 {total_str} د.ع")
        except Exception:
            pass

    def _on_search(self, text):
        if len(text) >= 2:
            doctors = self.doc_ctrl.search(text)
            self._populate_doctors(doctors)
        elif len(text) == 0:
            self._load_doctors()

    def _populate_doctors(self, doctors):
        self.doctor_table.setRowCount(len(doctors))
        self._doctor_count_lbl.setText(f"عدد الأطباء: {len(doctors)}")
        for i, d in enumerate(doctors):
            d_dict = dict(d)
            self.doctor_table.setItem(i, 0, QTableWidgetItem(str(d["id"])))

            name_item = QTableWidgetItem(d["name"])
            name_item.setFont(QFont("Segoe UI", 14, QFont.Bold))
            self.doctor_table.setItem(i, 1, name_item)

            self.doctor_table.setItem(i, 2, QTableWidgetItem(d_dict.get("specialization") or ""))

            rate = format_currency(d_dict.get("commission_rate", "0")) + " %"
            rate_item = QTableWidgetItem(rate)
            rate_item.setForeground(QColor(_AMBER))
            self.doctor_table.setItem(i, 3, rate_item)

            self.doctor_table.setItem(i, 4, QTableWidgetItem(d_dict.get("phone") or ""))

            detail_btn = QPushButton("🔍 تفاصيل")
            detail_btn.setFixedSize(90, 32)
            detail_btn.setCursor(Qt.PointingHandCursor)
            detail_btn.setStyleSheet(
                f"QPushButton{{background:{_BLUE2};color:white;border:none;"
                f"border-radius:6px;font-size:12px;font-weight:700}}"
                f"QPushButton:hover{{background:#3a7bd5}}"
            )
            doc_id = d["id"]
            detail_btn.clicked.connect(lambda checked, did=doc_id: self._on_doctor_detail(did))
            self.doctor_table.setCellWidget(i, 5, detail_btn)
            self.doctor_table.setRowHeight(i, 54)

    def _populate_rules(self, rules):
        self.rules_table.setRowCount(len(rules))
        for i, r in enumerate(rules):
            r_dict = dict(r)
            self.rules_table.setItem(i, 0, QTableWidgetItem(str(r["id"])))
            self.rules_table.setItem(i, 1, QTableWidgetItem(r_dict.get("doctor_name") or ""))
            name = r_dict.get("product_name") or r_dict.get("category_name") or "\u062c\u0645\u064a\u0639 \u0627\u0644\u0645\u0646\u062a\u062c\u0627\u062a"
            self.rules_table.setItem(i, 2, QTableWidgetItem(name))

            # Deal type badge
            dt = r_dict.get("deal_type", "deal")
            if dt == "deal":
                badge = QTableWidgetItem("\u062f\u064a\u0644 \u2191")
                badge.setForeground(QColor(_PURPLE))
            else:
                badge = QTableWidgetItem("\u062a\u062e\u0641\u064a\u0636 \u2193")
                badge.setForeground(QColor(_GREEN))
            badge.setFont(QFont("Segoe UI", 12, QFont.Bold))
            self.rules_table.setItem(i, 3, badge)

            type_map = {"percentage": "\u0646\u0633\u0628\u0629 \u0645\u0626\u0648\u064a\u0629", "fixed": "\u0645\u0628\u0644\u063a \u0645\u0642\u0637\u0648\u0639"}
            self.rules_table.setItem(i, 4, QTableWidgetItem(type_map.get(r["reward_type"], r["reward_type"])))
            val = format_currency(r["reward_value"])
            if r["reward_type"] == "percentage":
                val += " %"
            val_item = QTableWidgetItem(val)
            val_item.setForeground(QColor(_AMBER))
            self.rules_table.setItem(i, 5, val_item)
            self.rules_table.setRowHeight(i, 50)

    def _on_doctor_double_click(self, index):
        row = index.row()
        item = self.doctor_table.item(row, 0)
        if not item:
            return
        doctor_id = int(item.text())
        doctor = self.doc_ctrl.get_by_id(doctor_id)
        if doctor:
            self._show_edit_dialog(doctor)

    def _on_doctor_detail(self, doctor_id):
        doctor = self.doc_ctrl.get_by_id(doctor_id)
        if not doctor:
            return
        self._show_doctor_detail(doctor)
        self.tabs.setCurrentIndex(2)

    def _show_add_dialog(self):
        name = self._add_name_input.text().strip()
        dialog = DoctorDialog(self)
        if name:
            dialog.name_input.setText(name)
        if dialog.exec_() == QDialog.Accepted:
            self._add_name_input.clear()
            self._load_doctors()

    def _show_edit_dialog(self, doctor):
        dialog = DoctorDialog(self, doctor)
        if dialog.exec_() == QDialog.Accepted:
            self._load_doctors()

    def _show_rule_dialog(self):
        dialog = RuleDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self._load_rules()


# ═══════════════════════════════════════════════════════════
# DoctorDialog
# ═══════════════════════════════════════════════════════════
_DIALOG_SS = (
    f"QDialog{{background:#0b1120;color:{_TEXT}}}"
    f"QLabel{{color:{_DIM};font-size:18px;background:transparent}}"
    f"QLineEdit,QDoubleSpinBox,QSpinBox,QComboBox,QDateEdit{{"
    f"background:transparent;border:none;border-bottom:2px solid {_BORDER};"
    f"color:{_TEXT};font-size:20px;font-weight:600;padding:10px 6px;min-height:36px}}"
    f"QLineEdit:focus,QDoubleSpinBox:focus,QComboBox:focus{{border-bottom:2px solid {_BLUE2}}}"
    f"QComboBox::drop-down{{border:none;width:30px}}"
    f"QComboBox QAbstractItemView{{background:#141d2e;color:{_TEXT};font-size:16px;selection-background-color:{_BLUE2}40}}"
)


class DoctorDialog(QDialog):
    def __init__(self, parent=None, doctor=None):
        super().__init__(parent)
        self.doctor = doctor
        self.doc_ctrl = DoctorController()
        self.setWindowTitle("\u062a\u0639\u062f\u064a\u0644 \u0637\u0628\u064a\u0628" if doctor else "\u0625\u0636\u0627\u0641\u0629 \u0637\u0628\u064a\u0628")
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.CustomizeWindowHint)
        self.setStyleSheet(_DIALOG_SS)
        self._setup_ui()
        if doctor:
            self._load_data(doctor)
        self.layout().setSizeConstraint(QLayout.SetFixedSize)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 20, 24, 20)

        title = QLabel("\u062a\u0639\u062f\u064a\u0644 \u0637\u0628\u064a\u0628" if self.doctor else "\u0625\u0636\u0627\u0641\u0629 \u0637\u0628\u064a\u0628 \u062c\u062f\u064a\u062f")
        title.setStyleSheet(f"font-size:24px;font-weight:800;color:{_TEXT};background:transparent")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(16)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("\u0627\u0633\u0645 \u0627\u0644\u0637\u0628\u064a\u0628")
        self.name_input.setFixedHeight(56)
        form.addRow("\U0001f464 \u0627\u0644\u0627\u0633\u0645:", self.name_input)

        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("\u0631\u0642\u0645 \u0627\u0644\u0647\u0627\u062a\u0641")
        self.phone_input.setFixedHeight(56)
        form.addRow("\U0001f4de \u0627\u0644\u0647\u0627\u062a\u0641:", self.phone_input)

        self.spec_input = QLineEdit()
        self.spec_input.setPlaceholderText("\u0627\u0644\u062a\u062e\u0635\u0635")
        self.spec_input.setFixedHeight(56)
        form.addRow("\U0001f393 \u0627\u0644\u062a\u062e\u0635\u0635:", self.spec_input)

        self.rate_input = QDoubleSpinBox()
        self.rate_input.setRange(0, 100)
        self.rate_input.setDecimals(2)
        self.rate_input.setSuffix(" %")
        self.rate_input.setValue(0)
        self.rate_input.setFixedHeight(56)
        form.addRow("\U0001f4c8 \u0646\u0633\u0628\u0629 \u0627\u0644\u0639\u0645\u0648\u0644\u0629:", self.rate_input)

        layout.addLayout(form)
        layout.addStretch()

        buttons = QHBoxLayout()
        buttons.setSpacing(12)
        save_btn = QPushButton("\U0001f4be  \u062d\u0641\u0638")
        save_btn.setStyleSheet(
            f"QPushButton{{font-size:19px;font-weight:700;background:{_GREEN};"
            f"color:white;border:none;border-radius:12px;padding:14px 32px}}"
            f"QPushButton:hover{{background:#047857}}"
        )
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.clicked.connect(self._save)

        cancel_btn = QPushButton("\u0625\u0644\u063a\u0627\u0621")
        cancel_btn.setStyleSheet(
            f"QPushButton{{font-size:19px;font-weight:600;background:{_BORDER};"
            f"color:{_MUTED};border:none;border-radius:12px;padding:14px 32px}}"
            f"QPushButton:hover{{background:#475569;color:{_TEXT}}}"
        )
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)

        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        buttons.addStretch()
        layout.addLayout(buttons)

    def _load_data(self, doctor):
        doctor = dict(doctor)
        self.name_input.setText(doctor["name"])
        self.phone_input.setText(doctor.get("phone") or "")
        self.spec_input.setText(doctor.get("specialization") or "")
        self.rate_input.setValue(float(to_decimal(doctor.get("commission_rate", "0"))))

    def _save(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "\u062e\u0637\u0623", "\u064a\u0631\u062c\u0649 \u0625\u062f\u062e\u0627\u0644 \u0627\u0633\u0645 \u0627\u0644\u0637\u0628\u064a\u0628")
            return
        data = {
            "name": name,
            "phone": self.phone_input.text().strip() or None,
            "specialization": self.spec_input.text().strip() or None,
            "commission_rate": from_decimal(to_decimal(self.rate_input.value())),
        }
        try:
            if self.doctor:
                self.doc_ctrl.update(self.doctor["id"], data)
            else:
                self.doc_ctrl.create(data)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "\u062e\u0637\u0623", str(e))


# ═══════════════════════════════════════════════════════════
# RuleDialog — with deal_type support
# ═══════════════════════════════════════════════════════════
class RuleDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.doc_ctrl = DoctorController()
        self.product_ctrl = ProductController()
        self.setWindowTitle("\u0625\u0636\u0627\u0641\u0629 \u0642\u0627\u0639\u062f\u0629 \u062f\u064a\u0644 / \u062a\u062e\u0641\u064a\u0636")
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.CustomizeWindowHint)
        self.setStyleSheet(_DIALOG_SS)
        self._setup_ui()
        self.layout().setSizeConstraint(QLayout.SetFixedSize)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 20, 24, 20)

        title = QLabel("\u0625\u0636\u0627\u0641\u0629 \u0642\u0627\u0639\u062f\u0629 \u062f\u064a\u0644 / \u062a\u062e\u0641\u064a\u0636")
        title.setStyleSheet(f"font-size:24px;font-weight:800;color:{_TEXT};background:transparent")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(16)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        doctors = self.doc_ctrl.get_all()
        self.doctor_combo = QComboBox()
        self.doctor_combo.addItem("-- \u0627\u062e\u062a\u0631 \u0627\u0644\u0637\u0628\u064a\u0628 --", None)
        for d in doctors:
            self.doctor_combo.addItem(d["name"], d["id"])
        self.doctor_combo.setFixedHeight(56)
        form.addRow("\U0001f468\u200d\u2695\ufe0f \u0627\u0644\u0637\u0628\u064a\u0628:", self.doctor_combo)

        self.deal_type_combo = QComboBox()
        self.deal_type_combo.addItem("\U0001f3f7 \u062f\u064a\u0644 (\u0631\u0641\u0639 \u0633\u0639\u0631 + \u062d\u0635\u0629 \u0637\u0628\u064a\u0628)", "deal")
        self.deal_type_combo.addItem("\U0001f4c9 \u062a\u062e\u0641\u064a\u0636 (\u062e\u0641\u0636 \u0633\u0639\u0631 \u0644\u0644\u0645\u0631\u064a\u0636)", "discount")
        self.deal_type_combo.setFixedHeight(56)
        form.addRow("\U0001f4cb \u0646\u0648\u0639 \u0627\u0644\u0639\u0645\u0644\u064a\u0629:", self.deal_type_combo)

        self.scope_combo = QComboBox()
        self.scope_combo.addItem("\u0645\u0646\u062a\u062c \u0645\u062d\u062f\u062f", "product")
        self.scope_combo.addItem("\u062a\u0635\u0646\u064a\u0641 \u0645\u062d\u062f\u062f", "category")
        self.scope_combo.addItem("\u062c\u0645\u064a\u0639 \u0627\u0644\u0645\u0646\u062a\u062c\u0627\u062a", "all")
        self.scope_combo.currentIndexChanged.connect(self._on_scope_changed)
        self.scope_combo.setFixedHeight(56)
        form.addRow("\U0001f4cd \u0627\u0644\u0646\u0637\u0627\u0642:", self.scope_combo)

        self.product_combo = QComboBox()
        products = self.product_ctrl.get_all()
        self.product_combo.addItem("-- \u0627\u062e\u062a\u0631 \u0627\u0644\u0645\u0646\u062a\u062c --", None)
        for p in products:
            self.product_combo.addItem(f"{p['name']} ({p['barcode']})", p["id"])
        self.product_combo.setFixedHeight(56)
        form.addRow("\U0001f48a \u0627\u0644\u0645\u0646\u062a\u062c:", self.product_combo)

        from database.connection import DatabaseManager
        db = DatabaseManager()
        categories = db.fetchall("SELECT id, name FROM categories ORDER BY name")
        self.category_combo = QComboBox()
        self.category_combo.addItem("-- \u0627\u062e\u062a\u0631 \u0627\u0644\u062a\u0635\u0646\u064a\u0641 --", None)
        for c in categories:
            self.category_combo.addItem(c["name"], c["id"])
        self.category_combo.setVisible(False)
        self.category_combo.setFixedHeight(56)
        form.addRow("\U0001f4c2 \u0627\u0644\u062a\u0635\u0646\u064a\u0641:", self.category_combo)

        self.type_combo = QComboBox()
        self.type_combo.addItem("\u0645\u0628\u0644\u063a \u0645\u0642\u0637\u0648\u0639", "fixed")
        self.type_combo.addItem("\u0646\u0633\u0628\u0629 \u0645\u0626\u0648\u064a\u0629", "percentage")
        self.type_combo.setFixedHeight(56)
        form.addRow("\U0001f3f7 \u0646\u0648\u0639 \u0627\u0644\u062d\u0635\u0629:", self.type_combo)

        self.value_input = QDoubleSpinBox()
        self.value_input.setRange(0, 9999999)
        self.value_input.setDecimals(0)
        self.value_input.setFixedHeight(56)
        form.addRow("\U0001f4b0 \u0627\u0644\u0642\u064a\u0645\u0629:", self.value_input)

        layout.addLayout(form)
        layout.addStretch()

        buttons = QHBoxLayout()
        buttons.setSpacing(12)
        save_btn = QPushButton("\U0001f4be  \u062d\u0641\u0638")
        save_btn.setStyleSheet(
            f"QPushButton{{font-size:19px;font-weight:700;background:{_GREEN};"
            f"color:white;border:none;border-radius:12px;padding:14px 32px}}"
            f"QPushButton:hover{{background:#047857}}"
        )
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.clicked.connect(self._save)

        cancel_btn = QPushButton("\u0625\u0644\u063a\u0627\u0621")
        cancel_btn.setStyleSheet(
            f"QPushButton{{font-size:19px;font-weight:600;background:{_BORDER};"
            f"color:{_MUTED};border:none;border-radius:12px;padding:14px 32px}}"
            f"QPushButton:hover{{background:#475569;color:{_TEXT}}}"
        )
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)

        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        buttons.addStretch()
        layout.addLayout(buttons)

    def _on_scope_changed(self, idx):
        scope = self.scope_combo.currentData()
        self.product_combo.setVisible(scope == "product")
        self.category_combo.setVisible(scope == "category")

    def _save(self):
        doctor_id = self.doctor_combo.currentData()
        if not doctor_id:
            QMessageBox.warning(self, "\u062e\u0637\u0623", "\u064a\u0631\u062c\u0649 \u0627\u062e\u062a\u064a\u0627\u0631 \u0637\u0628\u064a\u0628")
            return

        scope = self.scope_combo.currentData()
        reward_type = self.type_combo.currentData()
        deal_type = self.deal_type_combo.currentData()
        value = self.value_input.value()

        data = {
            "doctor_id": doctor_id,
            "reward_type": reward_type,
            "reward_value": value,
            "deal_type": deal_type,
        }

        if scope == "product":
            data["product_id"] = self.product_combo.currentData()
            if not data["product_id"]:
                QMessageBox.warning(self, "\u062e\u0637\u0623", "\u064a\u0631\u062c\u0649 \u0627\u062e\u062a\u064a\u0627\u0631 \u0645\u0646\u062a\u062c")
                return
        elif scope == "category":
            data["category_id"] = self.category_combo.currentData()
            if not data["category_id"]:
                QMessageBox.warning(self, "\u062e\u0637\u0623", "\u064a\u0631\u062c\u0649 \u0627\u062e\u062a\u064a\u0627\u0631 \u062a\u0635\u0646\u064a\u0641")
                return

        try:
            self.doc_ctrl.add_rule(data)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "\u062e\u0637\u0623", str(e))
