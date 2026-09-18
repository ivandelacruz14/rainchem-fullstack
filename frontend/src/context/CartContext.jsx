import { createContext, useContext, useState, useEffect } from "react";

const CartContext = createContext(null);

export const FREE_SHIPPING_SUBTOTAL = 1500;
export const FREE_SHIPPING_QTY = 10;
const STANDARD_SHIPPING_FEE = 80;

export function bulkDiscountRate(qty) {
  if (qty >= 20) return 0.15;
  if (qty >= 10) return 0.1;
  if (qty >= 5) return 0.05;
  return 0;
}

export function computeShipping(subtotal, totalQty) {
  return subtotal >= FREE_SHIPPING_SUBTOTAL || totalQty >= FREE_SHIPPING_QTY ? 0 : STANDARD_SHIPPING_FEE;
}

export function CartProvider({ children }) {
  const [items, setItems] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem("rainchem_cart")) || [];
    } catch {
      return [];
    }
  });

  useEffect(() => {
    localStorage.setItem("rainchem_cart", JSON.stringify(items));
  }, [items]);

  function addItem(product, qty) {
    setItems((prev) => {
      const existing = prev.find((line) => line.product.id === product.id);
      if (existing) {
        return prev.map((line) =>
          line.product.id === product.id ? { ...line, qty: line.qty + qty } : line
        );
      }
      return [...prev, { product, qty }];
    });
  }

  function changeQty(productId, delta) {
    setItems((prev) =>
      prev
        .map((line) =>
          line.product.id === productId ? { ...line, qty: line.qty + delta } : line
        )
        .filter((line) => line.qty > 0)
    );
  }

  function removeItem(productId) {
    setItems((prev) => prev.filter((line) => line.product.id !== productId));
  }

  function clearCart() {
    setItems([]);
  }

  const lines = items.map((line) => {
    const rate = bulkDiscountRate(line.qty);
    const unitPrice = line.product.price * (1 - rate);
    return {
      ...line,
      discountRate: rate,
      unitPrice,
      lineTotal: unitPrice * line.qty,
      originalTotal: line.product.price * line.qty,
    };
  });

  const subtotal = lines.reduce((sum, l) => sum + l.lineTotal, 0);
  const totalQty = lines.reduce((sum, l) => sum + l.qty, 0);
  const savings = lines.reduce((sum, l) => sum + (l.originalTotal - l.lineTotal), 0);
  const shipping = computeShipping(subtotal, totalQty);
  const total = subtotal + shipping;

  return (
    <CartContext.Provider
      value={{ items, lines, subtotal, totalQty, savings, shipping, total, addItem, changeQty, removeItem, clearCart }}
    >
      {children}
    </CartContext.Provider>
  );
}

export function useCart() {
  return useContext(CartContext);
}
