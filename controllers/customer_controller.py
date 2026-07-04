from database.connection import DatabaseManager


class CustomerController:
    def __init__(self):
        self.db = DatabaseManager()

    def search(self, query: str):
        return self.db.fetchall(
            "SELECT * FROM customers WHERE name LIKE ? OR phone LIKE ? ORDER BY name LIMIT 20",
            (f"%{query}%", f"%{query}%"),
        )

    def get_by_id(self, customer_id: int):
        return self.db.fetchone("SELECT * FROM customers WHERE id = ?", (customer_id,))

    def get_by_phone(self, phone: str):
        return self.db.fetchone("SELECT * FROM customers WHERE phone = ?", (phone,))

    def get_all(self):
        return self.db.fetchall("SELECT * FROM customers ORDER BY name")

    def create(self, data: dict):
        self.db.execute(
            "INSERT INTO customers (name, phone, address) VALUES (?, ?, ?)",
            (data["name"], data.get("phone"), data.get("address")),
        )
        return self.db.fetchone("SELECT last_insert_rowid() as id")["id"]

    def update(self, customer_id: int, data: dict):
        fields = []
        values = []
        for key, value in data.items():
            fields.append(f"{key} = ?")
            values.append(value)
        values.append(customer_id)
        self.db.execute(
            f"UPDATE customers SET {', '.join(fields)} WHERE id = ?", tuple(values)
        )

    def get_debts(self, customer_id: int):
        return self.db.fetchall(
            "SELECT * FROM debts WHERE customer_id = ? AND status != 'paid' ORDER BY created_at DESC",
            (customer_id,),
        )

    def get_debt_history(self, customer_id: int):
        return self.db.fetchall(
            """SELECT d.*, dp.amount as payment_amount, dp.payment_date, dp.notes as payment_notes
               FROM debts d
               LEFT JOIN debt_payments dp ON d.id = dp.debt_id
               WHERE d.customer_id = ?
               ORDER BY d.created_at DESC""",
            (customer_id,),
        )
