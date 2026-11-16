import { useState } from "react";
import QtyInput from "./QtyInput";
import { useNavigate } from "react-router-dom";
import ProductVisual from "./ProductVisual";
import { peso } from "../utils/format";
import { useCart, FREE_SHIPPING_SUBTOTAL, FREE_SHIPPING_QTY } from "../context/CartContext";
import { useAuth } from "../context/AuthContext";
import { useUI } from "../context/UIContext";

export default function CartDrawer() {
  const { lines, changeQty, setQty, removeItem, selectedLines, selSubtotal: subtotal, selQty: totalQty, selSavings: savings,
    selShipping: shipping, isPicked, toggleLine, setAllPicked, removeMany } = useCart();
  const [editing, setEditing] = useState(false);
  const [deleteIds, setDeleteIds] = useState([]);
  const allPicked = lines.length > 0 && lines.every((l) => isPicked(l.product.id));
  const allToDelete = lines.length > 0 && deleteIds.length === lines.length;
  const { user } = useAuth();
  const { cartOpen, closeCart, requireLogin } = useUI();
  const navigate = useNavigate();

  if (!cartOpen) return null;

  function handleCheckout() {
    if (!user) {
      closeCart();
      requireLogin("login", "Please log in to check out");
      return;
    }
    closeCart();
    navigate("/checkout");
  }

  return (
    <div className="overlay" onClick={closeCart}>
      <div className="drawer" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-head">
          <h3 style={{ margin: 0, fontSize: 18 }}>Your Cart</h3>
          <button className="modal-close" onClick={closeCart}>&times;</button>
        </div>
        <div className="drawer-body">
          {lines.length > 0 && (
            <div className="cart-bar">
              {!editing ? (
                <label><input type="checkbox" checked={allPicked} onChange={(e) => setAllPicked(e.target.checked)} /> Select all to order</label>
              ) : (
                <label><input type="checkbox" checked={allToDelete} onChange={(e) => setDeleteIds(e.target.checked ? lines.map((l) => l.product.id) : [])} /> Select all to delete</label>
              )}
              <button type="button" className="btn btn-outline btn-sm" onClick={() => { setEditing((v) => !v); setDeleteIds([]); }}>{editing ? "Done" : "Edit"}</button>
              {editing && (
                <button type="button" className="btn btn-primary btn-sm" disabled={deleteIds.length === 0}
                  onClick={async () => { await removeMany(deleteIds); setDeleteIds([]); setEditing(false); }}>
                  Delete selected ({deleteIds.length})
                </button>
              )}
            </div>
          )}
          {lines.length === 0 ? (
            <div className="empty-state"><p>Your cart is empty.</p></div>
          ) : (
            lines.map((l) => (
              <div className="cart-item" key={l.product.id}>
                {editing ? (
                  <input type="checkbox" aria-label="Delete this item" checked={deleteIds.includes(l.product.id)}
                    onChange={() => setDeleteIds((ids) => (ids.includes(l.product.id) ? ids.filter((x) => x !== l.product.id) : [...ids, l.product.id]))} />
                ) : (
                  <input type="checkbox" aria-label="Order this item" checked={isPicked(l.product.id)} onChange={() => toggleLine(l.product.id)} />
                )}
                <div className="thumb"><ProductVisual product={l.product} widthPercent={100} /></div>
                <div style={{ flex: 1 }}>
                  <h5 style={{ margin: "0 0 4px", fontFamily: "var(--ff-display)", fontSize: 14 }}>{l.product.name}</h5>
                  <span className="mono" style={{ fontSize: 12, color: "var(--soft)" }}>
                    {peso(l.product.onSale ? l.product.salePrice : l.product.price)} each
                    {l.discountRate > 0 && <span style={{ color: "var(--ok-text)" }}> &middot; {Math.round(l.discountRate * 100)}% {l.saleApplied ? "sale" : "bulk"} off</span>}
                  </span>
                  <div className="qty-control">
                    <QtyInput value={l.qty} onCommit={(pcs) => setQty(l.product.id, pcs)} max={l.product.stock} packSize={l.product.packSize} />
                    <span className="remove-link" onClick={() => removeItem(l.product.id)}>Remove</span>
                  </div>
                </div>
                <div style={{ textAlign: "right" }}>
                  {l.discountRate > 0 && (
                    <div style={{ fontSize: 11, color: "var(--soft)", textDecoration: "line-through" }}>{peso(l.originalTotal)}</div>
                  )}
                  <div style={{ fontWeight: 700 }}>{peso(l.lineTotal)}</div>
                </div>
              </div>
            ))
          )}
        </div>
        <div className="drawer-foot">
          {lines.length === 0 ? (
            <button className="btn btn-outline btn-block" onClick={closeCart}>Continue Shopping</button>
          ) : (
            <>
              {savings > 0 && (
                <div className="cart-summary-row" style={{ color: "var(--ok-text)", fontWeight: 600 }}>
                  <span>Savings</span><span>-{peso(savings)}</span>
                </div>
              )}
              <div className="cart-summary-row"><span>Subtotal</span><span>{peso(subtotal)}</span></div>
              <div className="cart-summary-row" style={{ fontSize: 12 }}>
                {shipping === 0
                  ? <span style={{ color: "var(--ok-text)" }}>Free shipping applied</span>
                  : `Add ${peso(FREE_SHIPPING_SUBTOTAL - subtotal)} more or ${FREE_SHIPPING_QTY - totalQty} more items for free shipping`}
              </div>
              <button className="btn btn-primary btn-block" style={{ marginTop: 10 }} disabled={selectedLines.length === 0} onClick={handleCheckout}>Checkout ({selectedLines.length} selected)</button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
