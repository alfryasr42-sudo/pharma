from database.connection import DatabaseManager
from utils.decimal_handler import from_decimal, to_decimal


class ProductController:
    def __init__(self):
        self.db = DatabaseManager()

    def search_by_barcode(self, barcode: str):
        return self.db.fetchone(
            "SELECT * FROM products WHERE barcode = ? AND is_active = 1", (barcode,)
        )

    def search_by_name(self, query: str):
        return self.db.fetchall(
            "SELECT * FROM products WHERE name LIKE ? AND is_active = 1 ORDER BY name LIMIT 20",
            (f"%{query}%",),
        )

    def get_all(self):
        return self.db.fetchall(
            """SELECT p.*, c.name as category_name, s.name as supplier_name
               FROM products p
               LEFT JOIN categories c ON p.category_id = c.id
               LEFT JOIN suppliers s ON p.supplier_id = s.id
               WHERE p.is_active = 1
               ORDER BY p.name"""
        )

    def get_low_stock(self):
        return self.db.fetchall(
            "SELECT * FROM products WHERE stock_quantity <= min_stock AND is_active = 1"
        )

    def get_by_id(self, product_id: int):
        return self.db.fetchone("SELECT * FROM products WHERE id = ?", (product_id,))

    def create(self, data: dict):
        self.db.execute(
            """INSERT INTO products
               (barcode, name, scientific_name, category_id, supplier_id,
                sale_price, purchase_price, stock_quantity, min_stock, expiry_date,
                strips_per_pack, pieces_per_strip, is_barcoded)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data["barcode"], data["name"], data.get("scientific_name"),
                data.get("category_id"), data.get("supplier_id"),
                from_decimal(data["sale_price"]), from_decimal(data["purchase_price"]),
                data.get("stock_quantity", 0), data.get("min_stock", 10),
                data.get("expiry_date"),
                data.get("strips_per_pack", 1), data.get("pieces_per_strip", 1),
                data.get("is_barcoded", 1),
            ),
        )
        return self.db.fetchone("SELECT last_insert_rowid() as id")["id"]

    def update(self, product_id: int, data: dict):
        values = []
        fields = []
        for key, value in data.items():
            fields.append(f"{key} = ?")
            if key in ("sale_price", "purchase_price"):
                values.append(from_decimal(value))
            else:
                values.append(value)
        values.append(product_id)
        self.db.execute(
            f"UPDATE products SET {', '.join(fields)} WHERE id = ?", tuple(values)
        )

    def update_stock(self, product_id: int, quantity_change: int):
        self.db.execute(
            "UPDATE products SET stock_quantity = stock_quantity + ? WHERE id = ?",
            (quantity_change, product_id),
        )

    def delete(self, product_id: int):
        self.db.execute(
            "UPDATE products SET is_active = 0 WHERE id = ?", (product_id,)
        )
