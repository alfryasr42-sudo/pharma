import math
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QGraphicsDropShadowEffect, QSizePolicy,
)
from PyQt5.QtCore import (
    Qt, pyqtSignal, QTimer, QRectF, QPointF,
    QPropertyAnimation, QEasingCurve, pyqtProperty, QSequentialAnimationGroup,
    QParallelAnimationGroup,
)
from PyQt5.QtGui import (
    QFont, QColor, QPainter, QLinearGradient, QBrush, QPen,
    QRadialGradient, QConicalGradient, QPainterPath,
)

from database.connection import DatabaseManager
from utils.auth import verify_password


# ─────────────────────────────────────────────
# بطاقة المستخدم - تصميم مستقبلي
# ─────────────────────────────────────────────
class UserCard(QFrame):
    clicked = pyqtSignal(str)

    ROLE_CFG = {
        "admin":   ("🛡️", "#667eea", "#764ba2", "مدير النظام"),
        "manager": ("⭐", "#f093fb", "#f5576c", "مشرف"),
        "cashier": ("👤", "#4facfe", "#00f2fe", "كاشير"),
    }

    def __init__(self, username: str, full_name: str, role: str, parent=None):
        super().__init__(parent)
        self.username = username
        self.full_name = full_name
        self.role = role
        self._selected = False
        self._hovered = False
        self._glow = 0.0
        cfg = self.ROLE_CFG.get(role, ("👤", "#667eea", "#764ba2", role))
        self._icon = cfg[0]
        self._c1 = QColor(cfg[1])
        self._c2 = QColor(cfg[2])
        self._role_label = cfg[3]

        self.setFixedSize(170, 145)
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)

        # أنيميشن الـ glow
        self._anim = QPropertyAnimation(self, b"glow_val", self)
        self._anim.setDuration(220)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 14, 10, 10)
        layout.setSpacing(4)

        icon_lbl = QLabel(self._icon)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 36px; background: transparent;")
        layout.addWidget(icon_lbl)

        name_lbl = QLabel(self.full_name)
        name_lbl.setAlignment(Qt.AlignCenter)
        name_lbl.setStyleSheet(
            "font-size: 13px; font-weight: bold; color: white; background: transparent;"
        )
        name_lbl.setWordWrap(True)
        layout.addWidget(name_lbl)

        role_lbl = QLabel(self._role_label)
        role_lbl.setAlignment(Qt.AlignCenter)
        role_lbl.setStyleSheet(
            "font-size: 10px; color: rgba(255,255,255,160); background: transparent;"
        )
        layout.addWidget(role_lbl)

        self.setLayout(layout)

    def _get_glow(self):
        return self._glow

    def _set_glow(self, v):
        self._glow = v
        self.update()

    glow_val = pyqtProperty(float, fget=_get_glow, fset=_set_glow)

    def _animate_to(self, target):
        self._anim.stop()
        self._anim.setStartValue(self._glow)
        self._anim.setEndValue(target)
        self._anim.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        g = self._glow

        if self._selected:
            # خلفية متدرجة مضيئة عند الاختيار
            bg = QLinearGradient(0, 0, w, h)
            bg.setColorAt(0, QColor(self._c1.red(), self._c1.green(), self._c1.blue(), 210))
            bg.setColorAt(1, QColor(self._c2.red(), self._c2.green(), self._c2.blue(), 190))
        else:
            alpha = int(25 + 35 * g)
            bg = QLinearGradient(0, 0, w, h)
            bg.setColorAt(0, QColor(255, 255, 255, alpha))
            bg.setColorAt(1, QColor(255, 255, 255, max(5, alpha - 15)))

        painter.setBrush(QBrush(bg))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, w, h, 18, 18)

        # حدود متوهجة
        if self._selected:
            border_alpha = 220
            border_w = 2.0
            pen_color = QColor(
                int(self._c1.red() * 0.7 + self._c2.red() * 0.3),
                int(self._c1.green() * 0.7 + self._c2.green() * 0.3),
                int(self._c1.blue() * 0.7 + self._c2.blue() * 0.3),
                border_alpha,
            )
        else:
            border_alpha = int(50 + 120 * g)
            border_w = 1.0 + g * 0.5
            pen_color = QColor(255, 255, 255, border_alpha)

        painter.setPen(QPen(pen_color, border_w))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(1, 1, w - 2, h - 2, 17, 17)

        # تأثير glow داخلي عند الـ hover أو الاختيار
        if g > 0.01 or self._selected:
            gv = 1.0 if self._selected else g
            c1r, c1g_c, c1b = self._c1.red(), self._c1.green(), self._c1.blue()
            glow = QRadialGradient(w / 2, h / 2, w * 0.7)
            glow.setColorAt(0, QColor(c1r, c1g_c, c1b, int(55 * gv)))
            glow.setColorAt(1, QColor(c1r, c1g_c, c1b, 0))
            painter.setBrush(QBrush(glow))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(0, 0, w, h, 18, 18)

        # خط سفلي متوهج عند الاختيار
        if self._selected:
            line_grad = QLinearGradient(10, h - 4, w - 10, h - 4)
            line_grad.setColorAt(0, QColor(self._c1.red(), self._c1.green(), self._c1.blue(), 0))
            line_grad.setColorAt(0.5, QColor(self._c1.red(), self._c1.green(), self._c1.blue(), 255))
            line_grad.setColorAt(1, QColor(self._c1.red(), self._c1.green(), self._c1.blue(), 0))
            painter.setPen(QPen(QBrush(line_grad), 2))
            painter.drawLine(12, h - 5, w - 12, h - 5)
        
        painter.end()

    def enterEvent(self, event):
        self._hovered = True
        self._animate_to(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self._animate_to(0.0)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        self.clicked.emit(self.username)
        super().mousePressEvent(event)

    def set_selected(self, selected: bool):
        self._selected = selected
        self._animate_to(1.0 if selected else 0.0)


# ─────────────────────────────────────────────
# نقطة متحركة في الخلفية
# ─────────────────────────────────────────────
class _Particle:
    def __init__(self, x, y, r, dx, dy, alpha):
        self.x, self.y, self.r = x, y, r
        self.dx, self.dy = dx, dy
        self.alpha = alpha
        self.base_alpha = alpha


# ─────────────────────────────────────────────
# نافذة تسجيل الدخول الرئيسية
# ─────────────────────────────────────────────
class LoginDialog(QDialog):
    login_successful = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = DatabaseManager()
        self.selected_username = None
        self.setWindowTitle("PharmaSys")
        self.setFixedSize(580, 600)
        # إخفاء زر الإغلاق
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.CustomizeWindowHint)

        # جسيمات الخلفية
        import random
        self._particles = []
        for _ in range(22):
            self._particles.append(_Particle(
                x=random.uniform(0, 580),
                y=random.uniform(0, 600),
                r=random.uniform(1.5, 4.5),
                dx=random.uniform(-0.3, 0.3),
                dy=random.uniform(-0.25, 0.25),
                alpha=random.randint(30, 90),
            ))
        self._tick = 0
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._animate_particles)
        self._anim_timer.start(30)

        self._setup_ui()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            return
        super().keyPressEvent(event)

    def _animate_particles(self):
        self._tick += 1
        for p in self._particles:
            p.x += p.dx
            p.y += p.dy
            if p.x < -10:
                p.x = 590
            if p.x > 590:
                p.x = -10
            if p.y < -10:
                p.y = 610
            if p.y > 610:
                p.y = -10
            # تنفس الـ alpha
            p.alpha = int(p.base_alpha + 20 * math.sin(self._tick * 0.05 + p.x))
            p.alpha = max(10, min(110, p.alpha))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        # خلفية متدرجة ثلاثية
        bg = QLinearGradient(0, 0, w, h)
        bg.setColorAt(0.0, QColor("#0a0818"))
        bg.setColorAt(0.4, QColor("#1a1035"))
        bg.setColorAt(0.75, QColor("#0d1b3e"))
        bg.setColorAt(1.0, QColor("#050d1a"))
        painter.setBrush(QBrush(bg))
        painter.setPen(Qt.NoPen)
        painter.drawRect(self.rect())

        # شبكة نقطية خفيفة
        painter.setPen(QPen(QColor(255, 255, 255, 8), 1))
        grid = 38
        for gx in range(0, w + grid, grid):
            painter.drawLine(gx, 0, gx, h)
        for gy in range(0, h + grid, grid):
            painter.drawLine(0, gy, w, gy)

        # دائرة ضوئية في الأعلى
        glow_top = QRadialGradient(w * 0.5, -30, 280)
        glow_top.setColorAt(0, QColor(102, 126, 234, 45))
        glow_top.setColorAt(0.5, QColor(118, 75, 162, 18))
        glow_top.setColorAt(1, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(glow_top))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QRectF(w * 0.5 - 280, -30 - 280, 560, 560))

        # دائرة ضوئية في الأسفل
        glow_bot = QRadialGradient(w * 0.5, h + 30, 220)
        glow_bot.setColorAt(0, QColor(79, 172, 254, 35))
        glow_bot.setColorAt(1, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(glow_bot))
        painter.drawEllipse(QRectF(w * 0.5 - 220, h + 30 - 220, 440, 440))

        # الجسيمات المتحركة
        for p in self._particles:
            c = QRadialGradient(p.x, p.y, p.r * 2.5)
            c.setColorAt(0, QColor(180, 200, 255, p.alpha))
            c.setColorAt(1, QColor(100, 150, 255, 0))
            painter.setBrush(QBrush(c))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QRectF(p.x - p.r * 2.5, p.y - p.r * 2.5, p.r * 5, p.r * 5))

        # الحدود الخارجية للنافذة بتأثير توهج
        border_grad = QLinearGradient(0, 0, w, h)
        border_grad.setColorAt(0, QColor(102, 126, 234, 80))
        border_grad.setColorAt(0.5, QColor(118, 75, 162, 50))
        border_grad.setColorAt(1, QColor(79, 172, 254, 80))
        painter.setPen(QPen(QBrush(border_grad), 1.5))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(QRectF(0.75, 0.75, w - 1.5, h - 1.5))
        
        painter.end()

    def _setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(48, 36, 48, 36)

        # ──── شعار وعنوان ────
        logo_lbl = QLabel("⬡")
        logo_lbl.setAlignment(Qt.AlignCenter)
        logo_lbl.setStyleSheet(
            "font-size: 52px; color: rgba(102,126,234,220); background: transparent;"
        )
        layout.addWidget(logo_lbl)
        layout.addSpacing(2)

        title = QLabel("PharmaSys")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            "font-size: 34px; font-weight: 900; letter-spacing: 4px;"
            "background: transparent;"
            "color: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #667eea, stop:0.5 #c084fc, stop:1 #4facfe);"
        )
        layout.addWidget(title)
        layout.addSpacing(2)

        sub = QLabel("نظام إدارة الصيدليات")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet(
            "font-size: 12px; letter-spacing: 2px;"
            "color: rgba(180,190,255,120); background: transparent;"
        )
        layout.addWidget(sub)
        layout.addSpacing(22)

        # ──── خط فاصل متوهج ────
        sep = _GlowSeparator()
        sep.setFixedHeight(2)
        layout.addWidget(sep)
        layout.addSpacing(20)

        # ──── عنوان الاختيار ────
        pick_lbl = QLabel("اختر حسابك")
        pick_lbl.setAlignment(Qt.AlignCenter)
        pick_lbl.setStyleSheet(
            "font-size: 11px; letter-spacing: 2px; text-transform: uppercase;"
            "color: rgba(180,190,255,140); background: transparent;"
        )
        layout.addWidget(pick_lbl)
        layout.addSpacing(14)

        # ──── بطاقات المستخدمين ────
        users = self.db.fetchall(
            "SELECT username, full_name, role FROM users WHERE is_active = 1 ORDER BY role, full_name"
        )
        self.cards = []
        cards_row = QHBoxLayout()
        cards_row.setSpacing(18)
        cards_row.setContentsMargins(0, 0, 0, 0)
        cards_row.addStretch()

        for u in users:
            card = UserCard(u["username"], u["full_name"], u["role"])
            card.clicked.connect(self._on_card_clicked)
            self.cards.append(card)
            cards_row.addWidget(card)

        cards_row.addStretch()
        layout.addLayout(cards_row)
        layout.addSpacing(24)

        # ──── حقل كلمة المرور ────
        self.password_input = _FuturisticLineEdit("🔒  كلمة المرور")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.returnPressed.connect(self._do_login)
        self.password_input.setEnabled(False)
        layout.addWidget(self.password_input)
        layout.addSpacing(16)

        # ──── أزرار الدخول والخروج ────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(15)

        self.exit_btn = QPushButton("✕ إغلاق النظام")
        self.exit_btn.setFixedHeight(52)
        self.exit_btn.setCursor(Qt.PointingHandCursor)
        self.exit_btn.setStyleSheet("""
            QPushButton {
                background: rgba(231,76,60,0.15); color: rgba(255,120,100,200);
                border: 1px solid rgba(231,76,60,0.4); border-radius: 14px;
                font-size: 14px; font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(231,76,60,0.4); color: white;
            }
        """)
        from PyQt5.QtWidgets import QApplication
        self.exit_btn.clicked.connect(lambda: QApplication.instance().quit())

        self.login_btn = _GlowButton("دخول  →")
        self.login_btn.setEnabled(False)
        self.login_btn.clicked.connect(self._do_login)

        btn_row.addWidget(self.exit_btn, 1)
        btn_row.addWidget(self.login_btn, 2)
        layout.addLayout(btn_row)
        layout.addSpacing(10)

        # ──── رسالة الحالة ────
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet(
            "font-size: 12px; color: rgba(255,90,90,200); background: transparent;"
        )
        layout.addWidget(self.status_label)

        layout.addStretch()
        self.setLayout(layout)

    def _on_card_clicked(self, username):
        self.selected_username = username
        for card in self.cards:
            card.set_selected(card.username == username)
        self.password_input.setEnabled(True)
        self.login_btn.setEnabled(True)
        self.password_input.setFocus()
        self.password_input.clear()
        self.status_label.setText("")

    def _do_login(self):
        username = self.selected_username
        password = self.password_input.text()

        if not username:
            self.status_label.setText("⚠  يرجى اختيار مستخدم")
            return
        if not password:
            self.status_label.setText("⚠  يرجى إدخال كلمة المرور")
            return

        user = self.db.fetchone(
            "SELECT * FROM users WHERE username = ? AND is_active = 1",
            (username,),
        )
        if user and verify_password(password, user["password_hash"]):
            self.user_data = {
                "id": user["id"],
                "username": user["username"],
                "full_name": user["full_name"],
                "role": user["role"],
            }
            self.login_successful.emit(self.user_data)
            self._anim_timer.stop()
            self.accept()
        else:
            self.status_label.setText("✕  كلمة المرور غير صحيحة")
            self.password_input.clear()
            self.password_input.setFocus()
            self.password_input.flash_error()
            self._shake(self.password_input)

    def _shake(self, widget):
        orig = widget.pos()
        steps = [6, -6, 4, -4, 2, -2, 0]
        timer = QTimer(self)
        idx = [0]

        def _step():
            if idx[0] < len(steps):
                widget.move(orig.x() + steps[idx[0]], orig.y())
                idx[0] += 1
            else:
                widget.move(orig)
                timer.stop()

        timer.timeout.connect(_step)
        timer.start(35)


# ─────────────────────────────────────────────
# مكونات مساعدة
# ─────────────────────────────────────────────
class _GlowSeparator(QFrame):
    """خط فاصل بتأثير توهج متدرج"""
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        grad = QLinearGradient(0, 0, w, 0)
        grad.setColorAt(0.0, QColor(0, 0, 0, 0))
        grad.setColorAt(0.3, QColor(102, 126, 234, 180))
        grad.setColorAt(0.5, QColor(192, 132, 252, 220))
        grad.setColorAt(0.7, QColor(79, 172, 254, 180))
        grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setPen(QPen(QBrush(grad), 2))
        painter.drawLine(0, 1, w, 1)
        
        painter.end()


class _FuturisticLineEdit(QLineEdit):
    """حقل إدخال بتصميم مستقبلي مع أنيميشن التركيز وحالة الخطأ"""

    def __init__(self, placeholder="", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setFixedHeight(52)
        self._focused = False
        self._glow = 0.0
        self._error = False

        self._anim = QPropertyAnimation(self, b"_glow_prop", self)
        self._anim.setDuration(250)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

        self.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                color: white;
                font-size: 15px;
                padding: 0 16px 0 44px;
                selection-background-color: rgba(102,126,234,120);
            }
        """)

    def flash_error(self):
        self._error = True
        self._anim.stop()
        self._anim.setStartValue(self._glow)
        self._anim.setEndValue(1.0)
        self._anim.start()
        QTimer.singleShot(1200, self._clear_error)

    def _clear_error(self):
        self._error = False
        if self._focused:
            self._anim.stop()
            self._anim.setStartValue(self._glow)
            self._anim.setEndValue(1.0)
            self._anim.start()
        else:
            self._anim.stop()
            self._anim.setStartValue(self._glow)
            self._anim.setEndValue(0.0)
            self._anim.start()
        self.update()

    def _get_gp(self):
        return self._glow

    def _set_gp(self, v):
        self._glow = v
        self.update()

    _glow_prop = pyqtProperty(float, fget=_get_gp, fset=_set_gp)

    def focusInEvent(self, event):
        self._focused = True
        self._anim.stop()
        self._anim.setStartValue(self._glow)
        self._anim.setEndValue(1.0)
        self._anim.start()
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        self._focused = False
        self._anim.stop()
        self._anim.setStartValue(self._glow)
        self._anim.setEndValue(0.0)
        self._anim.start()
        super().focusOutEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        g = self._glow

        if self._error:
            c1, c2 = QColor(239, 68, 68), QColor(220, 38, 38)
        else:
            c1, c2 = QColor(102, 126, 234), QColor(79, 172, 254)

        bg_alpha = int(18 + 22 * g)
        painter.setBrush(QBrush(QColor(255, 255, 255, bg_alpha)))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, w, h, 14, 14)

        if g > 0.01:
            border = QLinearGradient(0, 0, w, 0)
            border.setColorAt(0, QColor(c1.red(), c1.green(), c1.blue(), int(80 + 150 * g)))
            border.setColorAt(0.5, QColor(c1.red(), c2.green(), c2.blue(), int(100 + 155 * g)))
            border.setColorAt(1, QColor(c2.red(), c2.green(), c2.blue(), int(80 + 150 * g)))
            painter.setPen(QPen(QBrush(border), 1.5 + g * 0.5))
        else:
            painter.setPen(QPen(QColor(255, 255, 255, 45), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(1, 1, w - 2, h - 2, 13, 13)

        if g > 0.01:
            line = QLinearGradient(20, h - 2, w - 20, h - 2)
            line.setColorAt(0, QColor(c1.red(), c1.green(), c1.blue(), 0))
            line.setColorAt(0.5, QColor(c1.red(), c2.green(), c2.blue(), int(220 * g)))
            line.setColorAt(1, QColor(c2.red(), c2.green(), c2.blue(), 0))
            painter.setPen(QPen(QBrush(line), 2))
            painter.drawLine(20, h - 2, w - 20, h - 2)

        painter.end()
        super().paintEvent(event)


class _GlowButton(QPushButton):
    """زر بتأثير توهج مستقبلي"""

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setFixedHeight(52)
        self.setCursor(Qt.PointingHandCursor)
        self._hovered = False
        self._pressed = False
        self._glow = 0.0

        self._anim = QPropertyAnimation(self, b"_glow_p", self)
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

        self.setStyleSheet("QPushButton { background: transparent; border: none; }")

    def _get_gp(self):
        return self._glow

    def _set_gp(self, v):
        self._glow = v
        self.update()

    _glow_p = pyqtProperty(float, fget=_get_gp, fset=_set_gp)

    def _animate_to(self, target):
        self._anim.stop()
        self._anim.setStartValue(self._glow)
        self._anim.setEndValue(target)
        self._anim.start()

    def enterEvent(self, event):
        self._hovered = True
        self._animate_to(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self._animate_to(0.0)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        self._pressed = True
        self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._pressed = False
        self.update()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        if not self.isEnabled():
            self._draw_disabled()
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        g = self._glow
        scale = 0.97 if self._pressed else 1.0

        # تصغير عند الضغط
        if scale < 1.0:
            margin_x = w * (1 - scale) / 2
            margin_y = h * (1 - scale) / 2
            painter.translate(margin_x, margin_y)
            painter.scale(scale, scale)
            w = int(w * scale)
            h = int(h * scale)

        # خلفية متدرجة
        base_alpha = int(160 + 80 * g)
        grad = QLinearGradient(0, 0, w, h)
        grad.setColorAt(0, QColor(102, 126, 234, base_alpha))
        grad.setColorAt(0.5, QColor(118, 75, 162, int(base_alpha * 0.9)))
        grad.setColorAt(1, QColor(79, 172, 254, base_alpha))
        painter.setBrush(QBrush(grad))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, w, h, 14, 14)

        # طبقة ضوئية علوية
        shine = QLinearGradient(0, 0, 0, h // 2)
        shine.setColorAt(0, QColor(255, 255, 255, int(40 + 30 * g)))
        shine.setColorAt(1, QColor(255, 255, 255, 0))
        painter.setBrush(QBrush(shine))
        painter.drawRoundedRect(0, 0, w, h // 2, 14, 14)

        # حدود
        border = QLinearGradient(0, 0, w, 0)
        border.setColorAt(0, QColor(192, 132, 252, int(120 + 135 * g)))
        border.setColorAt(1, QColor(79, 172, 254, int(120 + 135 * g)))
        painter.setPen(QPen(QBrush(border), 1.5))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(1, 1, w - 2, h - 2, 13, 13)

        # النص
        painter.setPen(QPen(QColor(255, 255, 255, 230)))
        font = QFont("Segoe UI", 14, QFont.Bold)
        painter.setFont(font)
        painter.drawText(QRectF(0, 0, w, h), Qt.AlignCenter, self.text())
        
        painter.end()

    def _draw_disabled(self):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        painter.setBrush(QBrush(QColor(255, 255, 255, 12)))
        painter.setPen(QPen(QColor(255, 255, 255, 30), 1))
        painter.drawRoundedRect(0, 0, w, h, 14, 14)
        painter.setPen(QPen(QColor(255, 255, 255, 55)))
        font = QFont("Segoe UI", 14, QFont.Bold)
        painter.setFont(font)
        painter.drawText(QRectF(0, 0, w, h), Qt.AlignCenter, self.text())
        
        painter.end()
