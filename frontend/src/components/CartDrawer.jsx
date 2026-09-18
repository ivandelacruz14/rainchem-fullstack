import { useNavigate } from "react-router-dom";
import ProductVisual from "./ProductVisual";
import { peso } from "../utils/format";
import { useCart, FREE_SHIPPING_SUBTOTAL, FREE_SHIPPING_QTY } from "../context/CartContext";
import { useAuth } from "../context/AuthContext";
import { useUI } from "../context/UIContext";

export default function CartDrawer() {
  const { lines, subtotal, totalQty, savings, shipping, changeQty, removeItem } = useCart();
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
          {lines.length === 0 ? (
            <div className="empty-state"><p>Your cart is empty.</p></div>
          ) : (
            lines.map((l) => (
              <div className="cart-item" key={l.product.id}>
                <div className="thumb"><ProductVisual product={l.product} widthPercent={100} /></div>
                <div style={{ flex: 1 }}>
                  <h5 style={{ margin: "0 0 4px", fontFamily: "var(--ff-display)", fontSize: 14 }}>{l.product.name}</h5>
                  <span className="mono" style={{ fontSize: 12, color: "#8a8580" }}>
                    {peso(l.product.price)} each
                    {l.discountRate > 0 && <span style={{ color: "#1d8348" }}> &middot; {Math.round(l.discountRate * 100)}% bulk off</span>}
                  </span>
                  <div className="qty-control">
                    <button onClick={() => changeQty(l.product.id, -1)}>-</button>
                    <span>{l.qty}</span>
                    <button onClick={() => changeQty(l.product.id, 1)}>+</button>
                    <span className="remove-link" onClick={() => removeItem(l.product.id)}>Remove</span>
                  </div>
                </div>
                <div style={{ textAlign: "right" }}>
                  {l.discountRate > 0 && (
                    <div style={{ fontSize: 11, color: "#8a8580", textDecoration: "line-through" }}>{peso(l.originalTotal)}</div>
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
                <div className="cart-summary-row" style={{ color: "#1d8348", fontWeight: 600 }}>
                  <span>Bulk savings</span><span>-{peso(savings)}</span>
                </div>
              )}
              <div className="cart-summary-row"><span>Subtotal</span><span>{peso(subtotal)}</span></div>
              <div className="cart-summary-row" style={{ fontSize: 12 }}>
                {shipping === 0
                  ? <span style={{ color: "#1d8348" }}>Free shipping applied</span>
                  : `Add ${peso(FREE_SHIPPING_SUBTOTAL - subtotal)} more or ${FREE_SHIPPING_QTY - totalQty} more items for free shipping`}
              </div>
              <button className="btn btn-primary btn-block" style={{ marginTop: 10 }} onClick={handleCheckout}>Checkout</button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
