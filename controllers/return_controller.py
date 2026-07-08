from database.connection import DatabaseManager
from utils.decimal_handler import to_decimal, from_decimal, DECIMAL_ZERO
from controllers.accounting_controller import AccountingController
from datetime import date


class ReturnController:
    def __init__(self):
        self.db = DatabaseManager()
        self.acct = AccountingController()

    def create_return(self, sale_id: int, user_id: int, items: list, reason: str = "") -> int:
        """
        items: list of dicts with keys:
            sale_item_id, product_id, quantity, unit_price, total_price
        """
        total_returned = sum_decimals(item["total_price"] for item in items)

        self.db.execute(
            """INSERT INTO return_transactions (sale_id, user_id, reason, total_returned)
               VALUES (?, ?, ?, ?)""",
            (sale_id, user_id, reason, from_decimal(total_returned)),
        )
        return_id = self.db.fetchone("SELECT last_insert_rowid()")[0]

        for item in items:
            self.db.execute(
                """INSERT INTO return_items (return_id, sale_item_id, product_id, quantity, unit_price, total_price)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (return_id, item["sale_item_id"], item["product_id"],
                 item["quantity"], from_decimal(item["unit_price"]),
                 from_decimal(item["total_price"])),
            )

        self._reverse_stock(items)
        self._reverse_accounting(sale_id, items, total_returned)
        self._reverse_debts(sale_id, items)
        self._reverse_doctor_rewards(sale_id, items)

        return return_id

    def _reverse_stock(self, items: list):
        for item in items:
            prod = self.db.fetchone(
                "SELECT sale_price, strips_per_pack FROM products WHERE id = ?",
                (item["product_id"],),
            )
            if prod:
                sp = to_decimal(prod["sale_price"])
                if sp:
                    strip_eq = int(to_decimal(item["total_price"]) / sp)
                else:
                    strip_eq = int(item["quantity"])
            else:
                strip_eq = int(item["quantity"])
            self.db.execute(
                "UPDATE products SET stock_quantity = stock_quantity + ? WHERE id = ?",
                (max(strip_eq, 0), item["product_id"]),
            )

    def _reverse_accounting(self, sale_id: int, items: list, total_returned):
        sale = self.db.fetchone("SELECT * FROM sales WHERE id = ?", (sale_id,))
        if not sale:
            return
        payment_method = sale["payment_method"]
        total_amount = to_decimal(sale["total_amount"])
        paid_amount = to_decimal(sale["paid_amount"])

        cash_acct = self.acct.get_account_by_code("1001")
        receivable_acct = self.acct.get_account_by_code("1002")
        revenue_acct = self.acct.get_account_by_code("4001")

        today = date.today().isoformat()
        returned = total_returned
        prorated_return = min(returned, paid_amount) if payment_method != "credit" else returned

        # Reverse: credit cash/ receivable, debit revenue
        if payment_method == "credit":
            lines = [
                {"account_id": revenue_acct["id"], "debit": from_decimal(returned), "credit": "0.00"},
                {"account_id": receivable_acct["id"], "debit": "0.00", "credit": from_decimal(returned)},
            ]
        else:
            lines = [
                {"account_id": revenue_acct["id"], "debit": from_decimal(returned), "credit": "0.00"},
                {"account_id": cash_acct["id"], "debit": "0.00", "credit": from_decimal(prorated_return)},
            ]
            if prorated_return < returned:
                remaining = returned - prorated_return
                lines.append({
                    "account_id": receivable_acct["id"],
                    "debit": "0.00", "credit": from_decimal(remaining),
                })

        self.acct.post_entry(today, "return", sale_id, f"مرتجع فاتورة #{sale_id}", lines)

    def _reverse_debts(self, sale_id: int, items: list):
        debt = self.db.fetchone("SELECT * FROM debts WHERE sale_id = ?", (sale_id,))
        if not debt:
            return
        total_returned = sum_decimals(item["total_price"] for item in items)
        returned = total_returned
        current_remaining = to_decimal(debt["remaining_amount"])
        current_paid = to_decimal(debt["paid_amount"])
        current_amount = to_decimal(debt["amount"])

        new_amount = max(current_amount - returned, DECIMAL_ZERO)
        new_remaining = max(current_remaining - returned, DECIMAL_ZERO)
        new_paid = current_paid
        status = debt["status"]
        if new_amount <= DECIMAL_ZERO:
            status = "paid"
        elif new_remaining <= DECIMAL_ZERO:
            status = "paid"
        elif new_remaining >= new_amount:
            status = "pending"
        else:
            status = "partial"

        self.db.execute(
            """UPDATE debts SET amount=?, paid_amount=?, remaining_amount=?, status=?
               WHERE id=?""",
            (from_decimal(new_amount), from_decimal(new_paid),
             from_decimal(new_remaining), status, debt["id"]),
        )

        customer = self.db.fetchone(
            "SELECT * FROM customers WHERE id = ?", (debt["customer_id"],)
        )
        if customer:
            current_total = to_decimal(customer["total_debt"])
            new_total = max(current_total - returned, DECIMAL_ZERO)
            self.db.execute(
                "UPDATE customers SET total_debt=? WHERE id=?",
                (from_decimal(new_total), debt["customer_id"]),
            )

    def _reverse_doctor_rewards(self, sale_id: int, items: list):
        product_ids = [item["product_id"] for item in items]
        for pid in product_ids:
            self.db.execute(
                "DELETE FROM doctor_rewards WHERE sale_id=? AND product_id=?",
                (sale_id, pid),
            )

    def get_return_by_id(self, return_id: int):
        return self.db.fetchone(
            "SELECT * FROM return_transactions WHERE id = ?", (return_id,)
        )

    def get_returns_for_sale(self, sale_id: int):
        return self.db.fetchall(
            "SELECT * FROM return_transactions WHERE sale_id = ? ORDER BY created_at DESC",
            (sale_id,),
        )

    def get_return_items(self, return_id: int):
        return self.db.fetchall(
            "SELECT * FROM return_items WHERE return_id = ?", (return_id,)
        )


def sum_decimals(values):
    return sum(to_decimal(v) if not isinstance(v, str) else to_decimal(v) for v in values)
