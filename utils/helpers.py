import re
from datetime import datetime, date


def generate_invoice_number(prefix="INV"):
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3]
    return f"{prefix}-{timestamp}"


def validate_barcode(barcode: str) -> bool:
    return bool(re.match(r"^\d{8,14}$", barcode))


def format_currency(amount: float) -> str:
    return f"{amount:,.2f}"


def parse_date(date_str: str) -> date:
    return datetime.strptime(date_str, "%Y-%m-%d").date()
