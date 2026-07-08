from decimal import Decimal, ROUND_HALF_UP, ROUND_CEILING, ROUND_FLOOR

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
    return f"{d:,.0f}"


def round_up_to_250(amount: Decimal) -> Decimal:
    """Round a Decimal amount UP to the nearest 250 (Iraqi currency)."""
    return (amount / Decimal("250")).quantize(Decimal("1"), rounding=ROUND_CEILING) * Decimal("250")


def round_down_to_250(amount: Decimal) -> Decimal:
    """Round a Decimal amount DOWN to the nearest 250 (Iraqi currency)."""
    return (amount / Decimal("250")).quantize(Decimal("1"), rounding=ROUND_FLOOR) * Decimal("250")


def round_to_nearest_250(amount: Decimal) -> Decimal:
    """Round a Decimal amount to the NEAREST 250."""
    return (amount / Decimal("250")).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * Decimal("250")


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
