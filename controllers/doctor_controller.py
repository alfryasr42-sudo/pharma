from database.connection import DatabaseManager
from utils.decimal_handler import to_decimal, from_decimal, DECIMAL_ZERO


class DoctorController:
    def __init__(self):
        self.db = DatabaseManager()

    def get_all(self):
        return self.db.fetchall(
            "SELECT * FROM doctors WHERE is_active = 1 ORDER BY name"
        )

    def get_doctors_with_rules(self):
        return self.db.fetchall(
            """SELECT DISTINCT d.* FROM doctors d
               INNER JOIN doctor_reward_rules r ON d.id = r.doctor_id
               WHERE d.is_active = 1 AND r.is_active = 1
               ORDER BY d.name"""
        )

    def search(self, query: str):
        return self.db.fetchall(
            "SELECT * FROM doctors WHERE name LIKE ? AND is_active = 1 ORDER BY name LIMIT 20",
            (f"%{query}%",),
        )

    def get_by_id(self, doctor_id: int):
        return self.db.fetchone("SELECT * FROM doctors WHERE id = ?", (doctor_id,))

    def create(self, data: dict):
        self.db.execute(
            "INSERT INTO doctors (name, phone, specialization, commission_rate) VALUES (?, ?, ?, ?)",
            (data["name"], data.get("phone"), data.get("specialization"),
             from_decimal(to_decimal(data.get("commission_rate", 0)))),
        )
        return self.db.fetchone("SELECT last_insert_rowid() as id")["id"]

    def update(self, doctor_id: int, data: dict):
        fields = []
        values = []
        for key, value in data.items():
            fields.append(f"{key} = ?")
            values.append(value)
        values.append(doctor_id)
        self.db.execute(
            f"UPDATE doctors SET {', '.join(fields)} WHERE id = ?", tuple(values)
        )

    def get_reward_rules(self, doctor_id: int = None):
        if doctor_id:
            return self.db.fetchall(
                """SELECT r.*, r.deal_type, p.name as product_name, c.name as category_name
                   FROM doctor_reward_rules r
                   LEFT JOIN products p ON r.product_id = p.id
                   LEFT JOIN categories c ON r.category_id = c.id
                   WHERE r.doctor_id = ? AND r.is_active = 1
                   ORDER BY r.id""",
                (doctor_id,),
            )
        return self.db.fetchall(
            """SELECT r.*, r.deal_type, d.name as doctor_name, p.name as product_name, c.name as category_name
               FROM doctor_reward_rules r
               JOIN doctors d ON r.doctor_id = d.id
               LEFT JOIN products p ON r.product_id = p.id
               LEFT JOIN categories c ON r.category_id = c.id
               WHERE r.is_active = 1
               ORDER BY d.name"""
        )

    def add_rule(self, data: dict):
        deal_type = data.get("deal_type", "deal")
        self.db.execute(
            """INSERT INTO doctor_reward_rules
               (doctor_id, product_id, category_id, reward_type, reward_value, deal_type)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (data["doctor_id"], data.get("product_id"), data.get("category_id"),
             data["reward_type"], from_decimal(to_decimal(data["reward_value"])),
             deal_type),
        )

    def remove_rule(self, rule_id: int):
        self.db.execute("UPDATE doctor_reward_rules SET is_active = 0 WHERE id = ?", (rule_id,))

    def calculate_reward(self, product_id: int, sale_price: str, category_id: int = None):
        rules = self.db.fetchall(
            """SELECT * FROM doctor_reward_rules
               WHERE is_active = 1
               AND (product_id = ? OR (product_id IS NULL AND category_id = ?))
               ORDER BY product_id DESC LIMIT 1""",
            (product_id, category_id),
        )
        if not rules:
            return None
        rule = rules[0]
        price = to_decimal(sale_price)
        value = to_decimal(rule["reward_value"])
        if rule["reward_type"] == "percentage":
            reward = (price * value / to_decimal("100")).quantize(to_decimal("0.01"))
        else:
            reward = value
        return {
            "doctor_id": rule["doctor_id"],
            "reward_type": rule["reward_type"],
            "reward_value": from_decimal(reward),
            "rule_id": rule["id"],
        }

    def get_rules_for_product(self, product_id: int):
        """Get active reward rules for a specific product, joined with doctor names."""
        return self.db.fetchall(
            """SELECT r.*, d.name as doctor_name
               FROM doctor_reward_rules r
               JOIN doctors d ON r.doctor_id = d.id
               WHERE r.product_id = ? AND r.is_active = 1
               ORDER BY d.name""",
            (product_id,),
        )

    def set_product_rules(self, product_id: int, rules: list, default_deal_type: str = "deal"):
        """Replace all reward rules for a product with new ones.
        Each rule dict: {doctor_id, reward_value (percentage as str), deal_type}
        """
        self.db.execute(
            "UPDATE doctor_reward_rules SET is_active = 0 WHERE product_id = ?",
            (product_id,),
        )
        for rule in rules:
            self.db.execute(
                """INSERT INTO doctor_reward_rules
                   (doctor_id, product_id, reward_type, reward_value, deal_type)
                   VALUES (?, ?, 'percentage', ?, ?)""",
                (rule["doctor_id"], product_id,
                 from_decimal(to_decimal(rule["reward_value"])),
                 rule.get("deal_type", default_deal_type)),
            )

    def record_reward(self, sale_id: int, sale_item_id: int, product_id: int,
                      doctor_id: int, reward_type: str, reward_value: str,
                      modified_price: str = "0.00", original_price: str = "0.00",
                      doctor_share: str = "0.00"):
        self.db.execute(
            """INSERT INTO doctor_rewards
               (sale_id, sale_item_id, doctor_id, product_id, reward_type, reward_value,
                modified_price, original_price, doctor_share)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (sale_id, sale_item_id, doctor_id, product_id, reward_type, reward_value,
             from_decimal(to_decimal(modified_price)),
             from_decimal(to_decimal(original_price)),
             from_decimal(to_decimal(doctor_share))),
        )

    def get_rewards_for_sale(self, sale_id: int):
        return self.db.fetchall(
            """SELECT r.*, d.name as doctor_name, p.name as product_name
               FROM doctor_rewards r
               JOIN doctors d ON r.doctor_id = d.id
               LEFT JOIN products p ON r.product_id = p.id
               WHERE r.sale_id = ?
               ORDER BY r.id""",
            (sale_id,),
        )

    def calculate_reward_for_doctor(self, doctor_id: int, product_id: int, sale_price: str, category_id: int = None):
        # 1. Check if there is a specific rule for this doctor and product/category
        rule = self.db.fetchone(
            """SELECT * FROM doctor_reward_rules
               WHERE doctor_id = ? AND is_active = 1
               AND (product_id = ? OR (product_id IS NULL AND category_id = ?))
               ORDER BY product_id DESC LIMIT 1""",
            (doctor_id, product_id, category_id),
        )
        price = to_decimal(sale_price)
        if rule:
            rule_dict = dict(rule)
            deal_type = rule_dict.get("deal_type", "deal")
            value = to_decimal(rule["reward_value"])
            if rule["reward_type"] == "percentage":
                calc_amount = (price * value / to_decimal("100")).quantize(to_decimal("0.01"))
            else:
                calc_amount = value

            if deal_type == "deal":
                modified_price = price
                doctor_share = calc_amount
            else:  # discount
                modified_price = price - calc_amount
                doctor_share = DECIMAL_ZERO

            return {
                "doctor_id": doctor_id,
                "reward_type": rule["reward_type"],
                "reward_value": from_decimal(calc_amount),
                "rule_id": rule["id"],
                "deal_type": deal_type,
                "modified_price": from_decimal(modified_price),
                "original_price": from_decimal(price),
                "doctor_share": from_decimal(doctor_share),
            }
        
        # 2. If no rule, check if doctor has general commission_rate
        doctor = self.get_by_id(doctor_id)
        if doctor:
            doctor_dict = dict(doctor)
            comm_rate_str = doctor_dict.get("commission_rate")
            if comm_rate_str:
                comm_rate = to_decimal(comm_rate_str)
                if comm_rate > DECIMAL_ZERO:
                    reward = (price * comm_rate / to_decimal("100")).quantize(to_decimal("0.01"))
                    modified_price = price
                    return {
                        "doctor_id": doctor_id,
                        "reward_type": "percentage",
                        "reward_value": from_decimal(reward),
                        "rule_id": None,
                        "deal_type": "deal",
                        "modified_price": from_decimal(modified_price),
                        "original_price": from_decimal(price),
                        "doctor_share": from_decimal(reward),
                    }
        return None

    def get_doctor_earnings(self, doctor_id, start_date=None, end_date=None):
        """Returns list of reward records with sale info for a specific doctor."""
        query = """
            SELECT dr.sale_id, s.invoice_number, p.name as product_name,
                   dr.original_price, dr.modified_price, dr.doctor_share,
                   dr.created_at
            FROM doctor_rewards dr
            JOIN sales s ON dr.sale_id = s.id
            LEFT JOIN products p ON dr.product_id = p.id
            WHERE dr.doctor_id = ?
        """
        params = [doctor_id]
        if start_date:
            query += " AND date(dr.created_at) >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date(dr.created_at) <= ?"
            params.append(end_date)
        query += " ORDER BY dr.created_at DESC"
        return self.db.fetchall(query, tuple(params))

    def get_all_earnings_summary(self):
        """Returns summary per doctor: doctor_id, doctor_name, total_share, total_invoices.
        Only counts records where doctor_share > 0 (deals only)."""
        return self.db.fetchall(
            """SELECT dr.doctor_id, d.name as doctor_name,
                      SUM(CAST(dr.doctor_share AS REAL)) as total_share,
                      COUNT(DISTINCT dr.sale_id) as total_invoices
               FROM doctor_rewards dr
               JOIN doctors d ON dr.doctor_id = d.id
               WHERE CAST(dr.doctor_share AS REAL) > 0
               GROUP BY dr.doctor_id
               ORDER BY d.name"""
        )

    def get_doctor_products(self, doctor_id: int):
        """Returns all products that have active deal/discount rules for this doctor."""
        return self.db.fetchall(
            """SELECT p.id as product_id, p.name as product_name,
                      r.reward_value, r.deal_type, r.id as rule_id
               FROM doctor_reward_rules r
               JOIN products p ON r.product_id = p.id
               WHERE r.doctor_id = ? AND r.is_active = 1
               ORDER BY p.name""",
            (doctor_id,),
        )
