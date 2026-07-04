"""
BulkPurchaseDialog - فاتورة مجمعة (v8)
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QDoubleSpinBox, QSpinBox, QComboBox,
    QDateEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QMessageBox, QApplication, QWidget, QCompleter,
)
from PyQt5.QtCore import Qt, QDate, pyqtSignal, QStringListModel, QLocale
from PyQt5.QtGui import QFont, QColor
from utils.modern_msgbox import ModernMessageBox as QMessageBox
from controllers.supplier_debt_controller import SupplierDebtController
from controllers.supplier_controller import SupplierController
from database.connection import DatabaseManager
from decimal import Decimal
from utils.decimal_handler import to_decimal, format_currency, DECIMAL_ZERO

_INP_SS = (
    "QLineEdit,QSpinBox,QDoubleSpinBox,QDateEdit,QComboBox{"
    "background:#0b1120;border:none;border-bottom:2px solid #2a3f5f;"
    "border-radius:8px;padding:8px 12px;"
    "color:#f1f5f9;font-size:18px;font-weight:700}"
    "QLineEdit:focus,QSpinBox:focus,QDoubleSpinBox:focus,QComboBox:focus{"
    "border-bottom:2px solid #4a8fe7}"
)

_INP_NUM_SS = (
    "QDoubleSpinBox,QSpinBox{"
    "background:#0b1120;border:none;border-bottom:2px solid #2a3f5f;"
    "border-radius:8px;padding:8px 12px;"
    "color:#7ba3ff;font-size:18px;font-weight:800}"
    "QDoubleSpinBox:focus,QSpinBox:focus{"
    "border-bottom:2px solid #4a8fe7}"
)

locale_iqd = QLocale(QLocale.English, QLocale.UnitedStates)

def _fl(text):
    l = QLabel(text)
    l.setStyleSheet("font-size:14px;font-weight:700;color:#c8d6e5;background:transparent")
    return l

def _make_combo(items, h=50):
    cb = QComboBox()
    cb.setFixedHeight(h)
    cb.setEditable(True)
    cb.setInsertPolicy(QComboBox.NoInsert)
    cb.setStyleSheet(_INP_SS)
    for t, d in items:
        cb.addItem(t, d)
    texts = [t for t, _ in items]
    model = QStringListModel(texts, cb)
    comp = QCompleter(model, cb)
    comp.setCaseSensitivity(Qt.CaseInsensitive)
    comp.setCompletionMode(QCompleter.PopupCompletion)
    cb.setCompleter(comp)
    return cb


# ══════════════════════════════════════════════════════════════
class BulkItemDialog(QDialog):
    """نافذة إدخال صنف واحد — تصميم يمين/يسار + تسعير كامل"""

    def __init__(self, parent=None, index=0, total=1, categories=None, suppliers=None):
        super().__init__(parent)
        self._index = index
        self._total = total
        self._categories = categories or []
        self._suppliers = suppliers or []
        self._item_data = None
        self._updating = False
        self.setWindowTitle(f"الصنف {index + 1} من {total}")
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.CustomizeWindowHint)
        self.setStyleSheet(
            "QDialog{background:#1e293b;color:#f1f5f9}"
            "QLabel{color:#cbd5e1;font-size:14px;background:transparent}"
        )
        self.setMinimumSize(960, 600)
        self._build_ui()

    def showEvent(self, event):
        super().showEvent(event)
        self.showMaximized()

    def _build_ui(self):
        main = QVBoxLayout(self)
        main.setSpacing(10)
        main.setContentsMargins(16, 12, 16, 12)

        title_lbl = QLabel(f"📦  الصنف {self._index + 1} من {self._total}")
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

        def _fl2(text):
            l = QLabel(text)
            l.setStyleSheet("font-size:14px;font-weight:600;color:#8899bb;background:transparent")
            return l

        body = QHBoxLayout()
        body.setSpacing(14)

        # ═══ LEFT ═══
        lc = QVBoxLayout()
        lc.setSpacing(10)

        def _setup_basic(cl):
            cl.addWidget(_fl2("🔳  الباركود"))
            bc_row = QHBoxLayout()
            bc_row.setSpacing(6)
            self.barcode_inp = QLineEdit()
            self.barcode_inp.setPlaceholderText("امسح الباركود أو اكتبه…")
            self.barcode_inp.setFixedHeight(54)
            self.barcode_inp.setStyleSheet(
                "QLineEdit{background:transparent;border:none;border-bottom:2px solid #2a3f5f;"
                "color:#f1f5f9;font-size:20px;font-weight:700;padding:8px 4px;font-family:monospace}"
                "QLineEdit:focus{border-bottom:2px solid #4a8fe7}"
            )
            bc_row.addWidget(self.barcode_inp, 1)

            self.print_btn = QPushButton("🖨️")
            self.print_btn.setToolTip("طباعة باركود")
            self.print_btn.setFixedSize(54, 54)
            self.print_btn.setStyleSheet(
                "QPushButton{background:#2a3f5f;color:#7ba3ff;border:none;"
                "border-radius:10px;font-size:20px}"
                "QPushButton:hover{background:#3a5580}"
            )
            bc_row.addWidget(self.print_btn)
            cl.addLayout(bc_row)

            cl.addWidget(_fl2("💊  اسم المادة"))
            self.name_inp = QLineEdit()
            self.name_inp.setPlaceholderText("اسم المادة / المحلول")
            self.name_inp.setFixedHeight(54)
            self.name_inp.setStyleSheet(
                "QLineEdit{background:transparent;border:none;border-bottom:2px solid #2a3f5f;"
                "color:#f1f5f9;font-size:20px;font-weight:700;padding:8px 4px}"
                "QLineEdit:focus{border-bottom:2px solid #4a8fe7}"
            )
            cl.addWidget(self.name_inp)

            cl.addWidget(_fl2("⚖️  وحدة القياس"))
            self.sci_inp = QLineEdit()
            self.sci_inp.setPlaceholderText("مهلي، جرام، أمبولة، …")
            self.sci_inp.setFixedHeight(54)
            self.sci_inp.setStyleSheet(
                "QLineEdit{background:transparent;border:none;border-bottom:2px solid #2a3f5f;"
                "color:#94a3b8;font-size:18px;font-weight:600;padding:8px 4px}"
                "QLineEdit:focus{border-bottom:2px solid #4a8fe7}"
            )
            cl.addWidget(self.sci_inp)

            cl.addWidget(_fl2("📂  القسم"))
            cat_items = [("-- اختر القسم --", None)] + [(c["name"], c["id"]) for c in self._categories]
            self.cat_combo = QComboBox()
            self.cat_combo.setEditable(True)
            self.cat_combo.setInsertPolicy(QComboBox.NoInsert)
            self.cat_combo.lineEdit().setPlaceholderText("اكتب للبحث…")
            self.cat_combo.setFixedHeight(54)
            self.cat_combo.setStyleSheet(
                "QComboBox{background:transparent;border:none;border-bottom:2px solid #2a3f5f;"
                "color:#f1f5f9;font-size:18px;font-weight:600;padding:8px 4px}"
                "QComboBox:focus{border-bottom:2px solid #4a8fe7}"
                "QComboBox::drop-down{border:none;width:28px}"
            )
            for t, d in cat_items:
                self.cat_combo.addItem(t, d)
            texts = [t for t, _ in cat_items]
            model = QStringListModel(texts, self.cat_combo)
            comp = QCompleter(model, self.cat_combo)
            comp.setCaseSensitivity(Qt.CaseInsensitive)
            comp.setFilterMode(Qt.MatchContains)
            comp.setCompletionMode(QCompleter.PopupCompletion)
            self.cat_combo.setCompleter(comp)
            cl.addWidget(self.cat_combo)

        lc.addWidget(_card("📋", "المعلومات الأساسية", _setup_basic))

        def _setup_inv(cl):
            cl.addWidget(_fl2("📦  الكمية"))
            self.qty_spin = QSpinBox()
            self.qty_spin.setRange(0, 999999)
            self.qty_spin.setValue(1)
            self.qty_spin.setFixedHeight(54)
            self.qty_spin.setLocale(locale_iqd)
            self.qty_spin.setGroupSeparatorShown(True)
            self.qty_spin.setStyleSheet(
                "QSpinBox{background:transparent;border:none;border-bottom:2px solid #2a3f5f;"
                "color:#7ba3ff;font-size:20px;font-weight:700;padding:8px 4px;min-width:140px}"
                "QSpinBox:focus{border-bottom:2px solid #4a8fe7}"
                "QSpinBox::up-button,QSpinBox::down-button{border:none;width:0px}"
            )
            cl.addWidget(self.qty_spin)

            cl.addWidget(_fl2("⚠️  حد التنبيه (أدنى)"))
            self.min_stock_spin = QSpinBox()
            self.min_stock_spin.setRange(0, 99999)
            self.min_stock_spin.setValue(10)
            self.min_stock_spin.setFixedHeight(54)
            self.min_stock_spin.setLocale(locale_iqd)
            self.min_stock_spin.setStyleSheet(
                "QSpinBox{background:transparent;border:none;border-bottom:2px solid #2a3f5f;"
                "color:#7ba3ff;font-size:20px;font-weight:700;padding:8px 4px;min-width:140px}"
                "QSpinBox:focus{border-bottom:2px solid #4a8fe7}"
                "QSpinBox::up-button,QSpinBox::down-button{border:none;width:0px}"
            )
            cl.addWidget(self.min_stock_spin)

            cl.addWidget(_fl2("📅  تاريخ انتهاء الصلاحية"))
            self.expiry_inp = QDateEdit()
            self.expiry_inp.setCalendarPopup(True)
            self.expiry_inp.setDate(QDate.currentDate())
            self.expiry_inp.setDisplayFormat("yyyy-MM-dd")
            self.expiry_inp.setFixedHeight(54)
            self.expiry_inp.setStyleSheet(
                "QDateEdit{background:transparent;border:none;border-bottom:2px solid #2a3f5f;"
                "color:#f4848f;font-size:20px;font-weight:700;padding:8px 4px}"
                "QDateEdit:focus{border-bottom:2px solid #4a8fe7}"
                "QCalendarWidget{background:#141d2e;color:#f1f5f9;border:none}"
                "QCalendarWidget QAbstractItemView{color:#f1f5f9;background:#141d2e;selection-background-color:#4a8fe7}"
            )
            cl.addWidget(self.expiry_inp)

        lc.addWidget(_card("📦", "المخزون", _setup_inv))
        lc.addStretch()

        # ═══ RIGHT ═══
        rc = QVBoxLayout()
        rc.setSpacing(10)

        def _setup_pricing(cl):
            cl.addWidget(_fl2("💵  سعر الشراء — للباكيت / العبوة"))
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

            cl.addWidget(_fl2("📦  الكمية في العبوة"))
            qty_row = QHBoxLayout()
            qty_row.setSpacing(8)
            self.qty_in_pack_spin = QSpinBox()
            self.qty_in_pack_spin.setRange(1, 99999)
            self.qty_in_pack_spin.setValue(6)
            self.qty_in_pack_spin.setFixedHeight(50)
            self.qty_in_pack_spin.setLocale(locale_iqd)
            self.qty_in_pack_spin.setGroupSeparatorShown(True)
            self.qty_in_pack_spin.setStyleSheet(
                "QSpinBox{background:#0b1120;border:none;border-radius:8px;"
                "color:#7ba3ff;font-size:22px;font-weight:800;padding:4px 14px;min-width:80px}"
                "QSpinBox:focus{background:#162035}"
            )
            self.qty_in_pack_spin.valueChanged.connect(self._update_auto_prices)
            qty_row.addWidget(self.qty_in_pack_spin)

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
                qb.clicked.connect(lambda checked, v=qval: self.qty_in_pack_spin.setValue(v))
                qty_row.addWidget(qb)
            qty_row.addStretch()
            cl.addLayout(qty_row)

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

            cl.addWidget(_fl2("📈  نسبة الربح % — يحتسب تلقائياً"))
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

            cl.addWidget(_fl2("💵  سعر البيع — للقطعة / الشريط"))
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

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        save_btn = QPushButton("💾  حفظ ومتابعة")
        save_btn.setFixedHeight(50)
        save_btn.setStyleSheet(
            "QPushButton{font-size:18px;font-weight:700;background:#059669;"
            "color:white;border:none;border-radius:10px;padding:0 36px}"
            "QPushButton:hover{background:#047857}"
        )
        save_btn.clicked.connect(self._save)
        skip_btn = QPushButton("تخطي")
        skip_btn.setFixedHeight(50)
        skip_btn.setStyleSheet(
            "QPushButton{font-size:18px;font-weight:600;background:#334155;"
            "color:#94a3b8;border:none;border-radius:10px;padding:0 36px}"
            "QPushButton:hover{background:#475569;color:#f1f5f9}"
        )
        skip_btn.clicked.connect(self.reject)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(skip_btn)
        btn_row.addStretch()
        main.addLayout(btn_row)

    def get_data(self) -> dict:
        return {
            "barcode": self.barcode_inp.text().strip(),
            "name": self.name_inp.text().strip(),
            "scientific_name": self.sci_inp.text().strip(),
            "category_id": self.cat_combo.currentData(),
            "quantity": self.qty_spin.value(),
            "unit_price": self.purchase_price_input.value(),
            "total_price": self.qty_spin.value() * self.purchase_price_input.value(),
            "expiry_date": self.expiry_inp.date().toString("yyyy-MM-dd"),
            "min_stock": self.min_stock_spin.value(),
            "strips_per_pack": self.qty_in_pack_spin.value(),
            "pieces_per_strip": 1,
            "sale_price": self.sale_price_input.value(),
        }

    def _save(self):
        name = self.name_inp.text().strip()
        if not name:
            QMessageBox.warning(None, "تنبيه", "يرجى إدخال اسم المادة")
            return
        self._item_data = self.get_data()
        self.accept()

    # ── auto-pricing ──
    def _update_auto_prices(self):
        if getattr(self, '_updating', False):
            return
        self._updating = True

        purchase = to_decimal(self.purchase_price_input.value())
        qty = self.qty_in_pack_spin.value() or 1
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
        qty = self.qty_in_pack_spin.value() or 1
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


# ══════════════════════════════════════════════════════════════
class BulkPurchaseDialog(QDialog):
    """نافذة الفاتورة المجمعة"""
    invoice_saved = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.debt_ctrl = SupplierDebtController()
        self.supplier_ctrl = SupplierController()
        self.db = DatabaseManager()
        self._items: list[dict] = []
        self._categories = self.db.fetchall("SELECT id, name FROM categories ORDER BY name")

        self.setWindowTitle("فاتورة مجمعة — استيراد من مذخر")
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.CustomizeWindowHint)
        self.setStyleSheet("QDialog{background:#0b1120}")
        self._build_ui()

    def showEvent(self, event):
        super().showEvent(event)
        self.showMaximized()

    def _build_ui(self):
        main = QVBoxLayout(self)
        main.setSpacing(14)
        main.setContentsMargins(20, 16, 20, 18)
        main.addWidget(self._build_header_card())
        self._summary_area = QWidget()
        self._sa_lay = QVBoxLayout(self._summary_area)
        self._sa_lay.setContentsMargins(0, 0, 0, 0)
        self._sa_lay.setSpacing(14)
        main.addWidget(self._summary_area, 1)
        self._summary_area.setVisible(False)
        main.addWidget(self._build_footer())

    def _field(self, label, widget):
        v = QVBoxLayout()
        v.setSpacing(4)
        v.addWidget(_fl(label))
        v.addWidget(widget)
        return v

    def _build_header_card(self) -> QFrame:
        card = QFrame()
        card.setStyleSheet("QFrame{background:#141d2e;border-radius:12px;padding:0}")
        cv = QVBoxLayout(card)
        cv.setContentsMargins(24, 20, 24, 22)
        cv.setSpacing(14)

        sup_items = [("-- اختر المذخر --", None)] + [(s["name"], s["id"]) for s in self.supplier_ctrl.get_all()]
        self.supplier_combo = _make_combo(sup_items, 50)

        self.inv_num_inp = QLineEdit()
        self.inv_num_inp.setPlaceholderText("INV-2025-001")
        self.inv_num_inp.setFixedHeight(50)
        self.inv_num_inp.setStyleSheet(_INP_SS)

        self.date_inp = QDateEdit()
        self.date_inp.setCalendarPopup(True)
        self.date_inp.setDate(QDate.currentDate())
        self.date_inp.setDisplayFormat("yyyy-MM-dd")
        self.date_inp.setFixedHeight(50)
        self.date_inp.setStyleSheet(
            "QDateEdit{background:#0b1120;border:none;border-bottom:2px solid #2a3f5f;"
            "border-radius:8px;padding:8px 12px;"
            "color:#f1f5f9;font-size:18px;font-weight:700}"
            "QDateEdit:focus{border-bottom:2px solid #4a8fe7}"
        )

        row0 = QHBoxLayout()
        row0.setSpacing(16)
        row0.addLayout(self._field("🏪  المذخر", self.supplier_combo), 2)
        row0.addLayout(self._field("🔢  رقم الفاتورة", self.inv_num_inp), 1)
        row0.addLayout(self._field("📅  التاريخ", self.date_inp), 1)
        cv.addLayout(row0)

        self.invoice_total_spin = QDoubleSpinBox()
        self.invoice_total_spin.setRange(0, 999999999)
        self.invoice_total_spin.setDecimals(2)
        self.invoice_total_spin.setLocale(locale_iqd)
        self.invoice_total_spin.setGroupSeparatorShown(True)
        self.invoice_total_spin.setFixedHeight(50)
        self.invoice_total_spin.setStyleSheet(_INP_NUM_SS + "QDoubleSpinBox{min-width:130px}")
        self.invoice_total_spin.valueChanged.connect(self._on_total_changed)

        self.paid_spin = QDoubleSpinBox()
        self.paid_spin.setRange(0, 999999999)
        self.paid_spin.setDecimals(2)
        self.paid_spin.setLocale(locale_iqd)
        self.paid_spin.setGroupSeparatorShown(True)
        self.paid_spin.setFixedHeight(50)
        self.paid_spin.setStyleSheet(_INP_NUM_SS + "QDoubleSpinBox{min-width:130px}")
        self.paid_spin.valueChanged.connect(self._recalc_remain)

        self.remain_lbl = QLabel("0.00")
        self.remain_lbl.setMinimumHeight(50)
        self.remain_lbl.setStyleSheet(
            "font-size:22px;font-weight:800;color:#7ba3ff;background:#0b1120;"
            "border-radius:8px;padding:8px 12px"
        )

        row1 = QHBoxLayout()
        row1.setSpacing(16)
        row1.addLayout(self._field("💵  الإجمالي", self.invoice_total_spin))
        row1.addLayout(self._field("💰  المسدد", self.paid_spin))
        row1.addLayout(self._field("📊  المتبقي", self.remain_lbl))
        cv.addLayout(row1)

        self.item_count_spin = QSpinBox()
        self.item_count_spin.setRange(1, 200)
        self.item_count_spin.setValue(1)
        self.item_count_spin.setFixedHeight(50)
        self.item_count_spin.setLocale(locale_iqd)
        self.item_count_spin.setStyleSheet(_INP_NUM_SS + "QSpinBox{min-width:80px}")

        self.start_btn = QPushButton("▶  بدء الإدخال")
        self.start_btn.setFixedHeight(50)
        self.start_btn.setStyleSheet(
            "QPushButton{font-size:15px;font-weight:700;background:#3b82f6;"
            "color:white;border:none;border-radius:10px;padding:0 28px}"
            "QPushButton:hover{background:#2563eb}"
        )
        self.start_btn.clicked.connect(self._start_entry)

        row2 = QHBoxLayout()
        row2.setSpacing(12)
        ic_label = _fl("📋  عدد الأصناف")
        row2.addWidget(ic_label)
        row2.addWidget(self.item_count_spin)
        row2.addWidget(self.start_btn)
        row2.addStretch()
        cv.addLayout(row2)

        cv.addWidget(_fl("📝  ملاحظات"))
        self.notes_inp = QLineEdit()
        self.notes_inp.setPlaceholderText("ملاحظات اختيارية…")
        self.notes_inp.setFixedHeight(50)
        self.notes_inp.setStyleSheet(_INP_SS)
        cv.addWidget(self.notes_inp)

        return card

    def _build_footer(self) -> QFrame:
        f = QFrame()
        f.setStyleSheet("QFrame{background:#141d2e;border-radius:12px;padding:0}")
        fl = QHBoxLayout(f)
        fl.setContentsMargins(20, 14, 20, 14)
        fl.setSpacing(12)

        self._save_inv_btn = QPushButton("💾  حفظ الفاتورة")
        self._save_inv_btn.setFixedHeight(50)
        self._save_inv_btn.setStyleSheet(
            "QPushButton{font-size:16px;font-weight:700;background:#059669;"
            "color:white;border:none;border-radius:10px;padding:0 32px}"
            "QPushButton:hover{background:#047857}"
        )
        self._save_inv_btn.clicked.connect(self._save_invoice)
        self._save_inv_btn.setVisible(False)
        fl.addWidget(self._save_inv_btn)

        self._cancel_btn = QPushButton("إلغاء")
        self._cancel_btn.setFixedHeight(50)
        self._cancel_btn.setStyleSheet(
            "QPushButton{font-size:16px;font-weight:600;background:#334155;"
            "color:#94a3b8;border:none;border-radius:10px;padding:0 32px}"
            "QPushButton:hover{background:#475569;color:#f1f5f9}"
        )
        self._cancel_btn.clicked.connect(self.reject)
        fl.addWidget(self._cancel_btn)
        fl.addStretch()

        self._total_items_lbl = QLabel("")
        self._total_items_lbl.setStyleSheet("font-size:16px;font-weight:700;color:#8899bb;background:transparent")
        fl.addWidget(self._total_items_lbl)
        return f

    def _on_total_changed(self):
        self._recalc_remain()

    def _recalc_remain(self):
        total = to_decimal(self.invoice_total_spin.value())
        paid = to_decimal(self.paid_spin.value())
        remain = total - paid
        self.remain_lbl.setText(f"{format_currency(remain)} د.ع")

    def _start_entry(self):
        count = self.item_count_spin.value()
        self._items.clear()
        self.setEnabled(False)

        for i in range(count):
            dlg = BulkItemDialog(
                self.window() if self.window() else self,
                index=i, total=count,
                categories=self._categories,
            )
            if dlg.exec_() == QDialog.Accepted:
                self._items.append(dlg.get_data())
            else:
                break

        self.setEnabled(True)
        self.raise_()

        if self._items:
            self._show_summary()
        else:
            self._summary_area.setVisible(False)
            self._save_inv_btn.setVisible(False)

    def _show_summary(self):
        self._summary_area.setVisible(True)

        for i in reversed(range(self._sa_lay.count())):
            w = self._sa_lay.itemAt(i).widget()
            if w:
                w.deleteLater()

        card = QFrame()
        card.setStyleSheet("QFrame{background:#141d2e;border-radius:12px;padding:0}")
        cv = QVBoxLayout(card)
        cv.setContentsMargins(24, 20, 24, 22)
        cv.setSpacing(14)

        cv.addWidget(_fl("📋  ملخص الأصناف"))
        cv.addWidget(QLabel(f"إجمالي الأصناف: {len(self._items)}"))

        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(["#", "الباركود", "اسم المادة", "الكمية", "سعر الوحدة", "الإجمالي"])
        table.setRowCount(len(self._items))
        table.setStyleSheet(
            "QTableWidget{background:#0b1120;border:none;border-radius:8px;"
            "color:#f1f5f9;font-size:14px;gridline-color:#1e2d45}"
            "QHeaderView::section{background:#1e2d45;color:#c8d6e5;"
            "font-size:14px;font-weight:700;padding:10px;border:none}"
        )
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        table.setMinimumHeight(200)

        grand_total = DECIMAL_ZERO
        for i, it in enumerate(self._items):
            total = to_decimal(str(it["total_price"]))
            grand_total += total
            table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            table.setItem(i, 1, QTableWidgetItem(it.get("barcode", "")))
            table.setItem(i, 2, QTableWidgetItem(it.get("name", "")))
            table.setItem(i, 3, QTableWidgetItem(str(it.get("quantity", 0))))
            table.setItem(i, 4, QTableWidgetItem(format_currency(to_decimal(str(it.get("unit_price", 0))))))
            table.setItem(i, 5, QTableWidgetItem(format_currency(total)))
            for c in range(6):
                item = table.item(i, c)
                if item:
                    item.setForeground(QColor("#e2e8f0"))

        cv.addWidget(table, 1)

        total_row = QHBoxLayout()
        total_row.setSpacing(16)
        total_row.addWidget(QLabel(f"💰  إجمالي قيمة الأصناف: {format_currency(grand_total)} د.ع"))
        total_row.itemAt(0).widget().setStyleSheet(
            "font-size:20px;font-weight:800;color:#7ba3ff;background:transparent"
        )
        total_row.addStretch()

        edit_btn = QPushButton("✏️  تعديل الأصناف")
        edit_btn.setFixedHeight(50)
        edit_btn.setStyleSheet(
            "QPushButton{font-size:15px;font-weight:600;background:#2a3f5f;"
            "color:#7ba3ff;border:none;border-radius:10px;padding:0 24px}"
            "QPushButton:hover{background:#3a5580}"
        )
        edit_btn.clicked.connect(self._edit_items)
        total_row.addWidget(edit_btn)
        cv.addLayout(total_row)

        self._sa_lay.addWidget(card)
        self._save_inv_btn.setVisible(True)
        self._total_items_lbl.setText(f"✅ {len(self._items)} صنف — الإجمالي: {format_currency(grand_total)} د.ع")

    def _edit_items(self):
        for i, it in enumerate(self._items):
            dlg = BulkItemDialog(
                self.window() if self.window() else self,
                index=i, total=len(self._items),
                categories=self._categories,
            )
            dlg.barcode_inp.setText(it.get("barcode", ""))
            dlg.name_inp.setText(it.get("name", ""))
            dlg.sci_inp.setText(it.get("scientific_name", ""))
            idx = dlg.cat_combo.findData(it.get("category_id"))
            if idx >= 0:
                dlg.cat_combo.setCurrentIndex(idx)
            dlg.qty_spin.setValue(it.get("quantity", 1))
            dlg.purchase_price_input.setValue(float(it.get("unit_price", 0)))
            dlg.qty_in_pack_spin.setValue(int(it.get("strips_per_pack", 6)))
            dlg.min_stock_spin.setValue(int(it.get("min_stock", 10)))
            dlg.expiry_inp.setDate(QDate.fromString(it.get("expiry_date", ""), "yyyy-MM-dd") or QDate.currentDate())
            if it.get("sale_price"):
                dlg.sale_price_input.setValue(float(it["sale_price"]))

            if dlg.exec_() == QDialog.Accepted:
                self._items[i] = dlg.get_data()
        self._show_summary()

    def _save_invoice(self):
        supplier_id = self.supplier_combo.currentData()
        if not supplier_id:
            QMessageBox.warning(None, "تنبيه", "يرجى اختيار المذخر (المورد)")
            return
        if not self._items:
            QMessageBox.warning(None, "تنبيه", "لا توجد أصناف لحفظها")
            return

        inv_total = to_decimal(self.invoice_total_spin.value())
        paid = to_decimal(self.paid_spin.value())
        items_total = sum(to_decimal(str(it["total_price"])) for it in self._items)

        try:
            self.debt_ctrl.create_bulk_invoice(
                supplier_id=supplier_id,
                invoice_number=self.inv_num_inp.text().strip() or None,
                invoice_total=inv_total,
                paid_amount=paid,
                remaining=inv_total - paid,
                items=self._items,
                notes=self.notes_inp.text().strip() or None,
            )
            QMessageBox.information(None, "تم", "تم حفظ الفاتورة بنجاح")
            self.invoice_saved.emit()
            self.accept()
        except Exception as e:
            QMessageBox.critical(None, "خطأ", f"فشل حفظ الفاتورة:\n{str(e)}")
