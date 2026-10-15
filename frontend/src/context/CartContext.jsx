import { createContext, useContext, useState, useEffect } from "react";

const CartContext = createContext(null);

import { FREE_SHIPPING_SUBTOTAL, FREE_SHIPPING_QTY, bulkDiscountRate, computeShipping, priceLine } from "../utils/pricing";

export { FREE_SHIPPING_SUBTOTAL, FREE_SHIPPING_QTY, bulkDiscountRate, computeShipping };

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
    const priced = priceLine(line.product.price, line.qty);
    return {
      ...line,
      discountRate: priced.rate,
      unitPrice: priced.unitPrice,
      lineTotal: priced.lineTotal,
      lineCents: priced.lineCents,
      originalTotal: priced.originalTotal,
    };
  });

  const subtotal = lines.reduce((sum, l) => sum + l.lineCents, 0) / 100;
  const totalQty = lines.reduce((sum, l) => sum + l.qty, 0);
  const savings = lines.reduce((sum, l) => sum + (l.originalTotal - l.lineTotal), 0);
  const shipping = computeShipping(subtotal, totalQty);
  const total = Math.round(subtotal * 100 + shipping * 100) / 100;

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
