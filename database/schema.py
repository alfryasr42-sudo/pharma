from database.connection import DatabaseManager

SCHEMA_VERSION = 17


def get_current_version(db):
    row = db.fetchone("PRAGMA user_version")
    return row[0] if row else 0


def migrate(db):
    version = get_current_version(db)

    if version < 1:
        _create_initial_schema(db)
        version = 1

    if version < 2:
        _migrate_v1_to_v2(db)
        version = 2

    if version < 3:
        _migrate_v2_to_v3(db)
        version = 3

    if version < 4:
        _migrate_v3_to_v4(db)
        version = 4

    if version < 5:
        _migrate_v4_to_v5(db)
        version = 5

    if version < 6:
        _migrate_v5_to_v6(db)
        version = 6

    if version < 7:
        _migrate_v6_to_v7(db)
        version = 7

    if version < 8:
        _migrate_v7_to_v8(db)
        version = 8

    if version < 9:
        _migrate_v8_to_v9(db)
        version = 9

    if version < 10:
        _migrate_v9_to_v10(db)
        version = 10

    if version < 11:
        _migrate_v10_to_v11(db)
        version = 11

    if version < 12:
        _migrate_v11_to_v12(db)
        version = 12

    if version < 13:
        _migrate_v12_to_v13(db)
        version = 13

    if version < 14:
        _migrate_v13_to_v14(db)
        version = 14

    if version < 15:
        _migrate_v14_to_v15(db)
        version = 15

    if version < 16:
        _migrate_v15_to_v16(db)
        version = 16

    if version < 17:
        _migrate_v16_to_v17(db)
        version = 17

    db.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")


def _create_initial_schema(db):
    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'cashier',
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            address TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT UNIQUE,
            address TEXT,
            total_debt TEXT DEFAULT '0.00',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barcode TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            scientific_name TEXT,
            category_id INTEGER,
            supplier_id INTEGER,
            sale_price TEXT NOT NULL DEFAULT '0.00',
            purchase_price TEXT NOT NULL DEFAULT '0.00',
            stock_quantity INTEGER DEFAULT 0,
            min_stock INTEGER DEFAULT 10,
            expiry_date DATE,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories(id),
            FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_number TEXT UNIQUE NOT NULL,
            user_id INTEGER,
            customer_id INTEGER,
            total_amount TEXT NOT NULL DEFAULT '0.00',
            discount TEXT DEFAULT '0.00',
            paid_amount TEXT DEFAULT '0.00',
            payment_method TEXT DEFAULT 'cash',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS sale_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price TEXT NOT NULL,
            total_price TEXT NOT NULL,
            FOREIGN KEY (sale_id) REFERENCES sales(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_number TEXT UNIQUE NOT NULL,
            supplier_id INTEGER,
            user_id INTEGER,
            total_amount TEXT NOT NULL DEFAULT '0.00',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS purchase_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            purchase_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price TEXT NOT NULL,
            total_price TEXT NOT NULL,
            FOREIGN KEY (purchase_id) REFERENCES purchases(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS debts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER,
            customer_id INTEGER NOT NULL,
            amount TEXT NOT NULL DEFAULT '0.00',
            paid_amount TEXT DEFAULT '0.00',
            remaining_amount TEXT NOT NULL DEFAULT '0.00',
            status TEXT DEFAULT 'pending',
            due_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sale_id) REFERENCES sales(id),
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS debt_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            debt_id INTEGER NOT NULL,
            amount TEXT NOT NULL,
            payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT,
            FOREIGN KEY (debt_id) REFERENCES debts(id) ON DELETE CASCADE
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS held_invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            items_json TEXT NOT NULL,
            subtotal TEXT NOT NULL DEFAULT '0.00',
            discount TEXT NOT NULL DEFAULT '0.00',
            payment_method TEXT DEFAULT 'cash',
            customer_id INTEGER,
            customer_name TEXT,
            doctor_id INTEGER,
            doctor_name TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    db.execute("""
        CREATE INDEX IF NOT EXISTS idx_products_barcode ON products(barcode)
    """)
    db.execute("""
        CREATE INDEX IF NOT EXISTS idx_products_name ON products(name)
    """)
    db.execute("""
        CREATE INDEX IF NOT EXISTS idx_sales_created ON sales(created_at)
    """)
    db.execute("""
        CREATE INDEX IF NOT EXISTS idx_debts_customer ON debts(customer_id)
    """)

    _seed_default_data(db)


def _migrate_v1_to_v2(db):
    text_cols = {
        "customers": ["total_debt"],
        "products": ["sale_price", "purchase_price"],
        "sales": ["total_amount", "discount", "paid_amount"],
        "sale_items": ["unit_price", "total_price"],
        "purchases": ["total_amount"],
        "purchase_items": ["unit_price", "total_price"],
        "debts": ["amount", "paid_amount", "remaining_amount"],
        "debt_payments": ["amount"],
    }
    for table, cols in text_cols.items():
        for col in cols:
            db.execute(f"ALTER TABLE {table} RENAME COLUMN {col} TO {col}_old")
        for col in cols:
            db.execute(f"ALTER TABLE {table} ADD COLUMN {col} TEXT NOT NULL DEFAULT '0.00'")
            db.execute(f"UPDATE {table} SET {col} = printf('%.2f', {col}_old)")
        for col in cols:
            db.execute(f"ALTER TABLE {table} DROP COLUMN {col}_old")


def _migrate_v2_to_v3(db):
    db.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            balance TEXT DEFAULT '0.00',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS journal_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_date DATE NOT NULL,
            reference_type TEXT,
            reference_id INTEGER,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS journal_lines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            journal_id INTEGER NOT NULL,
            account_id INTEGER NOT NULL,
            debit TEXT DEFAULT '0.00',
            credit TEXT DEFAULT '0.00',
            FOREIGN KEY (journal_id) REFERENCES journal_entries(id) ON DELETE CASCADE,
            FOREIGN KEY (account_id) REFERENCES accounts(id)
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            specialization TEXT,
            commission_rate TEXT DEFAULT '0.00',
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS doctor_reward_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doctor_id INTEGER NOT NULL,
            product_id INTEGER,
            category_id INTEGER,
            reward_type TEXT NOT NULL,
            reward_value TEXT NOT NULL DEFAULT '0.00',
            is_active INTEGER DEFAULT 1,
            FOREIGN KEY (doctor_id) REFERENCES doctors(id),
            FOREIGN KEY (product_id) REFERENCES products(id),
            FOREIGN KEY (category_id) REFERENCES categories(id)
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS doctor_rewards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER NOT NULL,
            sale_item_id INTEGER,
            doctor_id INTEGER NOT NULL,
            product_id INTEGER,
            reward_type TEXT NOT NULL,
            reward_value TEXT NOT NULL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sale_id) REFERENCES sales(id),
            FOREIGN KEY (doctor_id) REFERENCES doctors(id)
        )
    """)

    db.execute("""
        CREATE INDEX IF NOT EXISTS idx_expiry ON products(expiry_date)
    """)
    db.execute("""
        CREATE INDEX IF NOT EXISTS idx_journal_ref ON journal_entries(reference_type, reference_id)
    """)
    db.execute("""
        CREATE INDEX IF NOT EXISTS idx_rewards_sale ON doctor_rewards(sale_id)
    """)

    _seed_accounts(db)


def _migrate_v3_to_v4(db):
    db.execute("""
        CREATE TABLE IF NOT EXISTS products_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barcode TEXT NOT NULL,
            name TEXT NOT NULL,
            scientific_name TEXT,
            category_id INTEGER,
            supplier_id INTEGER,
            sale_price TEXT NOT NULL DEFAULT '0.00',
            purchase_price TEXT NOT NULL DEFAULT '0.00',
            stock_quantity INTEGER DEFAULT 0,
            min_stock INTEGER DEFAULT 10,
            expiry_date DATE,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories(id),
            FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
        )
    """)
    db.execute("INSERT INTO products_new SELECT * FROM products")
    db.execute("DROP TABLE products")
    db.execute("ALTER TABLE products_new RENAME TO products")
    db.execute("CREATE INDEX IF NOT EXISTS idx_barcode ON products(barcode)")


def _migrate_v4_to_v5(db):
    """Add deal_type to reward rules and price tracking columns to rewards."""
    alter_statements = [
        "ALTER TABLE doctor_reward_rules ADD COLUMN deal_type TEXT DEFAULT 'deal'",
        "ALTER TABLE doctor_rewards ADD COLUMN modified_price TEXT DEFAULT '0.00'",
        "ALTER TABLE doctor_rewards ADD COLUMN original_price TEXT DEFAULT '0.00'",
        "ALTER TABLE doctor_rewards ADD COLUMN doctor_share TEXT DEFAULT '0.00'",
    ]
    for stmt in alter_statements:
        try:
            db.execute(stmt)
        except Exception:
            pass


def _migrate_v5_to_v6(db):
    """Add order_items table for pharmacy shortage tracking."""
    db.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            notes       TEXT,
            created_at  DATETIME DEFAULT (datetime('now','localtime'))
        )
    """)


def _migrate_v6_to_v7(db):
    """Add quantity, unit, and company to order_items."""
    try:
        db.execute("ALTER TABLE order_items ADD COLUMN quantity INTEGER DEFAULT 0")
        db.execute("ALTER TABLE order_items ADD COLUMN unit TEXT")
        db.execute("ALTER TABLE order_items ADD COLUMN company TEXT")
    except Exception:
        pass


def _migrate_v7_to_v8(db):
    """Add settings table for configurations like default printers."""
    db.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            setting_key TEXT PRIMARY KEY,
            setting_value TEXT
        )
    """)


def _seed_accounts(db):
    accounts = [
        ("1001", "صندوق النقدية", "asset"),
        ("1002", "حساب العملاء (مدينون)", "asset"),
        ("1003", "المخزون", "asset"),
        ("2001", "حساب الموردون (دائنون)", "liability"),
        ("3001", "رأس المال", "equity"),
        ("4001", "إيرادات المبيعات", "revenue"),
        ("4002", "إيرادات أخرى", "revenue"),
        ("5001", "تكلفة البضاعة المباعة", "expense"),
        ("5002", "مصروفات عمومية", "expense"),
    ]
    for code, name, atype in accounts:
        exists = db.fetchone("SELECT id FROM accounts WHERE code = ?", (code,))
        if not exists:
            db.execute(
                "INSERT INTO accounts (code, name, type) VALUES (?, ?, ?)",
                (code, name, atype),
            )


def _seed_default_data(db):
    from utils.auth import hash_password

    users = [
        ("admin", hash_password("admin123"), "مدير النظام", "admin"),
        ("cashier", hash_password("123456"), "كاشير", "cashier"),
        ("manager", hash_password("123456"), "مشرف", "manager"),
    ]
    for username, pw, name, role in users:
        exists = db.fetchone("SELECT id FROM users WHERE username = ?", (username,))
        if not exists:
            db.execute(
                "INSERT INTO users (username, password_hash, full_name, role) VALUES (?, ?, ?, ?)",
                (username, pw, name, role),
            )


def _migrate_v8_to_v9(db):
    """Add expenses table for tracking pharmacy daily expenses."""
    db.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount TEXT NOT NULL DEFAULT '0.00',
            description TEXT,
            expense_date DATE DEFAULT (date('now', 'localtime')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


def _migrate_v9_to_v10(db):
    """Add strips_per_pack, pieces_per_strip to products for 3-tier pricing."""
    try:
        db.execute("ALTER TABLE products ADD COLUMN strips_per_pack INTEGER DEFAULT 1")
    except Exception:
        pass
    try:
        db.execute("ALTER TABLE products ADD COLUMN pieces_per_strip INTEGER DEFAULT 1")
    except Exception:
        pass


def _migrate_v10_to_v11(db):
    """Add is_barcoded flag to products."""
    try:
        db.execute("ALTER TABLE products ADD COLUMN is_barcoded INTEGER DEFAULT 1")
    except Exception:
        pass


def _migrate_v11_to_v12(db):
    """Fix is_barcoded: NON- barcodes → 0, NULL → 1."""
    try:
        db.execute("UPDATE products SET is_barcoded = 0 WHERE barcode LIKE 'NON-%'")
    except Exception:
        pass
    try:
        db.execute("UPDATE products SET is_barcoded = 1 WHERE is_barcoded IS NULL")
    except Exception:
        pass


def _migrate_v12_to_v13(db):
    """Add expense_types table + income_date, user_name, expense_type_id to expenses."""
    db.execute("""
        CREATE TABLE IF NOT EXISTS expense_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    try:
        db.execute("ALTER TABLE expenses ADD COLUMN expense_type_id INTEGER REFERENCES expense_types(id)")
    except Exception:
        pass
    try:
        db.execute("ALTER TABLE expenses ADD COLUMN user_name TEXT")
    except Exception:
        pass
    try:
        db.execute("ALTER TABLE expenses ADD COLUMN income_date DATE")
    except Exception:
        pass


def _migrate_v13_to_v14(db):
    """Add expense_income_sources table for multi-day income deduction tracking."""
    db.execute("""
        CREATE TABLE IF NOT EXISTS expense_income_sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            expense_id INTEGER NOT NULL,
            income_date DATE NOT NULL,
            amount TEXT NOT NULL DEFAULT '0.00',
            FOREIGN KEY (expense_id) REFERENCES expenses(id) ON DELETE CASCADE
        )
    """)
    rows = db.fetchall("SELECT id, income_date, amount FROM expenses WHERE income_date IS NOT NULL")
    for r in rows:
        db.execute(
            "INSERT INTO expense_income_sources (expense_id, income_date, amount) VALUES (?, ?, ?)",
            (r["id"], r["income_date"], r["amount"]),
        )


def _migrate_v14_to_v15(db):
    db.execute("""
        CREATE TABLE IF NOT EXISTS return_transactions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id         INTEGER NOT NULL,
            user_id         INTEGER,
            reason          TEXT,
            total_returned  TEXT NOT NULL DEFAULT '0.00',
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sale_id) REFERENCES sales(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS return_items (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            return_id           INTEGER NOT NULL,
            sale_item_id        INTEGER,
            product_id          INTEGER NOT NULL,
            quantity            INTEGER NOT NULL,
            unit_price          TEXT NOT NULL,
            total_price         TEXT NOT NULL,
            FOREIGN KEY (return_id) REFERENCES return_transactions(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS user_permissions (
            user_id       INTEGER NOT NULL,
            permission    TEXT NOT NULL,
            granted       INTEGER DEFAULT 1,
            PRIMARY KEY (user_id, permission),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

def _migrate_v15_to_v16(db):
    db.execute("""
        CREATE TABLE IF NOT EXISTS held_invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            items_json TEXT NOT NULL,
            subtotal TEXT NOT NULL DEFAULT '0.00',
            discount TEXT NOT NULL DEFAULT '0.00',
            payment_method TEXT DEFAULT 'cash',
            customer_id INTEGER,
            customer_name TEXT,
            doctor_id INTEGER,
            doctor_name TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    db.execute("""
        CREATE INDEX IF NOT EXISTS idx_held_invoices_user ON held_invoices(user_id)
    """)

def _migrate_v16_to_v17(db):
    """Add expense cancellation support: is_cancelled flag + expense_cancellations audit table."""
    try:
        db.execute("ALTER TABLE expenses ADD COLUMN is_cancelled INTEGER DEFAULT 0")
    except Exception:
        pass
    try:
        db.execute("ALTER TABLE expenses ADD COLUMN cancelled_at DATETIME")
    except Exception:
        pass
    try:
        db.execute("ALTER TABLE expenses ADD COLUMN cancelled_by INTEGER REFERENCES users(id)")
    except Exception:
        pass

    db.execute("""
        CREATE TABLE IF NOT EXISTS expense_cancellations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            expense_id INTEGER NOT NULL,
            cancelled_by INTEGER NOT NULL,
            cancelled_at DATETIME DEFAULT (datetime('now', 'localtime')),
            reason TEXT,
            FOREIGN KEY (expense_id) REFERENCES expenses(id),
            FOREIGN KEY (cancelled_by) REFERENCES users(id)
        )
    """)
