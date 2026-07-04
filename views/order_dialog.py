import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QSpinBox, QComboBox, QFrame, QWidget,
    QFileDialog, QMessageBox
)
from PyQt5.QtCore import Qt, QLocale
from PyQt5.QtGui import QColor, QBrush, QFont, QPainter, QLinearGradient, QPen
from PyQt5.QtPrintSupport import QPrinter
from PyQt5.QtGui import QTextDocument

from controllers.order_controller import OrderController

_BG    = "#0f172a"
_CARD  = "#1e293b"
_BORD  = "#334155"
_PURPLE = "#a78bfa"
_PURPLE_DARK = "#7c3aed"
_TEXT  = "#f1f5f9"
_MUTED = "#94a3b8"


class OrderDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.order_ctrl = OrderController()

        self.setWindowTitle("📦 الطلبية - نقوصات الصيدلية")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setMinimumSize(1100, 750)
        self.setStyleSheet(f"QDialog{{background:{_BG};color:{_TEXT};border:1.5px solid {_BORD};border-radius:14px}}")

        self._editing_id = None
        self._setup_ui()
        self._load_orders()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ──
        header = QFrame()
        header.setFixedHeight(60)
        header.setStyleSheet(f"""
            QFrame{{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
                     stop:0 {_PURPLE_DARK},stop:1 #5b21b6);
                     border-bottom:1px solid {_BORD}}}
        """)
        hdr_lay = QHBoxLayout(header)
        hdr_lay.setContentsMargins(20, 0, 16, 0)

        icon_lbl = QLabel("📦")
        icon_lbl.setStyleSheet("font-size:22px;background:transparent")

        title_lbl = QLabel("الطلبية - نقوصات الصيدلية")
        title_lbl.setStyleSheet("font-size:18px;font-weight:700;color:#fff;background:transparent")

        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedSize(40, 40)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setStyleSheet("""
            QPushButton{background:transparent;color:#fca5a5;font-size:20px;font-weight:700;
                       border:2px solid rgba(255,255,255,0.2);border-radius:8px}
            QPushButton:hover{background:#ef4444;color:#fff;border-color:#ef4444}
        """)
        self.btn_close.clicked.connect(self.accept)

        hdr_lay.addWidget(icon_lbl)
        hdr_lay.addSpacing(8)
        hdr_lay.addWidget(title_lbl)
        hdr_lay.addStretch()
        hdr_lay.addWidget(self.btn_close)
        root.addWidget(header)

        # ── Content ──
        content = QVBoxLayout()
        content.setContentsMargins(24, 20, 24, 20)
        content.setSpacing(16)

        # ── Add bar ──
        add_lay = QHBoxLayout()
        add_lay.setSpacing(10)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("اسم العلاج أو المادة...")

        self.qty_input = QSpinBox()
        self.qty_input.setRange(1, 9999)
        self.qty_input.setLocale(QLocale(QLocale.English, QLocale.UnitedStates))
        self.qty_input.setGroupSeparatorShown(True)
        self.qty_input.setFixedWidth(100)

        self.unit_combo = QComboBox()
        self.unit_combo.setEditable(True)
        self.unit_combo.addItems(["علب", "أشرطة", "كراتين", "قناني", "أمبولات"])
        self.unit_combo.setFixedWidth(110)
        self.unit_combo.setStyleSheet("""
            QComboBox::drop-down{subcontrol-origin:padding;subcontrol-position:left;
                      width:28px;border:none}
            QComboBox::down-arrow{image:none;width:0;height:0;
                      border-left:5px solid transparent;border-right:5px solid transparent;
                      border-top:7px solid #94a3b8}
            QComboBox QAbstractItemView{background:#1e293b;color:#f1f5f9;
                       selection-background:#7c3aed;selection-color:#fff}
            QComboBox QAbstractItemView::item{min-height:36px;padding:4px 10px}
        """)

        self.company_input = QLineEdit()
        self.company_input.setPlaceholderText("الشركة (اختياري)...")

        self.notes_input = QLineEdit()
        self.notes_input.setPlaceholderText("ملاحظة (اختياري)...")

        self.add_btn = QPushButton("➕ إضافة")
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.setFixedHeight(44)
        self.add_btn.setStyleSheet("""
            QPushButton{font-size:15px;font-weight:700;padding:0 20px;
                       background:#7c3aed;color:#fff;border:none;border-radius:8px}
            QPushButton:hover{background:#6d28d9}
            QPushButton:pressed{background:#5b21b6}
        """)
        self.add_btn.clicked.connect(self._add_or_update)

        self.cancel_edit_btn = QPushButton("✕")
        self.cancel_edit_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_edit_btn.setFixedSize(44, 44)
        self.cancel_edit_btn.setToolTip("إلغاء التعديل")
        self.cancel_edit_btn.setStyleSheet("""
            QPushButton{background:#334155;color:#94a3b8;font-size:18px;font-weight:700;
                       border:none;border-radius:8px}
            QPushButton:hover{background:#ef4444;color:#fff}
        """)
        self.cancel_edit_btn.clicked.connect(self._cancel_edit)
        self.cancel_edit_btn.setVisible(False)

        # Uniform field height
        field_h = 44
        for w in [self.name_input, self.qty_input, self.unit_combo, self.company_input, self.notes_input]:
            w.setFixedHeight(field_h)
        self.name_input.setMinimumWidth(160)
        self.company_input.setMinimumWidth(120)
        self.notes_input.setMinimumWidth(120)

        field_style = f"""
            QLineEdit,QSpinBox,QComboBox{{background:{_CARD};color:{_TEXT};
                       border:1.5px solid {_BORD};border-radius:8px;
                       padding:6px 12px;font-size:15px}}
            QLineEdit:focus,QSpinBox:focus,QComboBox:focus{{border-color:{_PURPLE}}}
            QSpinBox::up-button,QSpinBox::down-button{{width:24px;border:none;
                       background:transparent;subcontrol-position:right}}
        """
        for w in [self.name_input, self.qty_input, self.unit_combo, self.company_input, self.notes_input]:
            if hasattr(w, 'setStyleSheet'):
                if w is self.unit_combo:
                    w.setStyleSheet(w.styleSheet() + f"""
                        QComboBox{{background:{_CARD};color:{_TEXT};
                                   border:1.5px solid {_BORD};border-radius:8px;
                                   padding:6px 12px;font-size:15px}}
                        QComboBox:focus{{border-color:{_PURPLE}}}
                    """)
                else:
                    w.setStyleSheet(field_style)

        add_lay.addWidget(self.name_input, 3)
        add_lay.addWidget(self.qty_input)
        add_lay.addWidget(self.unit_combo)
        add_lay.addWidget(self.company_input, 2)
        add_lay.addWidget(self.notes_input, 2)
        add_lay.addWidget(self.cancel_edit_btn)
        add_lay.addWidget(self.add_btn)
        content.addLayout(add_lay)

        # ── Table ──
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["اسم العلاج", "الكمية", "الوحدة", "الشركة", "ملاحظة", "إجراء"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self.table.horizontalHeader().resizeSection(1, 90)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.table.horizontalHeader().resizeSection(2, 100)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Fixed)
        self.table.horizontalHeader().resizeSection(5, 180)
        self.table.horizontalHeader().setStretchLastSection(False)

        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(f"""
            QTableWidget{{background:{_CARD};border:1.5px solid {_BORD};
                         border-radius:12px;color:{_TEXT};gridline-color:transparent;outline:none}}
            QHeaderView::section{{background:#0f172a;color:{_PURPLE};padding:10px 6px;
                        border:none;border-bottom:2px solid {_BORD};font-size:13px;font-weight:700}}
            QTableWidget::item{{padding:6px 6px;border-bottom:1px solid rgba(255,255,255,0.04);font-size:14px}}
            QTableWidget::item:hover{{background:rgba(167,139,250,0.1)}}
            QTableWidget::item:selected{{background:rgba(167,139,250,0.2);color:#c4b5fd}}
            QTableWidget{{alternate-background-color:#162033}}
        """)
        content.addWidget(self.table, 1)

        # ── Footer ──
        footer = QFrame()
        footer.setStyleSheet(f"QFrame{{background:#0c1220;border-top:1px solid {_BORD}}}")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(24, 14, 24, 14)

        self.btn_print = QPushButton("🖨️ PDF")
        self.btn_print.setCursor(Qt.PointingHandCursor)
        self.btn_print.setFixedHeight(42)
        self.btn_print.setStyleSheet(f"""
            QPushButton{{background:{_PURPLE_DARK};color:#fff;font-weight:700;font-size:15px;
                       border:none;border-radius:8px;padding:0 24px}}
            QPushButton:hover{{background:#6d28d9}}
        """)
        self.btn_print.clicked.connect(self._export_order_pdf)

        self.btn_close2 = QPushButton("❌ إغلاق")
        self.btn_close2.setCursor(Qt.PointingHandCursor)
        self.btn_close2.setFixedHeight(42)
        self.btn_close2.setStyleSheet(f"""
            QPushButton{{background:{_CARD};color:{_MUTED};font-weight:700;font-size:15px;
                       border:none;border-radius:8px;padding:0 24px}}
            QPushButton:hover{{background:{_BORD};color:{_TEXT}}}
        """)
        self.btn_close2.clicked.connect(self.accept)

        fl.addWidget(self.btn_print)
        fl.addStretch()
        fl.addWidget(self.btn_close2)

        root.addLayout(content)
        root.addWidget(footer)

    def _load_orders(self):
        items = self.order_ctrl.get_all()
        self.table.setRowCount(0)

        for item in items:
            item_dict = dict(item)
            r = self.table.rowCount()
            self.table.insertRow(r)

            name_item = QTableWidgetItem(item_dict.get("name") or "")
            name_item.setTextAlignment(Qt.AlignCenter)
            f = name_item.font()
            f.setBold(True)
            f.setPointSize(14)
            name_item.setFont(f)
            self.table.setItem(r, 0, name_item)

            qty_item = QTableWidgetItem(str(item_dict.get("quantity") or 0))
            qty_item.setTextAlignment(Qt.AlignCenter)
            qty_item.setForeground(QBrush(QColor("#38bdf8")))
            f = qty_item.font()
            f.setBold(True)
            f.setPointSize(14)
            qty_item.setFont(f)
            self.table.setItem(r, 1, qty_item)

            unit_item = QTableWidgetItem(item_dict.get("unit") or "")
            unit_item.setTextAlignment(Qt.AlignCenter)
            unit_item.setForeground(QBrush(QColor(_MUTED)))
            self.table.setItem(r, 2, unit_item)

            company_item = QTableWidgetItem(item_dict.get("company") or "")
            company_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r, 3, company_item)

            notes_item = QTableWidgetItem(item_dict.get("notes") or "")
            notes_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r, 4, notes_item)

            # ── Actions cell: Edit + Delete ──
            item_id = item_dict.get("id")
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(2, 2, 2, 2)
            action_layout.setSpacing(6)

            edit_btn = QPushButton("✏️ تعديل")
            edit_btn.setToolTip("تعديل")
            edit_btn.setCursor(Qt.PointingHandCursor)
            edit_btn.setFixedHeight(34)
            edit_btn.setStyleSheet("""
                QPushButton{font-size:13px;font-weight:700;background:#2563eb20;
                           color:#60a5fa;border:1.5px solid #2563eb50;
                           border-radius:6px;padding:0 8px}
                QPushButton:hover{background:#2563eb;color:#fff;border-color:#2563eb}
            """)
            edit_btn.clicked.connect(lambda checked, iid=item_id, d=item_dict: self._start_edit(iid, d))

            del_btn = QPushButton("🗑️ حذف")
            del_btn.setToolTip("حذف")
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setFixedHeight(34)
            del_btn.setStyleSheet("""
                QPushButton{font-size:13px;font-weight:700;background:#ef444420;
                           color:#f87171;border:1.5px solid #ef444450;
                           border-radius:6px;padding:0 8px}
                QPushButton:hover{background:#ef4444;color:#fff;border-color:#ef4444}
            """)
            del_btn.clicked.connect(lambda checked, iid=item_id: self._remove_order(iid))

            action_layout.addWidget(edit_btn)
            action_layout.addWidget(del_btn)
            self.table.setCellWidget(r, 5, action_widget)
            self.table.setRowHeight(r, 48)

    def _add_or_update(self):
        name = self.name_input.text().strip()
        if not name:
            return
        qty = self.qty_input.value()
        unit = self.unit_combo.currentText().strip()
        company = self.company_input.text().strip()
        notes = self.notes_input.text().strip()

        if self._editing_id is not None:
            self.order_ctrl.update(self._editing_id, name, qty, unit, company, notes)
        else:
            self.order_ctrl.add(name, qty, unit, company, notes)

        self._reset_form()
        self._load_orders()

    def _start_edit(self, item_id, item_dict):
        self._editing_id = item_id
        self.name_input.setText(item_dict.get("name") or "")
        self.qty_input.setValue(int(item_dict.get("quantity") or 1))
        unit = item_dict.get("unit") or ""
        idx = self.unit_combo.findText(unit, Qt.MatchFixedString)
        if idx >= 0:
            self.unit_combo.setCurrentIndex(idx)
        else:
            self.unit_combo.setEditText(unit)
        self.company_input.setText(item_dict.get("company") or "")
        self.notes_input.setText(item_dict.get("notes") or "")
        self.add_btn.setText("💾 حفظ")
        self.cancel_edit_btn.setVisible(True)
        self.name_input.setFocus()

    def _cancel_edit(self):
        self._reset_form()

    def _reset_form(self):
        self._editing_id = None
        self.name_input.clear()
        self.qty_input.setValue(1)
        self.company_input.clear()
        self.notes_input.clear()
        self.add_btn.setText("➕ إضافة")
        self.cancel_edit_btn.setVisible(False)
        self.name_input.setFocus()

    def _remove_order(self, item_id):
        self.order_ctrl.remove(item_id)
        if self._editing_id == item_id:
            self._cancel_edit()
        self._load_orders()

    def _export_order_pdf(self):
        items = self.order_ctrl.get_all()
        if not items:
            QMessageBox.information(self, "تنبيه", "لا توجد مواد في الطلبية")
            return

        rows_html = ""
        for i, item in enumerate(items, 1):
            rows_html += f"""
                <tr>
                    <td>{i}</td>
                    <td>{item['name'] or ''}</td>
                    <td style="text-align:center">{item['quantity'] or 0}</td>
                    <td style="text-align:center">{item['unit'] or ''}</td>
                    <td>{item['company'] or ''}</td>
                    <td>{item['notes'] or ''}</td>
                </tr>"""

        html = f"""
        <html dir="rtl">
        <head><meta charset="utf-8"></head>
        <body style="font-family:'Segoe UI','Tahoma',sans-serif;padding:20px">
            <h2 style="text-align:center;color:#7c3aed">📦 الطلبية - نقوصات الصيدلية</h2>
            <hr style="border:1px solid #ddd">
            <table style="width:100%;border-collapse:collapse;margin-top:16px">
                <thead>
                    <tr style="background:#7c3aed;color:#fff">
                        <th style="padding:10px">#</th>
                        <th style="padding:10px">اسم العلاج</th>
                        <th style="padding:10px">الكمية</th>
                        <th style="padding:10px">الوحدة</th>
                        <th style="padding:10px">الشركة</th>
                        <th style="padding:10px">ملاحظة</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
            <p style="text-align:left;margin-top:20px;color:#666;font-size:12px">
                تم الإنشاء: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}
            </p>
        </body>
        </html>"""

        file_path, _ = QFileDialog.getSaveFileName(
            self, "حفظ الطلبية كملف PDF", "الطلبية.pdf", "PDF Files (*.pdf)"
        )
        if not file_path:
            return
        if not file_path.endswith(".pdf"):
            file_path += ".pdf"

        printer = QPrinter(QPrinter.ScreenResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(file_path)
        printer.setPageMargins(12, 12, 12, 12, QPrinter.Millimeter)

        doc = QTextDocument()
        doc.setHtml(html)
        doc.setPageSize(printer.pageRect().size())
        doc.print_(printer)

        QMessageBox.information(self, "تم", f"حفظ الطلبية بنجاح:\n{os.path.basename(file_path)}")
