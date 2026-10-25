from decimal import Decimal, ROUND_HALF_UP

FREE_SHIPPING_SUBTOTAL = Decimal("1500")
FREE_SHIPPING_QTY = 10
STANDARD_SHIPPING_FEE = Decimal("80")


def money(value):
    """Rounds to whole centavos, half up (the same as the website)."""
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def bulk_discount_rate(quantity):
    if quantity >= 20:
        return Decimal("0.15")
    if quantity >= 10:
        return Decimal("0.10")
    if quantity >= 5:
        return Decimal("0.05")
    return Decimal("0")


def effective_discount_rate(quantity, sale_percent=0):
    """A sale and the bulk discount do not stack: the customer gets whichever is bigger."""
    sale_rate = Decimal(int(sale_percent or 0)) / 100
    return max(bulk_discount_rate(quantity), sale_rate)


def unit_price_after_discount(price, rate):
    """Price of one unit after the bulk discount, to the centavo."""
    keep_percent = int(((1 - Decimal(str(rate))) * 100).to_integral_value(rounding=ROUND_HALF_UP))
    return money(Decimal(str(price)) * keep_percent / 100)


def compute_shipping(subtotal, total_qty):
    if Decimal(str(subtotal)) >= FREE_SHIPPING_SUBTOTAL or total_qty >= FREE_SHIPPING_QTY:
        return Decimal("0")
    return STANDARD_SHIPPING_FEE
