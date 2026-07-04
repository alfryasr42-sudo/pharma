from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGraphicsDropShadowEffect, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QGridLayout, QLineEdit,
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, pyqtProperty, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QColor, QPalette, QLinearGradient, QBrush, QPainter, QRadialGradient, QPen, QFont
from controllers.order_controller import OrderController
from database.connection import DatabaseManager


class GlassCard(QFrame):
    clicked = pyqtSignal()

    def __init__(self, icon, title, subtitle, shortcut, grad_from, grad_to, w=260, h=210, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(w, h)
        self.setMouseTracking(True)
        self._c1 = QColor(grad_from)
        self._c2 = QColor(grad_to)
        self._hv = 0.0
        self._mpos = None
        self._anim = QPropertyAnimation(self, b"hv", self)
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._setup_ui(icon, title, subtitle, shortcut)
        self._setup_shadow()

    def _setup_ui(self, icon, title, subtitle, shortcut):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(8)
        for txt, sz, col in [(icon, 46, None), (title, 22, "white"), (subtitle, 14, "rgba(255,255,255,180)")]:
            lbl = QLabel(txt)
            lbl.setAlignment(Qt.AlignCenter)
            ss = f"font-size: {sz}px; background: transparent;"
            if col:
                ss += f" color: {col};"
            lbl.setStyleSheet(ss)
            layout.addWidget(lbl)
        self.setLayout(layout)

    def _setup_shadow(self):
        pos_glow = QGraphicsDropShadowEffect()
        pos_glow.setBlurRadius(35)
        pos_glow.setColor(QColor(44, 83, 100, 180))
        pos_glow.setOffset(0, 6)
        self.setGraphicsEffect(pos_glow)

    @pyqtProperty(float)
    def hv(self):
        return self._hv

    @hv.setter
    def hv(self, v):
        self._hv = v
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        bg = QLinearGradient(0, 0, w, h)
        bg.setColorAt(0, QColor(self._c1.red(), self._c1.green(), self._c1.blue(), int(170 + 50 * self._hv)))
        bg.setColorAt(1, QColor(self._c2.red(), self._c2.green(), self._c2.blue(), int(150 + 50 * self._hv)))
        p.setBrush(QBrush(bg))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(0, 0, w, h, 20, 20)
        if self._hv > 0.01 and self._mpos:
            gl = QRadialGradient(self._mpos.x(), self._mpos.y(), 120 * self._hv)
            gl.setColorAt(0, QColor(255, 255, 255, int(40 * self._hv)))
            gl.setColorAt(0.5, QColor(255, 255, 255, int(10 * self._hv)))
            gl.setColorAt(1, QColor(255, 255, 255, 0))
            p.setBrush(QBrush(gl))
            p.drawRoundedRect(0, 0, w, h, 20, 20)
        p.setPen(QPen(QColor(255, 255, 255, int(60 + 120 * self._hv)), 1 + self._hv))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(1, 1, w - 2, h - 2, 19, 19)
        p.end()

    def enterEvent(self, event):
        self._anim_to(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._anim_to(0.0)
        self._mpos = None
        super().leaveEvent(event)

    def mouseMoveEvent(self, event):
        self._mpos = event.pos()
        self.update()
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)

    def _anim_to(self, t):
        self._anim.stop()
        self._anim.setStartValue(self._hv)
        self._anim.setEndValue(t)
        self._anim.start()


class DashboardWidget(QWidget):
    navigate = pyqtSignal(str)

    def __init__(self, user_data, parent=None):
        super().__init__(parent)
        self.user_data = user_data
        self.setMinimumSize(1200, 700)
        self.setAutoFillBackground(True)
        self._update_bg()
        self._setup_ui()

    def _update_bg(self):
        p = self.palette()
        g = QLinearGradient(0, 0, 0, self.height())
        g.setColorAt(0.0, QColor("#0f0c29"))
        g.setColorAt(0.5, QColor("#302b63"))
        g.setColorAt(1.0, QColor("#24243e"))
        p.setBrush(QPalette.Window, QBrush(g))
        self.setPalette(p)

    def resizeEvent(self, event):
        self._update_bg()
        super().resizeEvent(event)

    def _setup_ui(self):
        from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QGridLayout
        from database.connection import DatabaseManager

        layout = QVBoxLayout()
        layout.setSpacing(16)
        layout.setContentsMargins(30, 20, 30, 20)

        # ── BODY ──
        body = QHBoxLayout()
        body.setSpacing(20)

        # ── LEFT COLUMN: Tables ──
        left_col = QVBoxLayout()
        left_col.setSpacing(12)

        table_style = """
            QTableWidget {
                background: rgba(20, 25, 35, 200);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
                color: #f1f5f9;
                gridline-color: transparent;
                outline: none;
            }
            QHeaderView::section {
                background: rgba(15, 20, 30, 230);
                color: #94a3b8;
                padding: 10px 8px;
                border: none;
                border-bottom: 1px solid rgba(255, 255, 255, 12);
                font-size: 14px;
                font-weight: bold;
            }
            QTableWidget::item {
                padding: 10px 8px;
                border-bottom: 1px solid rgba(255, 255, 255, 6);
                font-size: 14px;
            }
            QTableWidget::item:hover { background: rgba(255, 255, 255, 8); }
            QTableWidget::item:selected { background: rgba(56,189,248,30); color: #38bdf8; }
            QScrollBar:vertical { background: rgba(15,23,42,100); width: 8px; border-radius: 4px; }
            QScrollBar::handle:vertical { background: rgba(255,255,255,40); border-radius: 4px; }
        """

        # Expired Table
        exp_lbl = QLabel("⚠️ المواد المنتهية / قريبة الانتهاء")
        exp_lbl.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #f87171; "
            "padding: 8px 16px; background: rgba(248,113,113,15); "
            "border: 1px solid rgba(248,113,113,40); border-radius: 8px;"
        )
        exp_lbl.setAlignment(Qt.AlignCenter)
        left_col.addWidget(exp_lbl)

        self.exp_table = QTableWidget()
        self.exp_table.setColumnCount(4)
        self.exp_table.setHorizontalHeaderLabels(["الحالة", "تاريخ الانتهاء", "الكمية", "اسم المادة"])
        self.exp_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        for i in range(0, 3):
            self.exp_table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.exp_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.exp_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.exp_table.verticalHeader().setVisible(False)
        self.exp_table.setStyleSheet(table_style)
        left_col.addWidget(self.exp_table, 1)

        # Low Stock Table
        low_lbl = QLabel("📦 المواد قريبة نفاذ الكمية")
        low_lbl.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #fbbf24; "
            "padding: 8px 16px; background: rgba(251,191,36,15); "
            "border: 1px solid rgba(251,191,36,40); border-radius: 8px;"
        )
        low_lbl.setAlignment(Qt.AlignCenter)
        left_col.addWidget(low_lbl)

        self.low_stock_table = QTableWidget()
        self.low_stock_table.setColumnCount(4)
        self.low_stock_table.setHorizontalHeaderLabels(["الحالة", "الحد الأدنى", "الكمية", "اسم المادة"])
        self.low_stock_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        for i in range(0, 3):
            self.low_stock_table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.low_stock_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.low_stock_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.low_stock_table.verticalHeader().setVisible(False)
        self.low_stock_table.setStyleSheet(table_style)
        left_col.addWidget(self.low_stock_table, 1)

        body.addLayout(left_col, 4)

        # ── RIGHT COLUMN: Title + Cards ──
        right_col = QVBoxLayout()
        right_col.setSpacing(12)
        right_col.setContentsMargins(0, 0, 0, 0)

        # Pharmacy Name
        db = DatabaseManager()
        pn_row = db.fetchone("SELECT setting_value FROM settings WHERE setting_key = 'pharmacy_name'")
        pharmacy_name = pn_row["setting_value"] if pn_row and pn_row["setting_value"] else "صيدلية الأمل"

        sys_name = QLabel("RTX")
        sys_name.setStyleSheet(
            "font-size: 46px; font-weight: bold; color: #ffffff; "
            "background: transparent; letter-spacing: 8px;"
        )
        sys_name.setAlignment(Qt.AlignCenter)
        right_col.addWidget(sys_name)

        self.ph_lbl = QLabel(pharmacy_name)
        self.ph_lbl.setStyleSheet(
            "font-size: 22px; font-weight: bold; "
            "color: rgba(255,255,255,180); background: transparent;"
        )
        self.ph_lbl.setAlignment(Qt.AlignCenter)
        right_col.addWidget(self.ph_lbl)

        right_col.addSpacing(10)

        is_admin = self.user_data.get("role") == "admin"

        # ── POS: Wide GlassCard hero at top ──
        pos_card = GlassCard("🛒", "نقطة البيع", "البيع المباشر وتسجيل الفواتير", "F2",
                             "#4A00E0", "#8E2DE2", w=530, h=140)
        pos_card.setFixedHeight(140)
        pos_card.setMinimumWidth(400)
        pos_card.setMaximumWidth(16777215)  # allow stretch
        pos_card.setSizePolicy(
            __import__('PyQt5.QtWidgets', fromlist=['QSizePolicy']).QSizePolicy.Expanding,
            __import__('PyQt5.QtWidgets', fromlist=['QSizePolicy']).QSizePolicy.Fixed
        )
        pos_card.clicked.connect(lambda: self._on_card_clicked("نقطة البيع"))
        right_col.addWidget(pos_card)

        right_col.addSpacing(10)


        # ── Compact cards grid (3 columns) ──
        _cw, _ch = 175, 170  # compact card size

        cc = QWidget()
        cc.setStyleSheet("background: transparent;")
        grid = QGridLayout(cc)
        grid.setSpacing(12)
        grid.setContentsMargins(0, 0, 0, 0)

        inv_card = GlassCard("📦", "المخزون", "إدارة المنتجات", "F3", "#9b23ea", "#5f72bd", _cw, _ch)
        inv_card.clicked.connect(lambda: self._on_card_clicked("المخزون"))
        grid.addWidget(inv_card, 0, 0)

        cust_card = GlassCard("💰", "ديون الزبائن", "إدارة ديون العملاء", "F1", "#00c6ff", "#0072ff", _cw, _ch)
        cust_card.clicked.connect(lambda: self._on_card_clicked("الديون"))
        grid.addWidget(cust_card, 0, 1)

        doc_card = GlassCard("👨‍⚕️", "الأطباء", "حسابات الأطباء", "F4", "#0ba360", "#3cba92", _cw, _ch)
        doc_card.clicked.connect(lambda: self._on_card_clicked("الأطباء"))
        grid.addWidget(doc_card, 0, 2)

        rep_card = GlassCard("📊", "التقارير", "الإحصائيات", "F6", "#73d13d", "#52c41a", _cw, _ch)
        rep_card.clicked.connect(lambda: self._on_card_clicked("التقارير"))
        if not is_admin:
            grid.addWidget(rep_card, 1, 0, 1, 3, Qt.AlignCenter)
        else:
            grid.addWidget(rep_card, 1, 0)

            set_card = GlassCard("⚙️", "الإعدادات", "تكوين النظام", "F5", "#d63131", "#a62424", _cw, _ch)
            set_card.clicked.connect(lambda: self._on_card_clicked("الإعدادات"))
            grid.addWidget(set_card, 1, 1)

            order_card = GlassCard("📋", "الطلبية", "تسجيل النواقص", "F7", "#5c258d", "#4389a2", _cw, _ch)
            order_card.clicked.connect(lambda: self._on_card_clicked("الطلبية"))
            grid.addWidget(order_card, 1, 2)

        if not is_admin:
            order_card = GlassCard("📋", "الطلبية", "تسجيل النواقص", "F7", "#5c258d", "#4389a2", _cw, _ch)
            order_card.clicked.connect(lambda: self._on_card_clicked("الطلبية"))
            grid.addWidget(order_card, 1, 1)

        right_col.addWidget(cc)
        right_col.addStretch()


        body.addLayout(right_col, 5)
        layout.addLayout(body)

        # Load tables data
        self._load_expired()
        self._load_low_stock()

        layout.addSpacing(6)
        st = QLabel("جميع الحقوق محفوظة © PharmaSys 2026")
        st.setStyleSheet("font-size: 11px; color: rgba(255,255,255,50); background: transparent;")
        st.setAlignment(Qt.AlignCenter)
        layout.addWidget(st)
        self.setLayout(layout)

    def showEvent(self, event):
        super().showEvent(event)
        # Refresh pharmacy name from DB
        db = DatabaseManager()
        pn_row = db.fetchone("SELECT setting_value FROM settings WHERE setting_key = 'pharmacy_name'")
        pharmacy_name = pn_row["setting_value"] if pn_row and pn_row["setting_value"] else "صيدلية الأمل"
        self.ph_lbl.setText(pharmacy_name)

    def _on_card_clicked(self, title):
        if title == "الطلبية":
            from views.order_dialog import OrderDialog
            OrderDialog(self).exec_()
            return

        m = {
            "نقطة البيع": "pos", "المخزون": "inventory", "الديون": "debts",
            "الأطباء": "doctors", "الإعدادات": "settings", "التقارير": "reports"
        }
        k = m.get(title)
        if k:
            self.navigate.emit(k)

    def _load_expired(self):
        from controllers.expiry_controller import ExpiryController
        from PyQt5.QtWidgets import QTableWidgetItem
        from PyQt5.QtGui import QColor, QBrush
        from datetime import datetime, date
        
        ctrl = ExpiryController()
        items = ctrl.get_expired() + ctrl.get_expiring_soon(60)
        self.exp_table.setRowCount(0)
        
        for p in items:
            p_dict = dict(p)
            r = self.exp_table.rowCount()
            self.exp_table.insertRow(r)
            
            # Name (right aligned for Arabic)
            name_item = QTableWidgetItem(p_dict.get("name") or "")
            name_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.exp_table.setItem(r, 0, name_item)
            
            # Qty (centered)
            qty_item = QTableWidgetItem(str(p_dict.get("stock_quantity") or 0))
            qty_item.setTextAlignment(Qt.AlignCenter)
            self.exp_table.setItem(r, 1, qty_item)
            
            # Expiry date (centered)
            exp_date = p_dict.get("expiry_date") or ""
            exp_item = QTableWidgetItem(exp_date)
            exp_item.setTextAlignment(Qt.AlignCenter)
            self.exp_table.setItem(r, 2, exp_item)
            
            # Status (centered + colored)
            status = "قريبة الانتهاء"
            status_color = "#fbbf24" # yellow
            if exp_date:
                try:
                    d = datetime.strptime(exp_date, "%Y-%m-%d").date()
                    if d < date.today():
                        status = "منتهية"
                        status_color = "#f87171" # red
                except: pass
            
            s_item = QTableWidgetItem(status)
            s_item.setTextAlignment(Qt.AlignCenter)
            s_item.setForeground(QBrush(QColor(status_color)))
            font = s_item.font()
            font.setBold(True)
            s_item.setFont(font)
            
            self.exp_table.setItem(r, 3, s_item)

    def _load_low_stock(self):
        from controllers.product_controller import ProductController
        from PyQt5.QtWidgets import QTableWidgetItem
        from PyQt5.QtGui import QColor, QBrush
        
        ctrl = ProductController()
        items = ctrl.get_low_stock()
        self.low_stock_table.setRowCount(0)
        
        for p in items:
            p_dict = dict(p)
            r = self.low_stock_table.rowCount()
            self.low_stock_table.insertRow(r)
            
            # Name (right aligned)
            name_item = QTableWidgetItem(p_dict.get("name") or "")
            name_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.low_stock_table.setItem(r, 0, name_item)
            
            # Qty (centered)
            qty = p_dict.get("stock_quantity") or 0
            qty_item = QTableWidgetItem(str(qty))
            qty_item.setTextAlignment(Qt.AlignCenter)
            self.low_stock_table.setItem(r, 1, qty_item)
            
            # Min stock (centered)
            min_item = QTableWidgetItem(str(p_dict.get("min_stock") or 0))
            min_item.setTextAlignment(Qt.AlignCenter)
            self.low_stock_table.setItem(r, 2, min_item)
            
            # Status (centered + colored)
            status = "نفذت" if qty <= 0 else "منخفضة"
            status_color = "#f87171" if qty <= 0 else "#fbbf24"
            
            s_item = QTableWidgetItem(status)
            s_item.setTextAlignment(Qt.AlignCenter)
            s_item.setForeground(QBrush(QColor(status_color)))
            font = s_item.font()
            font.setBold(True)
            s_item.setFont(font)
            
            self.low_stock_table.setItem(r, 3, s_item)

