from database.connection import DatabaseManager
from utils.decimal_handler import to_decimal, from_decimal, DECIMAL_ZERO
from controllers.order_controller import OrderController


class SupplierDebtController:
    """تحكم في ديون الموردين (المذاخر) والفواتير المجمعة"""

    def __init__(self):
        self.db = DatabaseManager()
        self._ensure_tables()

    # ─── إنشاء الجداول إن لم تكن موجودة ───
    def _ensure_tables(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS supplier_debts (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                supplier_id     INTEGER NOT NULL,
                invoice_number  TEXT,
                total_amount    REAL    NOT NULL DEFAULT 0,
                paid_amount     REAL    NOT NULL DEFAULT 0,
                remaining_amount REAL   NOT NULL DEFAULT 0,
                status          TEXT    NOT NULL DEFAULT 'pending',
                notes           TEXT,
                created_at      DATETIME DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
            )
        """)
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS supplier_debt_payments (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                supplier_debt_id INTEGER NOT NULL,
                amount          REAL    NOT NULL,
                notes           TEXT,
                payment_date    DATETIME DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (supplier_debt_id) REFERENCES supplier_debts(id)
            )
        """)
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS supplier_debt_items (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                supplier_debt_id    INTEGER NOT NULL,
                product_id          INTEGER,
                barcode             TEXT,
                name                TEXT    NOT NULL,
                scientific_name     TEXT,
                category_id         INTEGER,
                quantity            INTEGER NOT NULL DEFAULT 0,
                unit_price          REAL    NOT NULL DEFAULT 0,
                total_price         REAL    NOT NULL DEFAULT 0,
                expiry_date         TEXT,
                min_stock           INTEGER DEFAULT 10,
                FOREIGN KEY (supplier_debt_id) REFERENCES supplier_debts(id)
            )
        """)

    # ─── قراءة ───
    def get_all_pending(self):
        return self.db.fetchall("""
            SELECT sd.*, s.name as supplier_name, s.phone as supplier_phone
            FROM supplier_debts sd
            JOIN suppliers s ON sd.supplier_id = s.id
            WHERE sd.status IN ('pending', 'partial')
            ORDER BY sd.created_at DESC
        """)

    def get_all(self):
        return self.db.fetchall("""
            SELECT sd.*, s.name as supplier_name, s.phone as supplier_phone
            FROM supplier_debts sd
            JOIN suppliers s ON sd.supplier_id = s.id
            ORDER BY sd.created_at DESC
        """)

    def get_by_id(self, debt_id: int):
        return self.db.fetchone(
            "SELECT * FROM supplier_debts WHERE id = ?", (debt_id,)
        )

    def get_items(self, debt_id: int):
        return self.db.fetchall(
            "SELECT * FROM supplier_debt_items WHERE supplier_debt_id = ?", (debt_id,)
        )

    def get_payments(self, debt_id: int):
        return self.db.fetchall(
            "SELECT * FROM supplier_debt_payments WHERE supplier_debt_id = ? ORDER BY payment_date",
            (debt_id,),
        )

    def get_total_pending(self):
        rows = self.db.fetchall(
            "SELECT remaining_amount FROM supplier_debts WHERE status != 'paid'"
        )
        total = DECIMAL_ZERO
        for r in rows:
            total += to_decimal(r["remaining_amount"])
        return total

    def search(self, query: str):
        return self.db.fetchall("""
            SELECT sd.*, s.name as supplier_name, s.phone as supplier_phone
            FROM supplier_debts sd
            JOIN suppliers s ON sd.supplier_id = s.id
            WHERE s.name LIKE ? OR sd.invoice_number LIKE ?
            ORDER BY sd.created_at DESC
        """, (f"%{query}%", f"%{query}%"))

    # ─── إنشاء فاتورة مجمعة ───
    def create_bulk_invoice(self, supplier_id: int, items: list,
                            invoice_total: float = 0.0,
                            paid_amount: float = 0.0,
                            invoice_number: str = "",
                            notes: str = "") -> int:
        """
        invoice_total : الإجمالي الذي كتبه المستخدم في الفاتورة
        paid_amount   : المبلغ المسدد
        المتبقي       = invoice_total - paid_amount  (يُسجَّل كدين)
        items: list of dicts {name, scientific_name, category_id, barcode,
                               quantity, unit_price, total_price, expiry_date,
                               min_stock}
        """
        total     = float(invoice_total)
        paid      = float(paid_amount)
        remaining = max(total - paid, 0.0)
        status    = "paid" if remaining <= 0 else ("partial" if paid > 0 else "pending")

        self.db.execute("""
            INSERT INTO supplier_debts
                (supplier_id, invoice_number, total_amount, paid_amount,
                 remaining_amount, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (supplier_id, invoice_number, total, paid, remaining, status, notes))
        debt_id = self.db.fetchone("SELECT last_insert_rowid() as id")["id"]

        for it in items:
            self.db.execute("""
                INSERT INTO supplier_debt_items
                    (supplier_debt_id, barcode, name, scientific_name,
                     category_id, quantity, unit_price, total_price,
                     expiry_date, min_stock)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                debt_id,
                it.get("barcode", ""),
                it.get("name", ""),
                it.get("scientific_name", ""),
                it.get("category_id"),
                int(it.get("quantity", 0)),
                float(it.get("unit_price", 0)),
                float(it.get("total_price", 0)),
                it.get("expiry_date", ""),
                int(it.get("min_stock", 10)),
            ))

            # ── تحديث المخزون تلقائياً (منطق الوجبات) ──
            barcode = it.get("barcode", "").strip()
            if barcode:
                existing_list = self.db.fetchall(
                    "SELECT id, stock_quantity, name FROM products WHERE barcode = ? AND is_active = 1 ORDER BY id",
                    (barcode,)
                )
                if existing_list:
                    total_stock = sum(e["stock_quantity"] or 0 for e in existing_list)
                    if total_stock == 0:
                        # إذا كانت الوجبة الأولى (أو كل السابقة) رصيدها صفر، قم بتحديث أول وجبة
                        first_id = existing_list[0]["id"]
                        self.db.execute(
                            "UPDATE products SET stock_quantity=?, purchase_price=?, sale_price=?, expiry_date=?, strips_per_pack=?, pieces_per_strip=? WHERE id=?",
                            (
                                int(it.get("quantity", 0)),
                                float(it.get("unit_price", 0)),
                                float(it.get("unit_price", 0)),
                                it.get("expiry_date", ""),
                                int(it.get("strips_per_pack", 1)),
                                int(it.get("pieces_per_strip", 1)),
                                first_id
                            )
                        )
                    else:
                        # إذا كان هناك رصيد موجود لنفس الباركود، ننشئ وجبة جديدة
                        batch_num = len(existing_list) + 1
                        new_name = it.get("name", "")
                        if "وجبة" not in new_name:
                            new_name = f"{new_name} - وجبة {batch_num}"

                        sale_price = float(it.get("sale_price", 0)) or float(it.get("unit_price", 0)) * 1.2

                        self.db.execute("""
                            INSERT INTO products
                                (barcode, name, scientific_name, category_id, supplier_id,
                                 sale_price, purchase_price, stock_quantity, min_stock,
                                 expiry_date, strips_per_pack, pieces_per_strip, is_active)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                        """, (
                            barcode,
                            new_name,
                            it.get("scientific_name", ""),
                            it.get("category_id"),
                            supplier_id,
                            sale_price,
                            float(it.get("unit_price", 0)),
                            int(it.get("quantity", 0)),
                            int(it.get("min_stock", 10)),
                            it.get("expiry_date", ""),
                            int(it.get("strips_per_pack", 1)),
                            int(it.get("pieces_per_strip", 1)),
                        ))
                else:
                    sale_price = float(it.get("sale_price", 0)) or float(it.get("unit_price", 0)) * 1.2
                    self.db.execute("""
                        INSERT INTO products
                            (barcode, name, scientific_name, category_id, supplier_id,
                             sale_price, purchase_price, stock_quantity, min_stock,
                             expiry_date, strips_per_pack, pieces_per_strip, is_active)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                    """, (
                        barcode,
                        it.get("name", ""),
                        it.get("scientific_name", ""),
                        it.get("category_id"),
                        supplier_id,
                        sale_price,
                        float(it.get("unit_price", 0)),
                        int(it.get("quantity", 0)),
                        int(it.get("min_stock", 10)),
                        it.get("expiry_date", ""),
                        int(it.get("strips_per_pack", 1)),
                        int(it.get("pieces_per_strip", 1)),
                    ))

            # ── حذف تلقائي من الطلبية (في الخلفية) ──
            try:
                product_name = it.get("name", "").strip()
                if product_name:
                    OrderController().remove_by_name(product_name)
            except Exception:
                pass  # لا نريد أن يؤثر أي خطأ على عملية الشراء

        return debt_id


    # ─── تسديد دفعة ───
    def add_payment(self, debt_id: int, amount: float, notes: str = ""):
        debt = self.db.fetchone(
            "SELECT * FROM supplier_debts WHERE id = ?", (debt_id,)
        )
        if not debt:
            raise ValueError("الفاتورة غير موجودة")

        amount_dec = to_decimal(str(amount))
        paid_dec = to_decimal(str(debt["paid_amount"]))
        total_dec = to_decimal(str(debt["total_amount"]))
        new_paid = paid_dec + amount_dec
        remaining = total_dec - new_paid
        status = "paid" if remaining <= DECIMAL_ZERO else "partial"

        self.db.execute(
            "INSERT INTO supplier_debt_payments (supplier_debt_id, amount, notes) VALUES (?, ?, ?)",
            (debt_id, float(amount_dec), notes),
        )
        self.db.execute(
            """UPDATE supplier_debts
               SET paid_amount=?, remaining_amount=?, status=?
               WHERE id=?""",
            (float(new_paid), float(max(remaining, DECIMAL_ZERO)), status, debt_id),
        )
