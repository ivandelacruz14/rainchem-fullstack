import { useState } from "react";
import { useNavigate } from "react-router-dom";
import ProductVisual from "./ProductVisual";
import { peso } from "../utils/format";
import { useAuth } from "../context/AuthContext";
import { useCart, bulkDiscountRate } from "../context/CartContext";
import { useToast } from "../context/ToastContext";
import { useUI } from "../context/UIContext";

export default function ProductModal({ product, onClose }) {
  const { user } = useAuth();
  const { addItem } = useCart();
  const showToast = useToast();
  const navigate = useNavigate();
  const { requireLogin } = useUI();
  const [qty, setQty] = useState(1);

  if (!product) return null;

  const rate = bulkDiscountRate(qty);
  const discountedUnit = product.price * (1 - rate);
  const nextTier = qty < 5 ? 5 : qty < 10 ? 10 : 20;

  function handleAddToCart() {
    addItem(product, qty);
    showToast("Added to cart", "success");
    onClose();
  }

  function handleBuyNow() {
    addItem(product, qty);
    onClose();
    navigate("/checkout");
  }

  return (
    <div className="overlay" onClick={onClose}>
      <div className="modal wide" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h3>Product Details</h3>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>
        <div className="modal-body">
          <div className="pd-grid">
            <div className="pd-visual">
              <ProductVisual product={product} widthPercent={44} />
            </div>
            <div>
              <span className="product-cat">{product.category}</span>
              <h2 style={{ margin: "6px 0 4px" }}>{product.name}</h2>
              <span className="product-rating">{"\u2605"} {product.rating} &middot; {product.reviews} reviews</span>
              <span className={`stock-count ${product.stock < 20 ? "low" : ""}`} style={{ display: "block", marginTop: 4 }}>
                {product.stock > 0 ? `${product.stock} units available` : "Out of stock"}
              </span>
              <p style={{ marginTop: 14, color: "#57524c" }}>{product.description}</p>

              <ul className="pd-specs">
                {product.specs.map((s, i) => <li key={i}>{s}</li>)}
              </ul>

              {product.benefits?.length > 0 && (
                <div className="pd-extra">
                  <h4 className="pd-extra-head">Key Benefits</h4>
                  <ul className="pd-specs">
                    {product.benefits.map((b, i) => <li key={i}>{b}</li>)}
                  </ul>
                </div>
              )}

              {product.usage?.length > 0 && (
                <div className="pd-extra">
                  <h4 className="pd-extra-head">How to Use</h4>
                  <ol className="pd-specs" style={{ paddingLeft: 18 }}>
                    {product.usage.map((u, i) => <li key={i} style={{ listStyle: "decimal" }}>{u}</li>)}
                  </ol>
                </div>
              )}

              <div className="pd-extra">
                <h4 className="pd-extra-head">Bulk Pricing - Buy More, Save More</h4>
                <div className="bulk-tiers">
                  <div className="bulk-tier"><span>5-9 units</span><span>5% off</span></div>
                  <div className="bulk-tier"><span>10-19 units</span><span>10% off</span></div>
                  <div className="bulk-tier"><span>20+ units</span><span>15% off</span></div>
                </div>
                <p className="field-hint">Free shipping automatically applies on orders of &#8369;1,500+ or 10+ total items.</p>
              </div>

              <div className="pd-extra pd-shipping">
                <div>Metro Manila: 1-2 business days &middot; Provincial: 3-5 business days</div>
                <div>7-day return &middot; 30-day defect replacement &middot; Rainchem-verified product</div>
              </div>

              <div className="product-price" style={{ fontSize: 26 }}>{peso(product.price)}</div>

              {user ? (
                <>
                  <div className="pd-qty">
                    <div className="qty-control">
                      <button onClick={() => setQty((q) => Math.max(1, q - 1))}>-</button>
                      <span>{qty}</span>
                      <button onClick={() => setQty((q) => q + 1)}>+</button>
                    </div>
                  </div>
                  <p className="field-hint" style={{ marginTop: -8, marginBottom: 14 }}>
                    {rate > 0
                      ? <span style={{ color: "#1d8348", fontWeight: 600 }}>{Math.round(rate * 100)}% bulk discount applied - {peso(discountedUnit)} per unit &middot; {peso(discountedUnit * qty)} total</span>
                      : qty < 20 ? `Buy ${nextTier - qty} more to unlock a bulk discount` : ""}
                  </p>
                  <div className="flex gap-12">
                    <button className="btn btn-outline btn-block" disabled={product.stock === 0} onClick={handleAddToCart}>Add to Cart</button>
                    <button className="btn btn-primary btn-block" disabled={product.stock === 0} onClick={handleBuyNow}>Buy Now</button>
                  </div>
                </>
              ) : (
                <>
                  <div className="alert alert-info" style={{ marginTop: 16 }}>
                    Log in or create a free account to add this item to your cart or buy it now.
                  </div>
                  <div className="flex gap-12">
                    <button className="btn btn-outline btn-block" onClick={() => { onClose(); requireLogin("login"); }}>Log In</button>
                    <button className="btn btn-primary btn-block" onClick={() => { onClose(); requireLogin("register"); }}>Create Account</button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
