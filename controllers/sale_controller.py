from database.connection import DatabaseManager
from utils.helpers import generate_invoice_number
from utils.decimal_handler import (
    from_decimal, to_decimal, sum_decimals,
    DECIMAL_ZERO
)
from controllers.accounting_controller import AccountingController
from controllers.doctor_controller import DoctorController


class SaleController:
    def __init__(self):
        self.db = DatabaseManager()
        self.acct = AccountingController()
        self.doc_ctrl = DoctorController()

    def create_sale(self, user_id: int, items: list, discount: str = "0.00",
                    customer_id: int = None, payment_method: str = "cash",
                    paid_amount: str = None, doctor_id: int = None) -> int:
        invoice_number = generate_invoice_number()
        total = sum_decimals(item["total_price"] for item in items)
        discount_dec = to_decimal(discount)
        discount_amt = (total * discount_dec / to_decimal("100")).quantize(
            to_decimal("0.01"))
        net_total = total - discount_amt
        paid = to_decimal(paid_amount) if paid_amount else net_total

        cursor = self.db.execute(
            """INSERT INTO sales
               (invoice_number, user_id, customer_id, total_amount, discount, paid_amount, payment_method)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (invoice_number, user_id, customer_id,
             from_decimal(net_total), from_decimal(discount_amt),
             from_decimal(paid), payment_method),
        )
        sale_id = cursor.lastrowid

        for item in items:
            cursor2 = self.db.execute(
                "INSERT INTO sale_items (sale_id, product_id, quantity, unit_price, total_price) VALUES (?, ?, ?, ?, ?)",
                (sale_id, item["product_id"], item["quantity"],
                 from_decimal(item["unit_price"]), from_decimal(item["total_price"])),
            )
            sale_item_id = cursor2.lastrowid
            self.db.execute(
                "UPDATE products SET stock_quantity = stock_quantity - ? WHERE id = ?",
                (item["quantity"], item["product_id"]),
            )

            product = self.db.fetchone(
                "SELECT category_id FROM products WHERE id = ?", (item["product_id"],)
            )
            if product:
                reward = None
                # Calculate the effective total price for this item after the global invoice discount
                item_total = to_decimal(item["total_price"])
                effective_total = item_total
                if total > DECIMAL_ZERO:
                    # Proportion of this item's total to the invoice total
                    proportion = item_total / total
                    item_discount = discount_amt * proportion
                    effective_total = item_total - item_discount

                if doctor_id:
                    reward = self.doc_ctrl.calculate_reward_for_doctor(
                        doctor_id, item["product_id"], from_decimal(effective_total), product["category_id"]
                    )
                else:
                    reward = self.doc_ctrl.calculate_reward(
                        item["product_id"], from_decimal(effective_total), product["category_id"]
                    )
                if reward:
                    # If the reward was based on a percentage rule, it already used effective_total.
                    # If it was a fixed amount rule, calculate_reward evaluated it for a single unit. 
                    # We must multiply fixed amounts by quantity.
                    reward_val = to_decimal(reward["reward_value"])
                    if reward["reward_type"] != "percentage":
                        reward_val = reward_val * to_decimal(item["quantity"])
                        
                    self.doc_ctrl.record_reward(
                        sale_id, sale_item_id, item["product_id"],
                        reward["doctor_id"], reward["reward_type"],
                        from_decimal(reward_val),
                        modified_price=reward.get("modified_price", "0.00"),
                        original_price=reward.get("original_price", "0.00"),
                        doctor_share=from_decimal(reward_val),
                    )

        if payment_method == "credit" and customer_id:
            remaining = net_total - paid
            if remaining > DECIMAL_ZERO:
                self.db.execute(
                    """INSERT INTO debts (sale_id, customer_id, amount, paid_amount, remaining_amount, status)
                       VALUES (?, ?, ?, ?, ?, 'pending')""",
                    (sale_id, customer_id,
                     from_decimal(net_total), from_decimal(paid),
                     from_decimal(remaining)),
                )
                self.db.execute(
                    "UPDATE customers SET total_debt = printf('%.2f', CAST(total_debt AS REAL) + ?) WHERE id = ?",
                    (from_decimal(remaining), customer_id),
                )

        self.acct.record_sale_transaction(
            sale_id, from_decimal(net_total), from_decimal(paid), payment_method
        )

        return sale_id

    def get_sale_by_id(self, sale_id: int):
        return self.db.fetchone("SELECT * FROM sales WHERE id = ?", (sale_id,))

    def get_sale_items(self, sale_id: int):
        return self.db.fetchall(
            """SELECT si.*, p.name as product_name, p.barcode
               FROM sale_items si
               JOIN products p ON si.product_id = p.id
               WHERE si.sale_id = ?""",
            (sale_id,),
        )

    def get_today_sales(self):
        return self.db.fetchall(
            "SELECT * FROM sales WHERE date(created_at) = date('now') ORDER BY created_at DESC"
        )

    def search_sales(self, query: str):
        return self.db.fetchall(
            """SELECT s.*, u.full_name as user_name
               FROM sales s
               LEFT JOIN users u ON s.user_id = u.id
               WHERE s.invoice_number LIKE ? OR s.id = ?
               ORDER BY s.created_at DESC LIMIT 50""",
            (f"%{query}%", int(query) if query.isdigit() else -1),
        )

    def get_sales_report(self, start_date: str, end_date: str):
        return self.db.fetchall(
            "SELECT * FROM sales WHERE date(created_at) BETWEEN ? AND ? ORDER BY created_at",
            (start_date, end_date),
        )
