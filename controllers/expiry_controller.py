from database.connection import DatabaseManager
from utils.decimal_handler import format_currency
from datetime import datetime, date


class ExpiryController:
    def __init__(self):
        self.db = DatabaseManager()

    def get_expiring_soon(self, days: int = 90):
        cutoff = date.today()
        end = date.today()
        try:
            from datetime import timedelta
            end = cutoff + timedelta(days=days)
        except Exception:
            end = cutoff
        return self.db.fetchall(
            """SELECT * FROM products
               WHERE expiry_date IS NOT NULL
               AND expiry_date != ''
               AND expiry_date BETWEEN ? AND ?
               AND is_active = 1
               ORDER BY expiry_date ASC""",
            (cutoff.isoformat(), end.isoformat()),
        )

    def get_expired(self):
        today = date.today().isoformat()
        return self.db.fetchall(
            """SELECT * FROM products
               WHERE expiry_date IS NOT NULL
               AND expiry_date != ''
               AND expiry_date < ?
               AND is_active = 1
               ORDER BY expiry_date ASC""",
            (today,),
        )

    def format_expiry_alerts(self, products: list) -> str:
        if not products:
            return ""
        lines = []
        for p in products:
            lines.append(
                f"• {p['name']} - تاريخ الصلاحية: {p['expiry_date']} - الكمية: {p['stock_quantity']}"
            )
        return "\n".join(lines)
