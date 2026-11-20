import CheckoutItem from "../components/CheckoutItem";
import ProductModal from "../components/ProductModal";
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import client from "../api/client";
import { peso } from "../utils/format";
import { useAuth } from "../context/AuthContext";
import { useCart, FREE_SHIPPING_SUBTOTAL } from "../context/CartContext";
import { useToast } from "../context/ToastContext";
import ConfirmDialog from "../components/ConfirmDialog";
import useOrderRules from "../hooks/useOrderRules";

const PAYMENT_OPTIONS = [
  { value: "Cash on Delivery", tag: "Cash", label: "Cash on Delivery", hint: "Pay in cash when your order arrives." },
  { value: "GCash", tag: "GCash", label: "GCash", hint: "You'll see our GCash number and link next. Pay, then send your reference number." },
  { value: "Credit / Debit Card", tag: "Card", label: "Credit / Debit Card", hint: "You'll pay on a secure card page. We never see your card number." },
];

export default function Checkout() {
  const { user } = useAuth();
  const { selectedLines: lines, selSubtotal: subtotal, selSavings: savings, selShipping: shipping, selTotal: total, reloadCart, isDirect, clearDirect } = useCart();
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
  const [methods, setMethods] = useState({ "Cash on Delivery": true });
  const [savedAddresses, setSavedAddresses] = useState([]);
  const [addressChoice, setAddressChoice] = useState("");

  function pickAddress(a) {
    setAddressChoice(String(a.id));
    const line = [a.unit, [a.houseNumber, a.street].filter(Boolean).join(" "), a.subdivision, a.village, a.landmark]
      .filter(Boolean).join(", ");
    setForm((f) => ({
      ...f, addressType: a.label, line1: line, city: a.city.name, province: (a.province && a.province.name) || a.region.name,
      region: a.region.name, zip: a.zipCode || "",
    }));
  }

  function chooseAddress(value) {
    if (value === "new") {
      setAddressChoice("new");
      setForm((f) => ({ ...f, addressType: "Home", line1: "", city: "", province: "", region: "", zip: "" }));
      return;
    }
    const found = savedAddresses.find((a) => String(a.id) === value);
    if (found) pickAddress(found);
  }

  useEffect(() => {
    let active = true;
    Promise.resolve()
      .then(() => client.get("/api/addresses"))
      .then((res) => {
        if (!active) return;
        const list = res.data.addresses || [];
        setSavedAddresses(list);
        const chosen = list.find((a) => a.isDefault) || list[0];
        if (chosen) pickAddress(chosen);
      })
      .catch(() => {});
    return () => { active = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const [demoMode, setDemoMode] = useState(false);
  const [duplicateOrder, setDuplicateOrder] = useState(null);
  const [viewing, setViewing] = useState(null);

  // Same rule as the server: 100 boxes or more is a bulk order, and bulk orders are paid in advance.
  const totalBoxes = lines.reduce((sum, l) => sum + Math.ceil(l.qty / (Number(l.product.packSize) || 1)), 0);
  const rules = useOrderRules();
  const bulk = totalBoxes >= rules.reviewBoxes;
  const anyBoxed = lines.some((l) => Number(l.product.packSize) > 1);
  const isBusiness = user?.accountType === "business";
  const boxLimit = isBusiness ? (user?.businessVerified ? rules.verifiedMaxBoxes : rules.basicMaxBoxes) : rules.personalMaxBoxes;
  useEffect(() => {
    if (bulk && form.payment === "Cash on Delivery") update("payment", "GCash");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bulk]);


  useEffect(() => {
    client.get("/api/payments/config").then((res) => {
      setMethods(res.data.methods);
      setDemoMode(res.data.demoMode);
    }).catch(() => {});
  }, []);

  function update(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  if (lines.length === 0 && !submitting) {
    return (
      <div className="container" style={{ padding: "80px 24px", textAlign: "center" }}>
        <h2>Your cart is empty</h2>
        <button className="btn btn-primary" onClick={() => navigate("/")}>Continue Shopping</button>
      </div>
    );
  }

  function handleSubmit(e) {
    e.preventDefault();
    setError("");
    placeOrder();
  }

  async function placeOrder(confirmDuplicate = false) {
    let leavingPage = false;
    setSubmitting(true);
    try {
      const res = await client.post("/api/orders", {
        items: lines.map((l) => ({ productId: l.product.id, qty: l.qty })),
        customer: { name: form.name, phone: form.phone, email: form.email },
        address: { line1: form.addressType ? `${form.addressType}: ${form.line1}` : form.line1, city: form.city, province: form.province, region: form.region, zip: form.zip },
        paymentMethod: form.payment,
        confirmDuplicate,
        direct: isDirect,
      });
      reloadCart();
      if (isDirect) clearDirect();

      if (res.data.payPath) {
        // GCash / card: continue on our payment page (where the method can still be changed).
        leavingPage = true;
        navigate(res.data.payPath, { replace: true });
        return;
      }
      showToast("Order placed successfully. A confirmation email is on its way.", "success");
      navigate("/order-success", { state: { order: res.data.order, recommendations: res.data.recommendations } });
    } catch (err) {
      if (err.response?.status === 409 && err.response.data?.needsConfirmation) {
        setDuplicateOrder(err.response.data.duplicateOrder);
        return;
      }
      setError(
        err.response?.data?.error
          || (err.response
            ? `The server could not process your order (error ${err.response.status}). Please try again.`
            : "Could not reach the server. Please check your connection and try again."),
      );
      window.scrollTo({ top: 0, behavior: "smooth" });
    } finally {
      if (!leavingPage) setSubmitting(false);
    }
  }

  const isCod = form.payment === "Cash on Delivery";
  const buttonLabel = submitting
    ? "Please wait..."
    : isCod ? "Place Order" : `Place Order & Pay with ${form.payment === "GCash" ? "GCash" : "Card"}`;

  return (
    <div className="container" style={{ padding: "40px 24px 80px" }}>
      <h1 style={{ marginBottom: 24 }}>Checkout</h1>
      {error && <div className="alert alert-error">{error}</div>}
      {demoMode && (
        <div className="alert alert-info">
          Payment demo mode is ON: card payments use a fake payment page. For testing only.
        </div>
      )}
      <form onSubmit={handleSubmit} className="two-col" style={{ gridTemplateColumns: "1.2fr 0.8fr", gap: 26 }}>
        <div>
          <h4 style={{ marginBottom: 12 }}><span className="step-badge">1</span> Customer Information</h4>
          <div className="field-row">
            <div className="field"><label>Full Name</label><input required value={form.name} onChange={(e) => update("name", e.target.value)} /></div>
            <div className="field"><label>Contact Number</label><input required placeholder="09xx xxx xxxx" value={form.phone} onChange={(e) => update("phone", e.target.value)} /></div>
          </div>
          <div className="field"><label>Email Address</label><input required type="email" value={form.email} onChange={(e) => update("email", e.target.value)} /></div>

          {savedAddresses.length > 0 && (
            <div className="field">
              <label>Deliver to</label>
              <div className="seg" role="group" aria-label="Deliver to">
                {savedAddresses.map((a) => (
                  <button type="button" key={a.id} className={addressChoice === String(a.id) ? "active" : ""} onClick={() => chooseAddress(String(a.id))}>{a.label}</button>
                ))}
                <button type="button" className={addressChoice === "new" ? "active" : ""} onClick={() => chooseAddress("new")}>New address</button>
              </div>
              {addressChoice !== "new" && savedAddresses.find((a) => String(a.id) === addressChoice) && (
                <div className="addr-box">{savedAddresses.find((a) => String(a.id) === addressChoice).formatted}</div>
              )}
              <p className="field-hint">Manage your saved addresses in My Account &gt; Addresses.</p>
            </div>
          )}
          <h4 style={{ margin: "18px 0 12px" }}><span className="step-badge">2</span> Delivery Address</h4>
          {(savedAddresses.length === 0 || addressChoice === "new") && (
            <>
            <div className="field"><label htmlFor="ck-type">Address type</label>
              <select id="ck-type" value={form.addressType || "Home"} onChange={(e) => update("addressType", e.target.value)}>
                <option value="Home">Home</option><option value="Work">Work</option>
                <option value="Temporary">Temporary</option><option value="Other">Other</option>
              </select>
            </div>
            <div className="field"><label>Street Address</label><input required placeholder="House/Unit No., Street, Barangay" value={form.line1} onChange={(e) => update("line1", e.target.value)} /></div>
            <div className="field-row">
              <div className="field"><label>City / Municipality</label><input required value={form.city} onChange={(e) => update("city", e.target.value)} /></div>
              <div className="field"><label>Province</label><input required value={form.province} onChange={(e) => update("province", e.target.value)} /></div>
            </div>
            <div className="field-row">
              <div className="field"><label>Region</label><input required value={form.region} onChange={(e) => update("region", e.target.value)} /></div>
              <div className="field"><label>ZIP Code</label><input required value={form.zip} onChange={(e) => update("zip", e.target.value)} /></div>
            </div>

            {anyBoxed && (
              <p className="field-hint" style={{ marginBottom: 10 }}>
                Your order: {totalBoxes} box{totalBoxes === 1 ? "" : "es"}.
                {isBusiness
                  ? ` Business accounts can order up to ${boxLimit} boxes per order. Orders of ${rules.reviewBoxes} boxes or more are bulk orders, paid in advance by card or GCash.`
                  : ` Personal accounts can order up to ${boxLimit} boxes per order. For bigger orders, register a business account.`}
              </p>
            )}
            {bulk && (
              <p className="field-hint" style={{ marginBottom: 10, color: "var(--warn-fg)" }}>
                This is a bulk order ({totalBoxes} boxes). Cash on delivery is not available for bulk orders.
              </p>
            )}
            {duplicateOrder && (
              <ConfirmDialog
                title="Is this a new order?" confirmLabel="Place a new order" danger={false}
                message={`You placed the same order a few minutes ago (${duplicateOrder}). Place another one?`}
                onCancel={() => setDuplicateOrder(null)}
                onConfirm={() => { setDuplicateOrder(null); placeOrder(true); }}
              />
            )}
            </>
          )}
          <h4 style={{ margin: "18px 0 12px" }}><span className="step-badge">3</span> Payment Method</h4>
          <div className="pay-options">
            {PAYMENT_OPTIONS.map((opt) => {
              const available = opt.value === "Cash on Delivery" ? !bulk : methods[opt.value] === true;
              return (
                <label key={opt.value} className={`pay-option ${form.payment === opt.value ? "selected" : ""} ${available ? "" : "disabled"}`}>
                  <input
                    type="radio" name="payment" value={opt.value}
                    checked={form.payment === opt.value} disabled={!available}
                    onChange={() => update("payment", opt.value)}
                  />
                  <div>
                    <div style={{ fontWeight: 700, fontSize: 14 }}>
                      {opt.label} <span className="pay-tag">{opt.tag}</span>{!available && <span className="pay-soon"> Not available yet</span>}
                    </div>
                    <div style={{ fontSize: 12.5, color: "var(--muted)" }}>{opt.hint}</div>
                  </div>
                </label>
              );
            })}
          </div>
        </div>

        <div className="panel checkout-summary">
          <h4 style={{ marginBottom: 12 }}>Order Summary</h4>
          <div className="checkout-items">
            {lines.map((l) => <CheckoutItem key={l.product.id} line={l} onOpen={setViewing} />)}
          </div>
          {savings > 0 && (
            <div className="cart-summary-row" style={{ color: "var(--ok-text)", fontWeight: 600, marginTop: 10 }}>
              <span>Savings</span><span>-{peso(savings)}</span>
            </div>
          )}
          <div className="cart-summary-row"><span>Subtotal</span><span>{peso(subtotal)}</span></div>
          <div className="cart-summary-row"><span>Shipping</span><span>{shipping === 0 ? "FREE" : peso(shipping)}</span></div>
          <div className="cart-summary-row total"><span>Total</span><span>{peso(total)}</span></div>
          <button type="submit" className="btn btn-primary btn-block" style={{ marginTop: 16 }} disabled={submitting}>
            {buttonLabel}
          </button>
          <p className="field-hint" style={{ textAlign: "center", marginTop: 8 }}>
            Free shipping on orders of {peso(FREE_SHIPPING_SUBTOTAL)}+ or 10+ items. Bulk discounts apply automatically.
          </p>
        </div>
      </form>
      {viewing && <ProductModal product={viewing} onClose={() => setViewing(null)} />}
    </div>
  );
}
