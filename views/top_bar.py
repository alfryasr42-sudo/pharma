from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt, QTimer, QDateTime, pyqtSignal

class TopBar(QFrame):
    navigate = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(80)
        self.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1a1a2e, stop:1 #11111f);
                border-bottom: 1px solid rgba(102,126,234,0.3);
            }
            QLabel {
                color: rgba(255,255,255,220);
                font-weight: bold;
                font-size: 16px;
                background: transparent;
            }
            QPushButton {
                background: rgba(102,126,234,0.2);
                border: 1px solid rgba(102,126,234,0.5);
                border-radius: 8px;
                color: white;
                padding: 12px 28px;
                font-weight: bold;
                font-size: 16px;
                letter-spacing: 2px;
            }
            QPushButton:hover {
                background: rgba(102,126,234,0.5);
                border: 1px solid rgba(102,126,234,0.8);
            }
            QPushButton:pressed {
                background: rgba(102,126,234,0.7);
            }
            #sensorOk { color: #43e97b; }
            #sensorWarn { color: #f9ca24; }
            #sensorErr { color: #ff6b6b; }
        """)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout()
        # نفرض اتجاه من اليمين لليسار لتثبيت الأماكن
        layout.setDirection(QHBoxLayout.RightToLeft)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(15)

        # Home button
        self.home_btn = QPushButton("🏠 HOME")
        self.home_btn.setCursor(Qt.PointingHandCursor)
        self.home_btn.clicked.connect(lambda: self.navigate.emit("dashboard"))
        layout.addWidget(self.home_btn)

        layout.addStretch()

        # Maintenance Sensor
        self.maintenance_lbl = QLabel("🛠️ SYSTEM OK")
        self.maintenance_lbl.setObjectName("sensorOk")
        layout.addWidget(self.maintenance_lbl)

        # Internet Sensor
        self.internet_lbl = QLabel("🌐 ONLINE")
        self.internet_lbl.setObjectName("sensorOk")
        layout.addWidget(self.internet_lbl)

        # Date & Time
        self.time_lbl = QLabel()
        self.time_lbl.setStyleSheet("""
            color: #ffffff;
            font-size: 18px;
            font-weight: bold;
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.15);
            border-radius: 8px;
            padding: 8px 16px;
        """)
        layout.addWidget(self.time_lbl)

        layout.addSpacing(20)

        # Exit button
        self.exit_btn = QPushButton("⏻")
        self.exit_btn.setCursor(Qt.PointingHandCursor)
        self.exit_btn.setFixedSize(48, 48)
        self.exit_btn.setStyleSheet("""
            QPushButton {
                background: rgba(231,76,60,0.15);
                border: 1px solid rgba(231,76,60,0.4);
                border-radius: 24px;
                color: #e74c3c;
                font-size: 24px;
                padding: 0;
            }
            QPushButton:hover {
                background: rgba(231,76,60,0.8);
                color: white;
            }
        """)
        from PyQt5.QtWidgets import QApplication
        self.exit_btn.clicked.connect(lambda: QApplication.instance().quit())
        layout.addWidget(self.exit_btn)

        self.setLayout(layout)

        # Timer for time update
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_time)
        self.timer.start(1000)
        self._update_time()

    def _update_time(self):
        from PyQt5.QtCore import QLocale
        loc = QLocale(QLocale.English, QLocale.UnitedStates)
        current = QDateTime.currentDateTime()
        self.time_lbl.setText("🕒 " + loc.toString(current, "hh:mm:ss AP"))
