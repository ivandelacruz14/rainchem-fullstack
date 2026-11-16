import { createContext, useContext, useState, useEffect, useCallback } from "react";
import client from "../api/client";
import { useAuth } from "./AuthContext";
import { useToast } from "./ToastContext";
import { FREE_SHIPPING_SUBTOTAL, FREE_SHIPPING_QTY, bulkDiscountRate, computeShipping, priceLine } from "../utils/pricing";

const CartContext = createContext(null);

export { FREE_SHIPPING_SUBTOTAL, FREE_SHIPPING_QTY, bulkDiscountRate, computeShipping };

const LEGACY_CART_KEY = "rainchem_cart";

function errorText(err, fallback) {
  return err.response?.data?.error || fallback;
}

/**
 * The cart lives on the server, tied to the signed-in account, so it cannot be mixed up
 * between people sharing a device and always shows current prices and stock.
 */
export function CartProvider({ children }) {
  const { user } = useAuth();
  const showToast = useToast();
  const userId = user?.id ?? null;
  const [items, setItems] = useState([]);

  useEffect(() => {
    if (!userId) {
      setItems([]);
      return undefined;
    }
    let cancelled = false;

    async function load() {
      try {
        let res = await client.get("/api/cart");
        // Carts saved in the browser before accounts had a server cart: move them over once.
        const legacy = readLegacyCart();
        if (legacy.length && (res.data.items || []).length === 0) {
          for (const line of legacy) {
            try {
              res = await client.post("/api/cart/items", { productId: line.product.id, qty: line.qty });
            } catch { /* skip lines that are no longer available */ }
          }
        }
        if (!cancelled) setItems(res.data.items || []);
      } catch { /* the cart stays empty; the next action will surface any real problem */ }
      finally {
        localStorage.removeItem(LEGACY_CART_KEY);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [userId]);

  const apply = useCallback((res) => setItems(res.data.items || []), []);

  const addItem = useCallback(async (product, qty = 1) => {
    try {
      apply(await client.post("/api/cart/items", { productId: product.id, qty }));
      return true;
    } catch (err) {
      showToast(errorText(err, "Could not add this item to your cart"), "error");
      return false;
    }
  }, [apply, showToast]);

  const setQty = useCallback(async (productId, qty) => {
    try {
      apply(await client.put(`/api/cart/items/${productId}`, { qty }));
    } catch (err) {
      showToast(errorText(err, "Could not update your cart"), "error");
    }
  }, [apply, showToast]);

  function changeQty(productId, delta) {
    const line = items.find((l) => l.product.id === productId);
    if (line) setQty(productId, line.qty + delta);
  }

  async function removeItem(productId) {
    try {
      apply(await client.delete(`/api/cart/items/${productId}`));
    } catch (err) {
      showToast(errorText(err, "Could not update your cart"), "error");
    }
  }

  async function clearCart() {
    setItems([]);
    if (!userId) return;
    try {
      await client.delete("/api/cart");
    } catch { /* the order already cleared what was bought */ }
  }

  const reloadCart = useCallback(async () => {
    try {
      apply(await client.get("/api/cart"));
    } catch { /* keep what is shown */ }
  }, [apply]);

  const lines = items.map((line) => {
    const priced = priceLine(line.product.price, line.qty, line.product.salePercent);
    return {
      ...line,
      discountRate: priced.rate,
      saleApplied: (line.product.salePercent || 0) / 100 >= bulkDiscountRate(line.qty) && (line.product.salePercent || 0) > 0,
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

  // Which lines are picked for ordering. Everything is picked unless it was unticked, so new items start picked.
  const [excluded, setExcluded] = useState([]);
  // Buy Now is kept apart from the cart. It survives a page refresh within the same tab.
  const [directItem, setDirectItem] = useState(() => {
    try { return JSON.parse(sessionStorage.getItem("rainchem_direct") || "null"); } catch { return null; }
  });
  useEffect(() => {
    if (directItem) sessionStorage.setItem("rainchem_direct", JSON.stringify(directItem));
    else sessionStorage.removeItem("rainchem_direct");
  }, [directItem]);
  const startDirect = (product, pieces) => setDirectItem({ product, qty: Math.max(1, pieces) });
  const setDirectQty = (pieces) => setDirectItem((d) => (d ? { ...d, qty: Math.max(1, pieces) } : d));
  const clearDirect = () => setDirectItem(null);
  const isPicked = (productId) => !excluded.includes(productId);
  const directLine = directItem ? (() => {
    const priced = priceLine(directItem.product.price, directItem.qty, directItem.product.salePercent);
    return { product: directItem.product, qty: directItem.qty, lineCents: priced.lineCents, lineTotal: priced.lineTotal,
      originalTotal: priced.originalTotal, discountRate: priced.rate };
  })() : null;
  const selectedLines = directLine ? [directLine] : lines.filter((l) => isPicked(l.product.id));
  const selSubtotal = selectedLines.reduce((sum, l) => sum + l.lineCents, 0) / 100;
  const selQty = selectedLines.reduce((sum, l) => sum + l.qty, 0);
  const selSavings = selectedLines.reduce((sum, l) => sum + (l.originalTotal - l.lineTotal), 0);
  const selShipping = selectedLines.length ? computeShipping(selSubtotal, selQty) : 0;
  const selTotal = Math.round(selSubtotal * 100 + selShipping * 100) / 100;
  const toggleLine = (productId) => setExcluded((ex) => (ex.includes(productId) ? ex.filter((x) => x !== productId) : [...ex, productId]));
  const setAllPicked = (on) => setExcluded(on ? [] : lines.map((l) => l.product.id));

  async function removeMany(productIds) {
    try {
      apply(await client.post("/api/cart/remove", { productIds }));
      setExcluded([]);
    } catch (err) {
      showToast(errorText(err, "Could not remove the selected items"), "error");
    }
  }

  return (
    <CartContext.Provider
      value={{
        items, lines, subtotal, totalQty, savings, shipping, total, addItem, changeQty, setQty, removeItem, clearCart,
        reloadCart, selectedLines, selSubtotal, selQty, selSavings, selShipping, selTotal, isPicked, toggleLine, setAllPicked, removeMany,
        setExcludedIds: setExcluded, startDirect, setDirectQty, clearDirect, isDirect: Boolean(directItem),
      }}
    >
      {children}
    </CartContext.Provider>
  );
}

function readLegacyCart() {
  try {
    const saved = JSON.parse(localStorage.getItem(LEGACY_CART_KEY));
    return Array.isArray(saved) ? saved.filter((l) => l?.product?.id && l.qty > 0) : [];
  } catch {
    return [];
  }
}

export function useCart() {
  return useContext(CartContext);
}
