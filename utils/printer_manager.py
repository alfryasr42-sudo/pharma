import random
from PyQt5.QtPrintSupport import QPrinter, QPrinterInfo
from PyQt5.QtGui import QPainter, QFont, QColor, QPen
from PyQt5.QtCore import Qt, QRectF

from database.connection import DatabaseManager

class PrinterManager:
    def __init__(self):
        self.db = DatabaseManager()

    def get_available_printers(self):
        """إرجاع قائمة بأسماء الطابعات المتوفرة"""
        return [p.printerName() for p in QPrinterInfo.availablePrinters()]

    def get_default_barcode_printer(self):
        row = self.db.fetchone("SELECT setting_value FROM settings WHERE setting_key = 'barcode_printer'")
        return row["setting_value"] if row else ""

    def get_default_receipt_printer(self):
        row = self.db.fetchone("SELECT setting_value FROM settings WHERE setting_key = 'receipt_printer'")
        return row["setting_value"] if row else ""

    def save_printer_settings(self, barcode_printer, receipt_printer):
        self.db.execute("INSERT OR REPLACE INTO settings (setting_key, setting_value) VALUES ('barcode_printer', ?)", (barcode_printer,))
        self.db.execute("INSERT OR REPLACE INTO settings (setting_key, setting_value) VALUES ('receipt_printer', ?)", (receipt_printer,))

    def generate_random_barcode(self):
        """توليد رقم باركود عشوائي للتركيبات (12 رقم)"""
        # مثال: 2026 + 8 أرقام عشوائية
        return f"2026{random.randint(10000000, 99999999)}"

    def test_print(self, printer_name):
        """طباعة ورقة فحص للطابعة المحددة"""
        if not printer_name:
            return False, "لم يتم تحديد طابعة"

        printer = QPrinter()
        printer_info = QPrinterInfo.printerInfo(printer_name)
        if printer_info.isNull():
            return False, "الطابعة غير متوفرة"

        printer.setPrinterName(printer_name)
        
        painter = QPainter()
        if not painter.begin(printer):
            return False, "فشل في الاتصال بالطابعة"

        # إعدادات بسيطة لصفحة الفحص
        font = QFont("Arial", 16, QFont.Bold)
        painter.setFont(font)
        painter.drawText(100, 100, "PharmaSys - Test Print")
        
        font = QFont("Arial", 12)
        painter.setFont(font)
        painter.drawText(100, 150, "تم إعداد الطابعة بنجاح!")
        
        painter.end()
        return True, "تم إرسال أمر الطباعة بنجاح"

    def print_barcode(self, printer_name, barcode_text, product_name, copies=1):
        """طباعة باركود للمادة"""
        if not printer_name:
            return False, "لم يتم تحديد طابعة الباركود في الإعدادات"
            
        printer = QPrinter()
        printer_info = QPrinterInfo.printerInfo(printer_name)
        if printer_info.isNull():
            return False, "الطابعة المحددة غير متوفرة"

        printer.setPrinterName(printer_name)
        # إعداد الطابعة للحجم الصغير (تعتمد على إعدادات نظام التشغيل للطابعة الحرارية)
        # عادة طابعات الباركود تستخدم مقاسات معينة، نتركها للافتراضي الخاص بالطابعة

        painter = QPainter()
        
        try:
            # هنا يمكنك دمج مكتبة python-barcode لرسم الباركود بدقة
            # سنكتفي برسم تقريبي أو النص مؤقتاً لتجنب توقف النظام في حال عدم توفر المكتبة
            import barcode
            from barcode.writer import ImageWriter
            import tempfile
            import os
            from PyQt5.QtGui import QImage
            
            has_barcode_lib = True
        except ImportError:
            has_barcode_lib = False

        for i in range(copies):
            if i > 0:
                printer.newPage()
                
            if not painter.isActive() and not painter.begin(printer):
                return False, "فشل في بدء الطباعة"
            
            # رسم اسم المادة في الأعلى
            font = QFont("Arial", 10, QFont.Bold)
            painter.setFont(font)
            painter.drawText(QRectF(10, 10, 200, 30), Qt.AlignCenter, product_name)
            
            if has_barcode_lib:
                try:
                    # حفظ الباركود كصورة مؤقتة ثم رسمه
                    temp_dir = tempfile.gettempdir()
                    file_path = os.path.join(temp_dir, "temp_barcode")
                    # استخدام Code128 لدعم الحروف والأرقام
                    CODE128 = barcode.get_barcode_class('code128')
                    code_instance = CODE128(barcode_text, writer=ImageWriter())
                    
                    # نلغي كتابة النص تحت الباركود عبر المكتبة لنكتبه بأنفسنا بوضوح أو نتركه
                    options = {'write_text': False, 'module_height': 8.0, 'dpi': 300}
                    saved_path = code_instance.save(file_path, options=options)
                    
                    img = QImage(saved_path)
                    if not img.isNull():
                        # رسم الصورة في المنتصف
                        target_rect = QRectF(10, 40, 200, 60)
                        painter.drawImage(target_rect, img)
                        
                    # حذف الملف المؤقت
                    try:
                        os.remove(saved_path)
                    except:
                        pass
                except Exception:
                    # Fallback text
                    painter.drawText(QRectF(10, 50, 200, 40), Qt.AlignCenter, f"|||| {barcode_text} ||||")
            else:
                # إذا لم تكن المكتبة متوفرة، اطبع النص بشكل بارز
                font = QFont("Arial", 12)
                painter.setFont(font)
                painter.drawText(QRectF(10, 50, 200, 40), Qt.AlignCenter, f"* {barcode_text} *")
                
            # رسم الرقم أسفل الباركود
            font = QFont("Arial", 9)
            painter.setFont(font)
            painter.drawText(QRectF(10, 100, 200, 20), Qt.AlignCenter, barcode_text)
            
            if i < copies - 1:
                painter.end()

        if painter.isActive():
            painter.end()
            
        return True, "تمت طباعة الباركود بنجاح"
