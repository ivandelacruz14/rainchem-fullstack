
export const FREE_SHIPPING_SUBTOTAL = 1500;
export const FREE_SHIPPING_QTY = 10;
export const STANDARD_SHIPPING_FEE = 80;

export function bulkDiscountRate(qty) {
  if (qty >= 20) return 0.15;
  if (qty >= 10) return 0.1;
  if (qty >= 5) return 0.05;
  return 0;
}

export function computeShipping(subtotal, totalQty) {
  return subtotal >= FREE_SHIPPING_SUBTOTAL || totalQty >= FREE_SHIPPING_QTY ? 0 : STANDARD_SHIPPING_FEE;
}

export function priceLine(price, qty) {
  const rate = bulkDiscountRate(qty);
  const priceCents = Math.round(Number(price) * 100);
  const keepPercent = Math.round((1 - rate) * 100); // 100, 95, 90 or 85
  const unitCents = Math.round((priceCents * keepPercent) / 100);
  return {
    rate,
    unitCents,
    unitPrice: unitCents / 100,
    lineTotal: (unitCents * qty) / 100,
    lineCents: unitCents * qty,
    originalTotal: (priceCents * qty) / 100,
  };
}

export function priceCart(lines) {
  const priced = lines.map((l) => priceLine(l.price, l.qty));
  const subtotalCents = priced.reduce((sum, l) => sum + l.lineCents, 0);
  const totalQty = lines.reduce((sum, l) => sum + l.qty, 0);
  const subtotal = subtotalCents / 100;
  const shipping = computeShipping(subtotal, totalQty);
  return { priced, subtotal, shipping, total: (subtotalCents + shipping * 100) / 100, totalQty };
}
