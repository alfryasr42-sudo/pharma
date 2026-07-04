"""
OrderController — إدارة نقوصات الصيدلية (الطلبية)
يُستخدم لتسجيل المواد الناقصة وحذفها تلقائياً عند الشراء.
"""
from database.connection import DatabaseManager


class OrderController:
    def __init__(self):
        self.db = DatabaseManager()
        self._ensure_table()

    def _ensure_table(self):
        """إنشاء الجدول إن لم يكن موجوداً (حماية إضافية)"""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS order_items (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                quantity    INTEGER DEFAULT 0,
                unit        TEXT,
                company     TEXT,
                notes       TEXT,
                created_at  DATETIME DEFAULT (datetime('now','localtime'))
            )
        """)

    def get_all(self):
        """جلب كل النقوصات مرتبة بالأحدث"""
        return self.db.fetchall(
            "SELECT * FROM order_items ORDER BY created_at DESC"
        )

    def get_count(self):
        """عدد النقوصات الحالية"""
        row = self.db.fetchone("SELECT COUNT(*) as cnt FROM order_items")
        return row["cnt"] if row else 0

    def add(self, name: str, quantity: int = 0, unit: str = "", company: str = "", notes: str = ""):
        """إضافة مادة ناقصة"""
        name = name.strip()
        if not name:
            return
        self.db.execute(
            "INSERT INTO order_items (name, quantity, unit, company, notes) VALUES (?, ?, ?, ?, ?)",
            (name, quantity, unit.strip(), company.strip(), notes.strip()),
        )

    def update(self, item_id: int, name: str, quantity: int = 0, unit: str = "", company: str = "", notes: str = ""):
        """تحديث مادة ناقصة"""
        self.db.execute(
            "UPDATE order_items SET name=?, quantity=?, unit=?, company=?, notes=? WHERE id=?",
            (name.strip(), quantity, unit.strip(), company.strip(), notes.strip(), item_id),
        )

    def remove(self, item_id: int):
        """حذف نقص بواسطة المعرف"""
        self.db.execute(
            "DELETE FROM order_items WHERE id = ?", (item_id,)
        )

    def remove_by_name(self, name: str):
        """
        حذف تلقائي باستخدام خوارزمية ذكية (Fuzzy Matching) لتجنب الأخطاء الإملائية.
        يقارن الاسم المضاف مع النواقص المسجلة، وإذا كانت نسبة التطابق عالية (أكثر من 75%)
        أو كان أحدهما يحتوي الآخر، يتم حذفه.
        """
        import difflib

        name = name.strip().lower()
        if not name:
            return

        # جلب جميع النواقص لفحصها
        items = self.get_all()
        to_delete = []

        for item in items:
            order_name = item["name"].strip().lower()
            
            # فحص التطابق التام أو الجزئي المباشر
            if name in order_name or order_name in name:
                to_delete.append(item["id"])
                continue
                
            # فحص التقارب الإملائي (Similarity)
            # باستخدام SequenceMatcher للمقارنة بين الكلمتين
            similarity = difflib.SequenceMatcher(None, name, order_name).ratio()
            
            # إذا كانت نسبة التقارب 75% أو أكثر نعتبرها نفس المادة (أخطاء إملائية بسيطة)
            if similarity >= 0.75:
                to_delete.append(item["id"])

        # حذف المواد التي تم العثور عليها
        for item_id in to_delete:
            self.remove(item_id)

    def clear_all(self):
        """حذف كل النقوصات"""
        self.db.execute("DELETE FROM order_items")
