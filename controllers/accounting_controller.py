from database.connection import DatabaseManager
from utils.decimal_handler import to_decimal, from_decimal, DECIMAL_ZERO
from datetime import date


class AccountingController:
    def __init__(self):
        self.db = DatabaseManager()

    def get_account_by_code(self, code: str):
        return self.db.fetchone("SELECT * FROM accounts WHERE code = ?", (code,))

    def post_entry(self, entry_date: str, ref_type: str, ref_id: int,
                   description: str, lines: list):
        cursor = self.db.execute(
            """INSERT INTO journal_entries
               (entry_date, reference_type, reference_id, description)
               VALUES (?, ?, ?, ?)""",
            (entry_date, ref_type, ref_id, description),
        )
        journal_id = cursor.lastrowid

        for line in lines:
            self.db.execute(
                "INSERT INTO journal_lines (journal_id, account_id, debit, credit) VALUES (?, ?, ?, ?)",
                (journal_id, line["account_id"],
                 from_decimal(line.get("debit", DECIMAL_ZERO)),
                 from_decimal(line.get("credit", DECIMAL_ZERO))),
            )
            acct = self.db.fetchone("SELECT * FROM accounts WHERE id = ?", (line["account_id"],))
            if acct:
                balance = to_decimal(acct["balance"])
                debit = to_decimal(line.get("debit", DECIMAL_ZERO))
                credit = to_decimal(line.get("credit", DECIMAL_ZERO))
                if acct["type"] in ("asset", "expense"):
                    balance += debit - credit
                else:
                    balance += credit - debit
                self.db.execute(
                    "UPDATE accounts SET balance = ? WHERE id = ?",
                    (from_decimal(balance), line["account_id"]),
                )

        return journal_id

    def record_sale_transaction(self, sale_id: int, total_amount: str,
                                 paid_amount: str, payment_method: str):
        today = date.today().isoformat()

        cash_acct = self.get_account_by_code("1001")
        receivable_acct = self.get_account_by_code("1002")
        revenue_acct = self.get_account_by_code("4001")
        total = to_decimal(total_amount)
        paid = to_decimal(paid_amount)

        if payment_method == "credit":
            lines = [
                {"account_id": receivable_acct["id"], "debit": from_decimal(total), "credit": "0.00"},
                {"account_id": revenue_acct["id"], "debit": "0.00", "credit": from_decimal(total)},
            ]
        else:
            lines = [
                {"account_id": cash_acct["id"], "debit": from_decimal(paid), "credit": "0.00"},
                {"account_id": revenue_acct["id"], "debit": "0.00", "credit": from_decimal(total)},
            ]
            if paid < total:
                remaining = total - paid
                lines.append({
                    "account_id": receivable_acct["id"],
                    "debit": from_decimal(remaining), "credit": "0.00",
                })

        return self.post_entry(today, "sale", sale_id, f"فاتورة مبيعات #{sale_id}", lines)

    def record_payment_transaction(self, debt_id: int, customer_id: int,
                                    amount: str, sale_id: int = None):
        today = date.today().isoformat()
        cash_acct = self.get_account_by_code("1001")
        receivable_acct = self.get_account_by_code("1002")

        lines = [
            {"account_id": cash_acct["id"], "debit": from_decimal(to_decimal(amount)), "credit": "0.00"},
            {"account_id": receivable_acct["id"], "debit": "0.00", "credit": from_decimal(to_decimal(amount))},
        ]

        ref_id = sale_id or debt_id
        return self.post_entry(today, "payment", ref_id, f"دفعة دين #{debt_id}", lines)

    def get_account_balance(self, account_code: str):
        acct = self.get_account_by_code(account_code)
        if not acct:
            return DECIMAL_ZERO
        return to_decimal(acct["balance"])

    def get_trial_balance(self):
        return self.db.fetchall(
            "SELECT code, name, type, balance FROM accounts ORDER BY code"
        )
