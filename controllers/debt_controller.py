from database.connection import DatabaseManager
from utils.decimal_handler import to_decimal, from_decimal, DECIMAL_ZERO
from controllers.accounting_controller import AccountingController


class DebtController:
    def __init__(self):
        self.db = DatabaseManager()
        self.acct = AccountingController()

    def get_all_pending(self):
        return self.db.fetchall(
            """SELECT d.*, c.name as customer_name, c.phone as customer_phone
               FROM debts d
               JOIN customers c ON d.customer_id = c.id
               WHERE d.status IN ('pending', 'partial')
               ORDER BY d.created_at DESC"""
        )

    def get_by_customer(self, customer_id: int):
        return self.db.fetchall(
            "SELECT * FROM debts WHERE customer_id = ? ORDER BY created_at DESC",
            (customer_id,),
        )

    def get_payments(self, debt_id: int):
        return self.db.fetchall(
            "SELECT * FROM debt_payments WHERE debt_id = ? ORDER BY payment_date",
            (debt_id,),
        )

    def add_payment(self, debt_id: int, amount: str, notes: str = ""):
        debt = self.db.fetchone("SELECT * FROM debts WHERE id = ?", (debt_id,))
        if not debt:
            raise ValueError("الديون غير موجودة")

        amount_dec = to_decimal(amount)
        paid_dec = to_decimal(debt["paid_amount"])
        total_dec = to_decimal(debt["amount"])
        new_paid = paid_dec + amount_dec
        remaining = total_dec - new_paid
        status = "paid" if remaining <= DECIMAL_ZERO else "partial"

        self.db.execute(
            "INSERT INTO debt_payments (debt_id, amount, notes) VALUES (?, ?, ?)",
            (debt_id, from_decimal(amount_dec), notes),
        )
        self.db.execute(
            "UPDATE debts SET paid_amount = ?, remaining_amount = ?, status = ? WHERE id = ?",
            (from_decimal(new_paid), from_decimal(max(remaining, DECIMAL_ZERO)), status, debt_id),
        )
        self.db.execute(
            "UPDATE customers SET total_debt = printf('%.2f', CAST(total_debt AS REAL) - ?) WHERE id = ?",
            (from_decimal(amount_dec), debt["customer_id"]),
        )

        self.acct.record_payment_transaction(
            debt_id, debt["customer_id"], from_decimal(amount_dec), debt["sale_id"] if debt["sale_id"] else None
        )

        return debt["customer_id"]

    def get_total_pending(self):
        rows = self.db.fetchall(
            "SELECT remaining_amount FROM debts WHERE status != 'paid'"
        )
        total = DECIMAL_ZERO
        for row in rows:
            total += to_decimal(row["remaining_amount"])
        return total
