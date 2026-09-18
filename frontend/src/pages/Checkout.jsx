import { useState } from "react";
import { useNavigate } from "react-router-dom";
import client from "../api/client";
import { peso } from "../utils/format";
import { useAuth } from "../context/AuthContext";
import { useCart, FREE_SHIPPING_SUBTOTAL } from "../context/CartContext";
import { useToast } from "../context/ToastContext";

export default function Checkout() {
  const { user } = useAuth();
  const { lines, subtotal, savings, shipping, total, clearCart } = useCart();
  const showToast = useToast();
  const navigate = useNavigate();

  const [form, setForm] = useState({
    name: user?.name || "",
    phone: user?.phone || "",
    email: user?.email || "",
    line1: user?.address?.line1 || "",
    city: user?.address?.city || "",
    province: user?.address?.province || "",
    region: user?.address?.region || "",
    zip: user?.address?.zip || "",
    payment: "Cash on Delivery",
  });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function update(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  if (lines.length === 0) {
    return (
      <div className="container" style={{ padding: "80px 24px", textAlign: "center" }}>
        <h2>Your cart is empty</h2>
        <button className="btn btn-primary" onClick={() => navigate("/")}>Continue Shopping</button>
      </div>
    );
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const res = await client.post("/api/orders", {
        items: lines.map((l) => ({ productId: l.product.id, qty: l.qty })),
        customer: { name: form.name, phone: form.phone, email: form.email },
        address: { line1: form.line1, city: form.city, province: form.province, region: form.region, zip: form.zip },
        paymentMethod: form.payment,
      });
      clearCart();
      showToast("Order placed successfully. A confirmation email is on its way.", "success");
      navigate("/order-success", { state: { order: res.data.order, recommendations: res.data.recommendations } });
    } catch (err) {
      setError(err.response?.data?.error || "Something went wrong placing your order.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="container" style={{ padding: "40px 24px 80px" }}>
      <h1 style={{ marginBottom: 24 }}>Checkout</h1>
      {error && <div className="alert alert-error">{error}</div>}
      <form onSubmit={handleSubmit} className="two-col" style={{ gridTemplateColumns: "1.2fr 0.8fr", gap: 26 }}>
        <div>
          <h4 style={{ marginBottom: 12 }}>Customer Information</h4>
          <div className="field-row">
            <div className="field"><label>Full Name</label><input required value={form.name} onChange={(e) => update("name", e.target.value)} /></div>
            <div className="field"><label>Contact Number</label><input required placeholder="09xx xxx xxxx" value={form.phone} onChange={(e) => update("phone", e.target.value)} /></div>
          </div>
          <div className="field"><label>Email Address</label><input required type="email" value={form.email} onChange={(e) => update("email", e.target.value)} /></div>

          <h4 style={{ margin: "18px 0 12px" }}>Delivery Address</h4>
          <div className="field"><label>Street Address</label><input required placeholder="House/Unit No., Street, Barangay" value={form.line1} onChange={(e) => update("line1", e.target.value)} /></div>
          <div className="field-row">
            <div className="field"><label>City / Municipality</label><input required value={form.city} onChange={(e) => update("city", e.target.value)} /></div>
            <div className="field"><label>Province</label><input required value={form.province} onChange={(e) => update("province", e.target.value)} /></div>
          </div>
          <div className="field-row">
            <div className="field"><label>Region</label><input required value={form.region} onChange={(e) => update("region", e.target.value)} /></div>
            <div className="field"><label>ZIP Code</label><input required value={form.zip} onChange={(e) => update("zip", e.target.value)} /></div>
          </div>

          <h4 style={{ margin: "18px 0 12px" }}>Payment Method</h4>
          <div className="field">
            <select value={form.payment} onChange={(e) => update("payment", e.target.value)}>
              <option>Cash on Delivery</option>
              <option>GCash</option>
              <option>Credit / Debit Card</option>
            </select>
          </div>
        </div>

        <div className="panel">
          <h4 style={{ marginBottom: 12 }}>Order Summary</h4>
          <div style={{ maxHeight: 220, overflowY: "auto" }}>
            {lines.map((l) => (
              <div className="cart-summary-row" key={l.product.id}>
                <span>{l.product.name} x {l.qty}{l.discountRate > 0 && <span style={{ color: "#1d8348" }}> (-{Math.round(l.discountRate * 100)}%)</span>}</span>
                <span>{peso(l.lineTotal)}</span>
              </div>
            ))}
          </div>
          {savings > 0 && (
            <div className="cart-summary-row" style={{ color: "#1d8348", fontWeight: 600, marginTop: 10 }}>
              <span>Bulk savings</span><span>-{peso(savings)}</span>
            </div>
          )}
          <div className="cart-summary-row"><span>Subtotal</span><span>{peso(subtotal)}</span></div>
          <div className="cart-summary-row"><span>Shipping</span><span>{shipping === 0 ? "FREE" : peso(shipping)}</span></div>
          <div className="cart-summary-row total"><span>Total</span><span>{peso(total)}</span></div>
          <button type="submit" className="btn btn-primary btn-block" style={{ marginTop: 16 }} disabled={submitting}>
            {submitting ? "Placing Order..." : "Place Order"}
          </button>
          <p className="field-hint" style={{ textAlign: "center", marginTop: 8 }}>
            Free shipping on orders of {peso(FREE_SHIPPING_SUBTOTAL)}+ or 10+ items. Bulk discounts apply automatically.
          </p>
        </div>
      </form>
    </div>
  );
}
