from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import Qt

class ModernMessageBox(QMessageBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setStyleSheet("""
            QMessageBox {
                background-color: #1e293b;
                border: 2px solid #38bdf8;
            }
            QLabel {
                color: #f1f5f9;
                font-size: 15px;
                font-weight: 500;
                padding: 10px;
            }
            QPushButton {
                background-color: #38bdf8;
                color: #0f172a;
                border: none;
                padding: 8px 24px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
                min-width: 80px;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #0284c7;
                color: #f1f5f9;
            }
        """)

    @staticmethod
    def _create_and_exec(icon, parent, title, text, buttons, defaultButton):
        msg = ModernMessageBox(parent)
        msg.setIcon(icon)
        msg.setWindowTitle(title)
        msg.setText(text)
        if buttons is not None:
            msg.setStandardButtons(buttons)
        if defaultButton is not None:
            msg.setDefaultButton(defaultButton)
        return msg.exec_()

    @staticmethod
    def information(parent, title, text, buttons=None, defaultButton=None):
        if buttons is None: buttons = QMessageBox.Ok
        return ModernMessageBox._create_and_exec(QMessageBox.Information, parent, title, text, buttons, defaultButton)

    @staticmethod
    def warning(parent, title, text, buttons=None, defaultButton=None):
        if buttons is None: buttons = QMessageBox.Ok
        return ModernMessageBox._create_and_exec(QMessageBox.Warning, parent, title, text, buttons, defaultButton)

    @staticmethod
    def critical(parent, title, text, buttons=None, defaultButton=None):
        if buttons is None: buttons = QMessageBox.Ok
        return ModernMessageBox._create_and_exec(QMessageBox.Critical, parent, title, text, buttons, defaultButton)

    @staticmethod
    def question(parent, title, text, buttons=None, defaultButton=None):
        if buttons is None: buttons = QMessageBox.Yes | QMessageBox.No
        return ModernMessageBox._create_and_exec(QMessageBox.Question, parent, title, text, buttons, defaultButton)
