from database.connection import DatabaseManager


class SupplierController:
    def __init__(self):
        self.db = DatabaseManager()

    def search(self, query: str):
        return self.db.fetchall(
            "SELECT * FROM suppliers WHERE name LIKE ? OR phone LIKE ? ORDER BY name LIMIT 20",
            (f"%{query}%", f"%{query}%"),
        )

    def get_all(self):
        return self.db.fetchall("SELECT * FROM suppliers ORDER BY name")

    def create(self, data: dict):
        self.db.execute(
            "INSERT INTO suppliers (name, phone, address, notes) VALUES (?, ?, ?, ?)",
            (data["name"], data.get("phone"), data.get("address"), data.get("notes")),
        )
        return self.db.fetchone("SELECT last_insert_rowid() as id")["id"]

    def update(self, supplier_id: int, data: dict):
        fields = []
        values = []
        for key, value in data.items():
            fields.append(f"{key} = ?")
            values.append(value)
        values.append(supplier_id)
        self.db.execute(
            f"UPDATE suppliers SET {', '.join(fields)} WHERE id = ?", tuple(values)
        )
