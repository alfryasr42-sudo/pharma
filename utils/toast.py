import sys
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QApplication
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QRect, QEasingCurve
from PyQt5.QtGui import QFont, QPainter, QColor, QPen, QBrush

class ToastNotification(QWidget):
    def __init__(self, message, duration=50000, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.SubWindow | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        if not parent:
            self.setWindowFlags(self.windowFlags() | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        self.duration = duration
        self._setup_ui(message)
        self.opacity = 0.0

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide_toast)

    def _setup_ui(self, message):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        self.container = QWidget()
        self.container.setStyleSheet("""
            QWidget {
                background-color: rgba(15, 23, 42, 245);
                border: 2px solid #ef4444;
                border-radius: 12px;
            }
        """)
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(16, 16, 16, 16)
        container_layout.setSpacing(10)
        
        # Header layout
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        icon_lbl = QLabel("⚠️")
        icon_lbl.setStyleSheet("font-size: 18px; background: transparent; border: none;")
        title_lbl = QLabel("تنبيهات المخزن والمواد")
        title_lbl.setStyleSheet("color: #ef4444; font-size: 15px; font-weight: bold; background: transparent; border: none;")
        header.addWidget(icon_lbl)
        header.addWidget(title_lbl)
        header.addStretch()
        
        # Close button inside toast
        close_btn = QPushButton("✕")
        close_btn.setStyleSheet("QPushButton { color: #94a3b8; font-size: 13px; font-weight: bold; background: transparent; border: none; } QPushButton:hover { color: #ef4444; }")
        close_btn.clicked.connect(self.hide_toast)
        header.addWidget(close_btn)
        
        container_layout.addLayout(header)
        
        lbl = QLabel(message)
        lbl.setStyleSheet("color: #e2e8f0; font-size: 13px; line-height: 1.4; background: transparent; border: none;")
        lbl.setWordWrap(True)
        container_layout.addWidget(lbl)
        
        layout.addWidget(self.container)
        self.setLayout(layout)
        self.setMinimumWidth(380)
        self.setMaximumWidth(450)
        self.adjustSize()

    def show_toast(self):
        self.adjustSize()
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.x() + screen.width() - self.width() - 20, 
                  screen.y() + screen.height() - self.height() - 20)
        
        self.show()
        
        self.anim_in = QPropertyAnimation(self, b"windowOpacity")
        self.anim_in.setDuration(300)
        self.anim_in.setStartValue(0.0)
        self.anim_in.setEndValue(1.0)
        self.anim_in.start()

        self.timer.start(self.duration)

    def hide_toast(self):
        self.anim_out = QPropertyAnimation(self, b"windowOpacity")
        self.anim_out.setDuration(300)
        self.anim_out.setStartValue(1.0)
        self.anim_out.setEndValue(0.0)
        self.anim_out.finished.connect(self.close)
        self.anim_out.start()

    def mousePressEvent(self, event):
        self.hide_toast()
        super().mousePressEvent(event)

    @classmethod
    def show_message(cls, message, duration=50000, parent=None):
        toast = cls(message, duration, parent)
        toast.show_toast()
        return toast
