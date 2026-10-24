import { createContext, useContext, useState, useEffect, useRef } from "react";
import client from "../api/client";
import { useAuth } from "./AuthContext";
import { FREE_SHIPPING_SUBTOTAL, FREE_SHIPPING_QTY, bulkDiscountRate, computeShipping, priceLine } from "../utils/pricing";

const CartContext = createContext(null);

export { FREE_SHIPPING_SUBTOTAL, FREE_SHIPPING_QTY, bulkDiscountRate, computeShipping };

const LEGACY_CART_KEY = "rainchem_cart";

function cartKey(userId) {
  return `rainchem_cart:${userId}`;
}

function readCart(userId) {
  try {
    const saved = JSON.parse(localStorage.getItem(cartKey(userId)));
    return Array.isArray(saved) ? saved : [];
  } catch {
    return [];
  }
}

export function CartProvider({ children }) {
  const { user } = useAuth();
  const userId = user?.id ?? null;
  const [items, setItems] = useState([]);
  const loadedFor = useRef(null);

  // The cart belongs to the signed-in account. It is loaded when that account
  // signs in and cleared from memory when it signs out.
  useEffect(() => {
    localStorage.removeItem(LEGACY_CART_KEY);
    loadedFor.current = null;
    if (userId === null) {
      setItems([]);
      return;
    }
    setItems(readCart(userId));
    loadedFor.current = userId;
  }, [userId]);

  useEffect(() => {
    if (userId === null || loadedFor.current !== userId) return;
    localStorage.setItem(cartKey(userId), JSON.stringify(items));
  }, [items, userId]);

  // Prices and stock shown in the cart always come from the catalogue, not from
  // whatever was saved when the item was added. The server prices the order again at checkout.
  useEffect(() => {
    if (userId === null) return undefined;
    let cancelled = false;
    client.get("/api/products").then((res) => {
      if (cancelled) return;
      const fresh = new Map(res.data.products.map((p) => [p.id, p]));
      setItems((prev) => prev
        .filter((line) => fresh.has(line.product.id))
        .map((line) => ({ ...line, product: fresh.get(line.product.id) })));
    }).catch(() => {});
    return () => { cancelled = true; };
  }, [userId]);

  function addItem(product, qty) {
    if (userId === null) return;
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
