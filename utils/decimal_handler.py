from decimal import Decimal, ROUND_HALF_UP

PRECISION = Decimal("0.01")
DECIMAL_ZERO = Decimal("0.00")


def to_decimal(value) -> Decimal:
    if value is None:
        return DECIMAL_ZERO
    if isinstance(value, Decimal):
        return value.quantize(PRECISION, rounding=ROUND_HALF_UP)
    if isinstance(value, str):
        if value.strip() == "":
            return DECIMAL_ZERO
        try:
            return Decimal(value.strip()).quantize(PRECISION, rounding=ROUND_HALF_UP)
        except Exception:
            return DECIMAL_ZERO
    if isinstance(value, (int, float)):
        return Decimal(str(value)).quantize(PRECISION, rounding=ROUND_HALF_UP)
    return DECIMAL_ZERO


def from_decimal(value) -> str:
    return str(to_decimal(value))


def format_currency(value) -> str:
    d = to_decimal(value)
    return f"{d:,.2f}"


def sum_decimals(values: list) -> Decimal:
    total = DECIMAL_ZERO
    for v in values:
        total += to_decimal(v)
    return total.quantize(PRECISION, rounding=ROUND_HALF_UP)


def multiply_decimals(a, b) -> Decimal:
    return (to_decimal(a) * to_decimal(b)).quantize(PRECISION, rounding=ROUND_HALF_UP)


def apply_discount(amount: Decimal, discount_pct: Decimal) -> Decimal:
    factor = (Decimal("100") - discount_pct) / Decimal("100")
    return (amount * factor).quantize(PRECISION, rounding=ROUND_HALF_UP)
