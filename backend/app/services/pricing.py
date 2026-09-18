FREE_SHIPPING_SUBTOTAL = 1500
FREE_SHIPPING_QTY = 10
STANDARD_SHIPPING_FEE = 80


def bulk_discount_rate(quantity):
    if quantity >= 20:
        return 0.15
    if quantity >= 10:
        return 0.10
    if quantity >= 5:
        return 0.05
    return 0


def compute_shipping(subtotal, total_qty):
    if subtotal >= FREE_SHIPPING_SUBTOTAL or total_qty >= FREE_SHIPPING_QTY:
        return 0
    return STANDARD_SHIPPING_FEE
