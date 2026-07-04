from PyQt5.QtCore import QObject, pyqtSignal, QUrl
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PyQt5.QtWidgets import QMessageBox
import json
from version import VERSION


class UpdateChecker(QObject):
    finished = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._manager = QNetworkAccessManager(self)
        self._manager.finished.connect(self._on_reply)

    def check(self):
        url = "https://raw.githubusercontent.com/alfryasr42-sudo/pharma/main/version.json"
        self._manager.get(QNetworkRequest(QUrl(url)))

    def _on_reply(self, reply):
        if reply.error():
            return
        try:
            data = json.loads(bytes(reply.readAll()).decode("utf-8"))
            latest = data.get("latest", "")
            url = data.get("url", "")
            if latest > VERSION:
                self.finished.emit(latest, url)
        except Exception:
            pass


def show_update_dialog(parent, latest, url):
    msg = QMessageBox(parent)
    msg.setWindowTitle("تحديث متوفر")
    msg.setText(f"الإصدار {latest} متوفر الآن!")
    msg.setInformativeText("هل تريد تحميل التحديث؟")
    msg.setIcon(QMessageBox.Information)
    msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    msg.setDefaultButton(QMessageBox.Yes)
    if msg.exec_() == QMessageBox.Yes:
        import webbrowser
        webbrowser.open(url)
