import sys
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QApplication
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QPoint, QEasingCurve
from PyQt5.QtGui import QFont

class ToastNotification(QWidget):
    _active_toasts = []

    def __init__(self, message, duration=30000, parent=None, title="تنبيه"):
        super().__init__(parent)
        self.setWindowFlags(Qt.SubWindow | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        if not parent:
            self.setWindowFlags(self.windowFlags() | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.duration = duration
        self._setup_ui(message, title)
        self.opacity = 0.0

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide_toast)

        ToastNotification._active_toasts.append(self)

    def _setup_ui(self, message, title):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        self.container = QWidget()
        self.container.setStyleSheet("""
            QWidget {
                background-color: #0f172a;
                border: 2px solid #14b8a6;
                border-radius: 10px;
            }
        """)
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(14, 12, 14, 12)
        container_layout.setSpacing(8)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        icon_lbl = QLabel("⚠️")
        icon_lbl.setStyleSheet("font-size: 16px; background: transparent; border: none;")
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color: #14b8a6; font-size: 14px; font-weight: bold; background: transparent; border: none;")
        header.addWidget(icon_lbl)
        header.addWidget(title_lbl)
        header.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setStyleSheet("QPushButton { color: #64748b; font-size: 12px; font-weight: bold; background: transparent; border: none; padding: 2px 6px; } QPushButton:hover { color: #ef4444; }")
        close_btn.clicked.connect(self.hide_toast)
        header.addWidget(close_btn)

        container_layout.addLayout(header)

        lbl = QLabel(message)
        lbl.setStyleSheet("color: #e2e8f0; font-size: 13px; background: transparent; border: none;")
        lbl.setWordWrap(True)
        container_layout.addWidget(lbl)

        layout.addWidget(self.container)
        self.setLayout(layout)
        self.setMinimumWidth(340)
        self.setMaximumWidth(420)
        self.adjustSize()

    def show_toast(self):
        self.adjustSize()
        screen = QApplication.primaryScreen().availableGeometry()
        base_x = screen.x() + screen.width() - self.width() - 20
        base_y = screen.y() + screen.height() - self.height() - 20

        offset = 0
        for t in ToastNotification._active_toasts:
            if t is not self and t.isVisible():
                offset += t.height() + 10

        self.move(base_x, base_y - offset)
        self.show()

        self.anim_in = QPropertyAnimation(self, b"windowOpacity")
        self.anim_in.setDuration(250)
        self.anim_in.setStartValue(0.0)
        self.anim_in.setEndValue(1.0)
        self.anim_in.start()

        self.timer.start(self.duration)

    def hide_toast(self):
        self.timer.stop()
        if self in ToastNotification._active_toasts:
            ToastNotification._active_toasts.remove(self)
        self.anim_out = QPropertyAnimation(self, b"windowOpacity")
        self.anim_out.setDuration(250)
        self.anim_out.setStartValue(1.0)
        self.anim_out.setEndValue(0.0)
        self.anim_out.finished.connect(self.close)
        self.anim_out.start()

    def mousePressEvent(self, event):
        self.hide_toast()
        super().mousePressEvent(event)

    def closeEvent(self, event):
        if self in ToastNotification._active_toasts:
            ToastNotification._active_toasts.remove(self)
        super().closeEvent(event)

    @classmethod
    def show_message(cls, message, duration=30000, parent=None, title="تنبيه"):
        toast = cls(message, duration, parent, title)
        toast.show_toast()
        return toast

    @classmethod
    def clear_all(cls):
        for t in cls._active_toasts[:]:
            try:
                t.hide_toast()
            except:
                pass
