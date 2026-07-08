import os

# --- PATCH inventory_widget.py ---
inv_path = r'd:\pharma\views\inventory_widget.py'
with open(inv_path, 'r', encoding='utf-8') as f:
    inv = f.read()

# remove right_col layout
ui_old = '''        # ── right panel: alerts ──
        right_col = QVBoxLayout()
        right_col.setSpacing(8)
        right_col.setContentsMargins(0, 0, 0, 0)

        alert_header = _lbl("تنبيهات سريعة", "#f1f5f9", 15, True)
        right_col.addWidget(alert_header)

        self.alerts_area = QWidget()
        self.alerts_layout = QVBoxLayout(self.alerts_area)
        self.alerts_layout.setSpacing(6)
        self.alerts_layout.setContentsMargins(0, 0, 0, 0)
        self.alerts_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidget(self.alerts_area)
        scroll.setWidgetResizable(True)
        scroll.setFixedWidth(320)
        scroll.setStyleSheet(
            "QScrollArea{background:#1e293b;border:1px solid #334155;"
            "border-radius:12px}"
            "QScrollBar:vertical{background:#0f172a;width:6px;border-radius:3px}"
            "QScrollBar::handle:vertical{background:#334155;border-radius:3px}"
        )
        right_col.addWidget(scroll, 1)

        # assemble
        root.addLayout(main_col, 1)
        root.addLayout(right_col)'''

ui_new = '''        # assemble
        root.addLayout(main_col, 1)'''
        
inv = inv.replace(ui_old, ui_new)

# replace _refresh_alerts
alert_old_start = '    def _refresh_alerts(self):'
alert_old_end = '    # ─────── actions ───────'

idx1 = inv.find(alert_old_start)
idx2 = inv.find(alert_old_end)

if idx1 != -1 and idx2 != -1:
    new_alert = '''    def _refresh_alerts(self):
        alerts = []
        for p in self._all_products:
            status = self._product_status(p)
            name = p.get("name") or ""
            qty = p.get("stock_quantity") or 0
            if status == "expired":
                alerts.append(f"{name} - {qty} - منتهية الصلاحية")
            elif status == "low":
                alerts.append(f"{name} - {qty} - منخفضة في المخزن")
                
            if len(alerts) >= 15:
                break
                
        if alerts:
            from utils.toast import ToastNotification
            ToastNotification.show_message("\\n".join(alerts), 30000, self.window())

'''
    inv = inv[:idx1] + new_alert + inv[idx2:]

with open(inv_path, 'w', encoding='utf-8') as f:
    f.write(inv)


# --- PATCH dashboard_widget.py ---
dash_path = r'd:\pharma\views\dashboard_widget.py'
with open(dash_path, 'r', encoding='utf-8') as f:
    dash = f.read()

# Add table logic to DashboardWidget
setup_ui_old = '''        cl.addStretch()
        cc.setLayout(cl)
        layout.addWidget(cc)
        layout.addStretch()
        st = QLabel("جميع الحقوق محفوظة © RTX 2026")'''

setup_ui_new = '''        cl.addStretch()
        cc.setLayout(cl)
        layout.addWidget(cc)
        
        # Table for expired products
        from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
        from controllers.expiry_controller import ExpiryController
        
        t_lbl = QLabel("المواد المنتهية أو قريبة الانتهاء")
        t_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #f87171; background: transparent; margin-top: 15px;")
        layout.addWidget(t_lbl)
        
        self.exp_table = QTableWidget()
        self.exp_table.setColumnCount(4)
        self.exp_table.setHorizontalHeaderLabels(["اسم المادة", "الكمية", "تاريخ الانتهاء", "الحالة"])
        self.exp_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 4):
            self.exp_table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.exp_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.exp_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.exp_table.setStyleSheet(
            "QTableWidget { background:#1e293b; border:1px solid #334155; border-radius:8px; color:#f1f5f9; }"
            "QHeaderView::section { background:#0f172a; color:#94a3b8; padding:8px; border:none; border-bottom:1px solid #334155; font-weight:bold; }"
        )
        self.exp_table.setFixedHeight(180)
        
        layout.addWidget(self.exp_table)
        self._load_expired()
        
        layout.addStretch()
        st = QLabel("جميع الحقوق محفوظة © RTX 2026")'''

if setup_ui_old in dash:
    dash = dash.replace(setup_ui_old, setup_ui_new)

# Add _load_expired method
if 'def _load_expired(self):' not in dash:
    load_exp_code = '''    def _load_expired(self):
        from controllers.expiry_controller import ExpiryController
        from PyQt5.QtWidgets import QTableWidgetItem
        from datetime import datetime, date
        ctrl = ExpiryController()
        items = ctrl.get_expired() + ctrl.get_expiring_soon(60)
        self.exp_table.setRowCount(0)
        for p in items:
            r = self.exp_table.rowCount()
            self.exp_table.insertRow(r)
            self.exp_table.setItem(r, 0, QTableWidgetItem(p.get("name") or ""))
            self.exp_table.setItem(r, 1, QTableWidgetItem(str(p.get("stock_quantity") or 0)))
            self.exp_table.setItem(r, 2, QTableWidgetItem(p.get("expiry_date") or ""))
            
            exp_date = p.get("expiry_date")
            status = "قريبة الانتهاء"
            if exp_date:
                try:
                    d = datetime.strptime(exp_date, "%Y-%m-%d").date()
                    if d < date.today():
                        status = "منتهية"
                except: pass
            
            s_item = QTableWidgetItem(status)
            if status == "منتهية":
                from PyQt5.QtGui import QColor, QBrush
                s_item.setForeground(QBrush(QColor("#f87171")))
            else:
                from PyQt5.QtGui import QColor, QBrush
                s_item.setForeground(QBrush(QColor("#14b8a6")))
                
            self.exp_table.setItem(r, 3, s_item)

'''
    dash = dash + '\n' + load_exp_code

with open(dash_path, 'w', encoding='utf-8') as f:
    f.write(dash)

print('Patched successfully!')
