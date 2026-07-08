from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QFormLayout, QDoubleSpinBox, QMessageBox,
    QAbstractItemView, QFrame, QTabWidget, QScrollArea,
    QSizePolicy,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QFont, QPainter, QLinearGradient, QBrush
from PyQt5.QtWidgets import QShortcut
from PyQt5.QtGui import QKeySequence
from utils.modern_msgbox import ModernMessageBox as QMessageBox

from controllers.debt_controller import DebtController
from controllers.customer_controller import CustomerController
from controllers.supplier_debt_controller import SupplierDebtController
from controllers.supplier_controller import SupplierController
from database.connection import DatabaseManager
from utils.decimal_handler import to_decimal, from_decimal, format_currency, DECIMAL_ZERO
from utils.logger import safe_operation
from views.bulk_purchase_dialog import BulkPurchaseDialog


# ── style constants ──
_BG    = "#0f172a"
_CARD  = "#1e293b"
_BORD  = "#334155"
_GREEN = "#10b981"
_BLUE  = "#38bdf8"
_RED   = "#f87171"
_TEAL = "#0d9488"
_TEXT  = "#f1f5f9"
_MUTED = "#94a3b8"


def _lbl(text, color=_TEXT, size=13, bold=False):
    l = QLabel(text)
    l.setStyleSheet(
        f"font-size:{size}px;font-weight:{'700' if bold else '400'};"
        f"color:{color};background:transparent"
    )
    return l


def _btn(text, bg=_GREEN, color="white", fs=14, h=40):
    b = QPushButton(text)
    b.setFixedHeight(h)
    b.setCursor(Qt.PointingHandCursor)
    b.setStyleSheet(
        f"QPushButton{{font-size:{fs}px;font-weight:700;"
        f"background:{bg};color:{color};border:none;border-radius:10px;padding:0 16px}}"
        f"QPushButton:hover{{background:{bg}dd}}"
        f"QPushButton:pressed{{background:{bg}99}}"
    )
    return b


def _table_style():
    return (
        f"QTableWidget{{background:{_CARD};border:1px solid {_BORD};"
        f"border-radius:10px;color:{_TEXT};outline:none}}"
        f"QHeaderView::section{{background:{_BG};color:{_MUTED};"
        f"padding:10px 8px;border:none;border-bottom:1px solid {_BORD};"
        f"font-size:13px;font-weight:700}}"
        f"QTableWidget::item{{padding:10px 8px;"
        f"border-bottom:1px solid {_BG}50;font-size:14px}}"
        f"QTableWidget::item:selected{{background:{_BLUE}20}}"
    )


# ══════════════════════════════════════════════════════════════
class DebtsWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.debt_ctrl          = DebtController()
        self.customer_ctrl      = CustomerController()
        self.supplier_debt_ctrl = SupplierDebtController()
        self.db                 = DatabaseManager()
        self._setup_ui()
        self._load_debts()

    # ─── background ──────────────────────────────────────────
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        g = QLinearGradient(0, 0, 0, self.height())
        g.setColorAt(0, QColor(15, 23, 42))
        g.setColorAt(1, QColor(10, 15, 30))
        p.fillRect(self.rect(), QBrush(g))
        p.end()

    # ─── UI ─────────────────────────────────────────────────
    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # ── top summary cards ──
        cards_row = QHBoxLayout()
        cards_row.setSpacing(10)

        self._cust_debt_card, self._cust_debt_val = self._stat_card(
            "👤", "ديون العملاء", "0", _RED, "#7f1d1d30")
        self._supp_debt_card, self._supp_debt_val = self._stat_card(
            "🏪", "ديون المذاخر", "0", _TEAL, "#134e4a30")
        self._total_card, self._total_val = self._stat_card(
            "💰", "إجمالي الديون", "0", _BLUE, "#0c4a6e30")

        cards_row.addWidget(self._cust_debt_card)
        cards_row.addWidget(self._supp_debt_card)
        cards_row.addWidget(self._total_card)
        root.addLayout(cards_row)

        # ── tabs ──
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(
            f"QTabWidget::pane{{background:{_CARD};border:1px solid {_BORD};"
            f"border-radius:10px;margin-top:-1px}}"
            f"QTabBar::tab{{background:{_BG};color:{_MUTED};padding:10px 24px;"
            f"font-size:14px;font-weight:600;border:1px solid {_BORD};"
            f"border-bottom:none;border-radius:8px 8px 0 0;margin-left:4px}}"
            f"QTabBar::tab:selected{{background:{_CARD};color:{_BLUE};"
            f"border-bottom:2px solid {_BLUE}}}"
            f"QTabBar::tab:hover{{color:{_TEXT}}}"
        )

        # tab 1: customer debts
        self.cust_tab = self._build_customer_tab()
        self.tabs.addTab(self.cust_tab, "👤  ديون العملاء")

        # tab 2: supplier debts
        self.supp_tab = self._build_supplier_tab()
        self.tabs.addTab(self.supp_tab, "🏪  ديون المذاخر")

        root.addWidget(self.tabs, 1)

        QShortcut(QKeySequence("F1"), self, self._show_customer_payment)

    # ─── customer tab ────────────────────────────────────────
    def _build_customer_tab(self):
        w = QWidget()
        w.setStyleSheet(f"background:{_CARD}")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(8)

        # toolbar
        tb = QHBoxLayout()
        self.cust_search = QLineEdit()
        self.cust_search.setPlaceholderText("🔍  ابحث عن عميل...")
        self.cust_search.setFixedHeight(38)
        self.cust_search.setStyleSheet(
            f"QLineEdit{{font-size:13px;padding:0 12px;"
            f"background:{_BG};border:1.5px solid {_BORD};"
            f"border-radius:8px;color:{_TEXT}}}"
            f"QLineEdit:focus{{border-color:{_BLUE}}}"
        )
        self.cust_search.textChanged.connect(self._on_cust_search)
        tb.addWidget(self.cust_search)
        tb.addStretch()

        pay_btn = _btn("💵  تسديد دفعة (F1)", _GREEN, "white", 13, 38)
        pay_btn.clicked.connect(self._show_customer_payment)
        hist_btn = _btn("📋  سجل الدفعات", "#6366f1", "white", 13, 38)
        hist_btn.clicked.connect(self._show_customer_history)
        tb.addWidget(pay_btn)
        tb.addWidget(hist_btn)
        lay.addLayout(tb)

        self.cust_table = QTableWidget()
        self.cust_table.setColumnCount(6)
        self.cust_table.setHorizontalHeaderLabels([
            "العميل", "الهاتف", "إجمالي الدين",
            "المدفوع", "المتبقي", "الحالة"
        ])
        self.cust_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.cust_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.cust_table.verticalHeader().setVisible(False)
        self.cust_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.cust_table.setShowGrid(False)
        self.cust_table.setStyleSheet(_table_style())
        self.cust_table.doubleClicked.connect(self._show_customer_payment)
        lay.addWidget(self.cust_table, 1)
        return w

    # ─── supplier tab ────────────────────────────────────────
    def _build_supplier_tab(self):
        w = QWidget()
        w.setStyleSheet(f"background:{_CARD}")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(8)

        # toolbar
        tb = QHBoxLayout()
        self.supp_search = QLineEdit()
        self.supp_search.setPlaceholderText("🔍  ابحث عن مذخر أو رقم فاتورة...")
        self.supp_search.setFixedHeight(38)
        self.supp_search.setStyleSheet(
            f"QLineEdit{{font-size:13px;padding:0 12px;"
            f"background:{_BG};border:1.5px solid {_BORD};"
            f"border-radius:8px;color:{_TEXT}}}"
            f"QLineEdit:focus{{border-color:{_BLUE}}}"
        )
        self.supp_search.textChanged.connect(self._on_supp_search)
        tb.addWidget(self.supp_search)
        tb.addStretch()

        new_inv_btn = _btn("➕  فاتورة مجمعة جديدة", "#6366f1", "white", 13, 38)
        new_inv_btn.clicked.connect(self._show_bulk_purchase)
        pay_btn = _btn("💵  تسديد للمذخر", _TEAL, "#0f172a", 13, 38)
        pay_btn.clicked.connect(self._show_supplier_payment)
        hist_btn = _btn("📋  سجل الدفعات", "#334155", _MUTED, 13, 38)
        hist_btn.clicked.connect(self._show_supplier_history)
        tb.addWidget(new_inv_btn)
        tb.addWidget(pay_btn)
        tb.addWidget(hist_btn)
        lay.addLayout(tb)

        self.supp_table = QTableWidget()
        self.supp_table.setColumnCount(8)
        self.supp_table.setHorizontalHeaderLabels([
            "المذخر", "رقم الفاتورة", "عدد الأصناف",
            "إجمالي الفاتورة", "المسدد", "المتبقي",
            "الحالة", "التاريخ"
        ])
        self.supp_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.supp_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.supp_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.supp_table.verticalHeader().setVisible(False)
        self.supp_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.supp_table.setShowGrid(False)
        self.supp_table.setStyleSheet(_table_style())
        self.supp_table.doubleClicked.connect(self._show_supplier_payment)
        lay.addWidget(self.supp_table, 1)
        return w

    # ─── stat card helper ────────────────────────────────────
    def _stat_card(self, icon, title, value, accent, bg_icon):
        card = QFrame()
        card.setStyleSheet(
            f"QFrame{{background:{_CARD};border:1px solid {_BORD};"
            f"border-radius:12px}}"
        )
        card.setFixedHeight(90)
        h = QHBoxLayout(card)
        h.setContentsMargins(14, 10, 14, 10)
        h.setSpacing(14)

        icon_lbl = QLabel(icon)
        icon_lbl.setFixedSize(50, 50)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet(
            f"font-size:24px;background:{bg_icon};"
            f"border-radius:10px;color:{accent}"
        )
        h.addWidget(icon_lbl)

        v = QVBoxLayout()
        v.setSpacing(2)
        v.addWidget(_lbl(title, _MUTED, 12, True))
        val_lbl = _lbl(value, accent, 22, True)
        v.addWidget(val_lbl)
        h.addLayout(v)
        h.addStretch()
        return card, val_lbl

    # ─── load all ────────────────────────────────────────────
    def _load_debts(self):
        self._load_customer_debts()
        self._load_supplier_debts()
        self._update_summary()

    def _update_summary(self):
        cust_total  = self.debt_ctrl.get_total_pending()
        supp_total  = self.supplier_debt_ctrl.get_total_pending()
        grand_total = cust_total + supp_total
        self._cust_debt_val.setText(format_currency(cust_total))
        self._supp_debt_val.setText(format_currency(supp_total))
        self._total_val.setText(format_currency(grand_total))

    # ─── customer debts ──────────────────────────────────────
    def _load_customer_debts(self, debts=None):
        if debts is None:
            debts = self.debt_ctrl.get_all_pending()
        self._populate_cust_table(debts)

    def _on_cust_search(self, text):
        if len(text) >= 2:
            customers = self.customer_ctrl.search(text)
            cids = [c["id"] for c in customers]
            if cids:
                ph = ",".join("?" for _ in cids)
                debts = self.db.fetchall(
                    f"""SELECT d.*, c.name as customer_name, c.phone as customer_phone
                        FROM debts d JOIN customers c ON d.customer_id = c.id
                        WHERE d.customer_id IN ({ph})
                        AND d.status IN ('pending','partial')
                        ORDER BY d.created_at DESC""",
                    tuple(cids),
                )
                self._populate_cust_table(debts)
            else:
                self._populate_cust_table([])
        elif not text:
            self._load_customer_debts()

    def _populate_cust_table(self, debts):
        t = self.cust_table
        t.setRowCount(len(debts))
        for i, d in enumerate(debts):
            t.setItem(i, 0, QTableWidgetItem(d["customer_name"]))
            t.setItem(i, 1, QTableWidgetItem(dict(d).get("customer_phone") or ""))
            t.setItem(i, 2, QTableWidgetItem(format_currency(d["amount"])))
            t.setItem(i, 3, QTableWidgetItem(format_currency(d["paid_amount"])))

            remain_item = QTableWidgetItem(format_currency(d["remaining_amount"]))
            remain_item.setForeground(QColor(_RED))
            remain_item.setFont(QFont("Segoe UI", 13, QFont.Bold))
            t.setItem(i, 4, remain_item)

            status_map = {"pending": "⏳ معلق", "partial": "💛 جزئي", "paid": "✅ مسدد"}
            st = status_map.get(d["status"], d["status"])
            st_item = QTableWidgetItem(st)
            if d["status"] == "pending":
                st_item.setForeground(QColor(_RED))
            elif d["status"] == "partial":
                st_item.setForeground(QColor(_TEAL))
            else:
                st_item.setForeground(QColor(_GREEN))
            t.setItem(i, 5, st_item)
            t.setRowHeight(i, 50)

            # store debt id
            t.item(i, 0).setData(Qt.UserRole, d["id"])

    # ─── supplier debts ──────────────────────────────────────
    def _load_supplier_debts(self, debts=None):
        if debts is None:
            debts = self.supplier_debt_ctrl.get_all_pending()
        self._populate_supp_table(debts)

    def _on_supp_search(self, text):
        if len(text) >= 2:
            debts = self.supplier_debt_ctrl.search(text)
            self._populate_supp_table(debts)
        elif not text:
            self._load_supplier_debts()

    def _populate_supp_table(self, debts):
        t = self.supp_table
        t.setRowCount(len(debts))
        for i, d in enumerate(debts):
            t.setItem(i, 0, QTableWidgetItem(dict(d).get("supplier_name") or ""))

            inv_item = QTableWidgetItem(dict(d).get("invoice_number") or "—")
            inv_item.setForeground(QColor(_MUTED))
            t.setItem(i, 1, inv_item)

            # عدد الأصناف
            items = self.supplier_debt_ctrl.get_items(d["id"])
            cnt_item = QTableWidgetItem(str(len(items)))
            cnt_item.setTextAlignment(Qt.AlignCenter)
            cnt_item.setForeground(QColor(_BLUE))
            cnt_item.setFont(QFont("Segoe UI", 13, QFont.Bold))
            t.setItem(i, 2, cnt_item)

            t.setItem(i, 3, QTableWidgetItem(format_currency(d["total_amount"])))
            t.setItem(i, 4, QTableWidgetItem(format_currency(d["paid_amount"])))

            remain_item = QTableWidgetItem(format_currency(d["remaining_amount"]))
            remain_item.setForeground(QColor(
                _GREEN if float(d["remaining_amount"]) <= 0 else _RED
            ))
            remain_item.setFont(QFont("Segoe UI", 13, QFont.Bold))
            t.setItem(i, 5, remain_item)

            status_map = {"pending": "⏳ معلق", "partial": "💛 جزئي", "paid": "✅ مسدد"}
            st = status_map.get(d["status"], d["status"])
            st_item = QTableWidgetItem(st)
            if d["status"] == "pending":
                st_item.setForeground(QColor(_RED))
            elif d["status"] == "partial":
                st_item.setForeground(QColor(_TEAL))
            else:
                st_item.setForeground(QColor(_GREEN))
            t.setItem(i, 6, st_item)

            date_str = str(dict(d).get("created_at") or "")[:10]
            t.setItem(i, 7, QTableWidgetItem(date_str))

            t.setRowHeight(i, 50)
            t.item(i, 0).setData(Qt.UserRole, d["id"])

    # ─── actions: customer ────────────────────────────────────
    def _show_customer_payment(self):
        row = self.cust_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "تنبيه", "يرجى تحديد دين من القائمة")
            return
        debt_id  = self.cust_table.item(row, 0).data(Qt.UserRole)
        cust_name = self.cust_table.item(row, 0).text()
        remaining = float(self.cust_table.item(row, 4).text().replace(",", ""))
        dlg = CustomerPaymentDialog(debt_id, cust_name, remaining, self)
        if dlg.exec_() == QDialog.Accepted:
            self._load_debts()

    def _show_customer_history(self):
        row = self.cust_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "تنبيه", "يرجى تحديد دين أولاً")
            return
        debt_id = self.cust_table.item(row, 0).data(Qt.UserRole)
        dlg = HistoryDialog(
            debt_id, self.debt_ctrl.get_payments, "سجل دفعات العميل", self
        )
        dlg.exec_()

    # ─── actions: supplier ────────────────────────────────────
    def _show_bulk_purchase(self):
        dlg = BulkPurchaseDialog(self)
        dlg.invoice_saved.connect(self._load_debts)
        dlg.exec_()

    def _show_supplier_payment(self):
        row = self.supp_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "تنبيه", "يرجى تحديد فاتورة من القائمة")
            return
        debt_id   = self.supp_table.item(row, 0).data(Qt.UserRole)
        supp_name = self.supp_table.item(row, 0).text()
        remaining = float(self.supp_table.item(row, 5).text().replace(",", ""))
        if remaining <= 0:
            QMessageBox.information(self, "مسددة", "هذه الفاتورة مسددة بالكامل")
            return
        dlg = SupplierPaymentDialog(debt_id, supp_name, remaining,
                                    self.supplier_debt_ctrl, self)
        if dlg.exec_() == QDialog.Accepted:
            self._load_debts()

    def _show_supplier_history(self):
        row = self.supp_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "تنبيه", "يرجى تحديد فاتورة أولاً")
            return
        debt_id = self.supp_table.item(row, 0).data(Qt.UserRole)
        dlg = HistoryDialog(
            debt_id, self.supplier_debt_ctrl.get_payments,
            "سجل دفعات المذخر", self
        )
        dlg.exec_()


# ══════════════════════════════════════════════════════════════
class CustomerPaymentDialog(QDialog):
    def __init__(self, debt_id, customer_name, remaining, parent=None):
        super().__init__(parent)
        self.debt_id   = debt_id
        self.debt_ctrl = DebtController()
        self.setWindowTitle(f"تسديد دفعة - {customer_name}")
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.CustomizeWindowHint)
        self.setMinimumWidth(380)
        self.setStyleSheet(
            f"QDialog{{background:{_CARD};color:{_TEXT}}}"
            f"QLabel{{background:transparent}}"
        )
        self._setup_ui(remaining)

    def _setup_ui(self, remaining):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)

        lay.addWidget(_lbl("💵  تسديد دفعة", _BLUE, 18, True))

        remain_lbl = _lbl(f"المبلغ المتبقي:  {remaining:,.2f}", _RED, 16, True)
        lay.addWidget(remain_lbl)

        form = QFormLayout()
        form.setSpacing(10)

        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(1, remaining)
        self.amount_spin.setDecimals(0)
        self.amount_spin.setValue(remaining)
        self.amount_spin.setButtonSymbols(QDoubleSpinBox.NoButtons)
        self.amount_spin.setFixedHeight(40)
        self.amount_spin.setStyleSheet(
            f"QDoubleSpinBox{{font-size:15px;font-weight:700;padding:6px 10px;"
            f"background:{_BG};border:1.5px solid {_BORD};border-radius:8px;color:{_GREEN}}}"
            f"QDoubleSpinBox:focus{{border-color:{_BLUE}}}"
        )
        form.addRow(_lbl("المبلغ:"), self.amount_spin);

        self.notes_inp = QLineEdit()
        self.notes_inp.setPlaceholderText("ملاحظات (اختياري)")
        self.notes_inp.setFixedHeight(38)
        self.notes_inp.setStyleSheet(
            f"QLineEdit{{font-size:13px;padding:4px 10px;"
            f"background:{_BG};border:1.5px solid {_BORD};border-radius:8px;color:{_TEXT}}}"
        )
        form.addRow(_lbl("ملاحظات:"), self.notes_inp)
        lay.addLayout(form)

        btn_row = QHBoxLayout()
        save_btn   = _btn("✅  تسديد", _GREEN, "white", 14, 42)
        cancel_btn = _btn("إلغاء", "#334155", _MUTED, 13, 42)
        save_btn.clicked.connect(self._save)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(cancel_btn)
        lay.addLayout(btn_row)

    @safe_operation("عذراً، حدث خطأ أثناء تسجيل الدفعة.")
    def _save(self):
        amount = self.amount_spin.value()
        notes  = self.notes_inp.text().strip()
        self.debt_ctrl.add_payment(self.debt_id, from_decimal(to_decimal(amount)), notes)
        QMessageBox.information(self, "تم", "تم تسجيل الدفعة بنجاح ✅")
        self.accept()


# ══════════════════════════════════════════════════════════════
class SupplierPaymentDialog(QDialog):
    def __init__(self, debt_id, supplier_name, remaining, ctrl, parent=None):
        super().__init__(parent)
        self.debt_id = debt_id
        self.ctrl    = ctrl
        self.setWindowTitle(f"تسديد للمذخر - {supplier_name}")
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.CustomizeWindowHint)
        self.setMinimumWidth(380)
        self.setStyleSheet(
            f"QDialog{{background:{_CARD};color:{_TEXT}}}"
            f"QLabel{{background:transparent}}"
        )
        self._setup_ui(remaining)

    def _setup_ui(self, remaining):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)

        lay.addWidget(_lbl("🏪  تسديد للمذخر", _TEAL, 18, True))
        lay.addWidget(_lbl(f"المبلغ المتبقي:  {remaining:,.0f}", _RED, 16, True))

        form = QFormLayout()
        form.setSpacing(10)

        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(1, remaining)
        self.amount_spin.setDecimals(0)
        self.amount_spin.setValue(remaining)
        self.amount_spin.setButtonSymbols(QDoubleSpinBox.NoButtons)
        self.amount_spin.setFixedHeight(40)
        self.amount_spin.setStyleSheet(
            f"QDoubleSpinBox{{font-size:15px;font-weight:700;padding:6px 10px;"
            f"background:{_BG};border:1.5px solid {_BORD};border-radius:8px;color:{_TEAL}}}"
        )
        form.addRow(_lbl("المبلغ:"), self.amount_spin);

        self.notes_inp = QLineEdit()
        self.notes_inp.setPlaceholderText("ملاحظات")
        self.notes_inp.setFixedHeight(38)
        self.notes_inp.setStyleSheet(
            f"QLineEdit{{font-size:13px;padding:4px 10px;"
            f"background:{_BG};border:1.5px solid {_BORD};border-radius:8px;color:{_TEXT}}}"
        )
        form.addRow(_lbl("ملاحظات:"), self.notes_inp)
        lay.addLayout(form)

        btn_row = QHBoxLayout()
        save_btn   = _btn("✅  تسديد", _TEAL, "#0f172a", 14, 42)
        cancel_btn = _btn("إلغاء", "#334155", _MUTED, 13, 42)
        save_btn.clicked.connect(self._save)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(cancel_btn)
        lay.addLayout(btn_row)

    def _save(self):
        try:
            self.ctrl.add_payment(
                self.debt_id,
                self.amount_spin.value(),
                self.notes_inp.text().strip()
            )
            QMessageBox.information(self, "تم", "تم تسجيل الدفعة بنجاح ✅")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", str(e))


# ══════════════════════════════════════════════════════════════
class HistoryDialog(QDialog):
    def __init__(self, debt_id, get_payments_fn, title, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.CustomizeWindowHint)
        self.setMinimumSize(500, 340)
        self.setStyleSheet(
            f"QDialog{{background:{_CARD};color:{_TEXT}}}"
        )
        self._setup_ui(debt_id, get_payments_fn)

    def _setup_ui(self, debt_id, get_payments_fn):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)

        lay.addWidget(_lbl("📋  سجل الدفعات", _BLUE, 16, True))

        payments = get_payments_fn(debt_id)

        t = QTableWidget()
        t.setColumnCount(3)
        t.setHorizontalHeaderLabels(["المبلغ", "التاريخ", "ملاحظات"])
        t.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        t.verticalHeader().setVisible(False)
        t.setShowGrid(False)
        t.setStyleSheet(_table_style())
        t.setRowCount(len(payments))

        for i, p in enumerate(payments):
            amt_item = QTableWidgetItem(format_currency(p["amount"]))
            amt_item.setForeground(QColor(_GREEN))
            amt_item.setFont(QFont("Segoe UI", 13, QFont.Bold))
            t.setItem(i, 0, amt_item)
            t.setItem(i, 1, QTableWidgetItem(str(dict(p).get("payment_date", ""))[:16]))
            t.setItem(i, 2, QTableWidgetItem(dict(p).get("notes") or ""))
            t.setRowHeight(i, 44)

        lay.addWidget(t, 1)

        close_btn = _btn("إغلاق", "#334155", _MUTED, 13, 38)
        close_btn.clicked.connect(self.accept)
        lay.addWidget(close_btn)
