import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import client from "../api/client";
import { peso } from "../utils/format";
import { resizeImage } from "../utils/imageResize";
import { useToast } from "../context/ToastContext";

const METHODS = [
  { value: "GCash", label: "GCash", hint: "Send the exact amount to our GCash, then enter the reference number." },
  { value: "Credit / Debit Card", label: "Credit / Debit Card", hint: "Pay on a secure card page. We never see your card number." },
  { value: "Cash on Delivery", label: "Cash on Delivery", hint: "Pay in cash when your order arrives." },
];

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);
  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard blocked: the number is still on screen to copy by hand */
    }
  }
  return (
    <button type="button" className="btn btn-outline btn-sm" onClick={copy}>{copied ? "Copied" : "Copy"}</button>
  );
}

function GcashPanel({ order, gcash, onSubmitted }) {
  const showToast = useToast();
  const [reference, setReference] = useState(order.paymentReference || "");
  const [proof, setProof] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const fileRef = useRef(null);
  const verifying = order.paymentStatus === "verifying";
  const [editing, setEditing] = useState(!verifying);

  async function pickFile(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      setProof(await resizeImage(file, 900));
    } catch {
      setError("That file could not be read. Please choose a screenshot (JPG or PNG).");
    }
  }

  async function submit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const res = await client.post(`/api/payments/orders/${order.id}/gcash`, { reference, proof });
      showToast("Payment details sent. We'll verify them shortly.", "success");
      setEditing(false);
      onSubmitted(res.data.order);
    } catch (err) {
      setError(err.response?.data?.error || "Could not send your payment details. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <div className="gcash-box">
        <div className="gcash-amount">
          <span>Amount to send</span>
          <strong>{peso(order.total)}</strong>
        </div>

        {gcash.dynamicQr ? (
          <div style={{ textAlign: "center" }}>
            <img className="gcash-qr" src={gcash.dynamicQr} alt={`GCash QR code for ${peso(order.total)}`} />
            <div className="field-hint">Scan this with the GCash app. The amount is already filled in.</div>
          </div>
        ) : (
          gcash.qr && <img className="gcash-qr" src={gcash.qr} alt="GCash QR code" />
        )}

        {gcash.number && (
          <div className="gcash-row">
            <div>
              <div className="field-hint">GCash number</div>
              <div className="mono" style={{ fontSize: 20, fontWeight: 700 }}>{gcash.number}</div>
              {gcash.accountName && <div style={{ fontSize: 13, color: "var(--muted)" }}>Account name: {gcash.accountName}</div>}
            </div>
            <CopyButton text={gcash.number.replace(/\s/g, "")} />
          </div>
        )}

        {gcash.link && (
          <a className="btn btn-primary btn-block" style={{ marginTop: 12 }} href={gcash.link} target="_blank" rel="noopener noreferrer">
            Open GCash payment link
          </a>
        )}

        {gcash.note && <p className="field-hint" style={{ marginTop: 10 }}>{gcash.note}</p>}
        <ol className="gcash-steps">
          <li>Send exactly <strong>{peso(order.total)}</strong> using the number, QR, or link above.</li>
          <li>Copy the <strong>reference number</strong> from your GCash receipt.</li>
          <li>Enter it below. We'll verify it and confirm your order.</li>
        </ol>
      </div>

      {verifying && !editing ? (
        <div className="alert alert-info" style={{ marginTop: 16 }}>
          <strong>Payment submitted. Waiting for verification.</strong>
          <div style={{ marginTop: 4 }}>Reference: <span className="mono">{order.paymentReference}</span></div>
          <button type="button" className="link-btn" style={{ marginTop: 8 }} onClick={() => setEditing(true)}>
            Wrong reference? Send it again
          </button>
        </div>
      ) : (
        <form onSubmit={submit} style={{ marginTop: 16 }}>
          {error && <div className="alert alert-error">{error}</div>}
          <div className="field">
            <label>GCash Reference Number</label>
            <input
              required value={reference} placeholder="e.g. 1234 567 890123"
              onChange={(e) => setReference(e.target.value)}
            />
          </div>
          <div className="field">
            <label>Screenshot of your payment (optional)</label>
            <input ref={fileRef} type="file" accept="image/*" onChange={pickFile} />
            {proof && <img src={proof} alt="Payment screenshot preview" style={{ maxWidth: 160, marginTop: 8, borderRadius: 8, border: "1px solid var(--line)" }} />}
          </div>
          <button type="submit" className="btn btn-primary btn-block" disabled={busy}>
            {busy ? "Sending..." : "I've paid, send my details"}
          </button>
        </form>
      )}
    </div>
  );
}

function CardPanel({ order, available }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function pay() {
    setBusy(true);
    setError("");
    try {
      const res = await client.post(`/api/payments/orders/${order.id}/checkout`);
      window.location.href = res.data.checkoutUrl;
    } catch (err) {
      setError(err.response?.data?.error || "Could not open the card page. Please try again.");
      setBusy(false);
    }
  }

  if (!available) {
    return <div className="alert alert-error">Card payment is not available right now. Please pick GCash or Cash on Delivery.</div>;
  }
  return (
    <div>
      {error && <div className="alert alert-error">{error}</div>}
      <p style={{ color: "var(--muted)", fontSize: 14 }}>
        You'll be taken to a secure card page to pay <strong>{peso(order.total)}</strong>. You can come back and pick a different method any time before you pay.
      </p>
      <button type="button" className="btn btn-primary btn-block" disabled={busy} onClick={pay}>
        {busy ? "Please wait..." : `Pay ${peso(order.total)} by card`}
      </button>
    </div>
  );
}

function CodPanel({ order }) {
  const navigate = useNavigate();
  return (
    <div>
      <p style={{ color: "var(--muted)", fontSize: 14 }}>
        Nothing to pay now. Please prepare <strong>{peso(order.total)}</strong> in cash for the rider. Our team will confirm your order shortly.
      </p>
      <button type="button" className="btn btn-primary btn-block" onClick={() => navigate("/order-success", { state: { order } })}>
        Continue
      </button>
    </div>
  );
}

export default function PaymentPage() {
  const { orderId } = useParams();
  const navigate = useNavigate();
  const showToast = useToast();
  const [info, setInfo] = useState(null);
  const [error, setError] = useState("");
  const [switching, setSwitching] = useState(false);

  function load() {
    return client.get(`/api/payments/orders/${orderId}`)
      .then((res) => setInfo(res.data))
      .catch((err) => setError(err.response?.data?.error || "Could not load this payment page."));
  }
  useEffect(() => { load(); }, [orderId]); // eslint-disable-line react-hooks/exhaustive-deps

  async function chooseMethod(method) {
    if (!info || method === info.order.paymentMethod || switching) return;
    setSwitching(true);
    try {
      await client.post(`/api/payments/orders/${orderId}/method`, { method });
      await load();
    } catch (err) {
      showToast(err.response?.data?.error || "Could not change the payment method", "error");
    } finally {
      setSwitching(false);
    }
  }

  if (error) {
    return (
      <div className="container" style={{ padding: "60px 24px", textAlign: "center", maxWidth: 520 }}>
        <div className="alert alert-error">{error}</div>
        <Link to="/account/orders" className="btn btn-outline">Go to My Orders</Link>
      </div>
    );
  }
  if (!info) return null;

  const { order, methods, gcash } = info;
  const method = order.paymentMethod;

  if (order.status === "cancelled" || order.paymentStatus === "paid") {
    const paid = order.paymentStatus === "paid";
    return (
      <div className="container" style={{ padding: "60px 24px", textAlign: "center", maxWidth: 520 }}>
        <h3>{paid ? "This order is already paid" : "This order was cancelled"}</h3>
        <p style={{ color: "var(--muted)" }}>Order <span className="mono">{order.orderNumber}</span></p>
        <Link to="/account/orders" className="btn btn-primary btn-block">View My Orders</Link>
      </div>
    );
  }

  const canChange = order.canChangePayment;

  return (
    <div className="container" style={{ padding: "40px 24px 80px", maxWidth: 640 }}>
      <h1 style={{ marginBottom: 4 }}>Complete your payment</h1>
      <p style={{ color: "var(--muted)", marginBottom: 20 }}>
        Order <span className="mono">{order.orderNumber}</span> &middot; Total <strong>{peso(order.total)}</strong>
      </p>

      <div className="panel" style={{ marginBottom: 18 }}>
        <h4 style={{ marginBottom: 12 }}>{canChange ? "Choose how to pay" : "Payment method"}</h4>
        <div className="pay-options">
          {METHODS.map((opt) => {
            const available = methods[opt.value] === true;
            const selected = method === opt.value;
            const disabled = !selected && (!available || !canChange);
            return (
              <label key={opt.value} className={`pay-option ${selected ? "selected" : ""} ${disabled ? "disabled" : ""}`}>
                <input
                  type="radio" name="pay-method" value={opt.value}
                  checked={selected} disabled={disabled || switching}
                  onChange={() => chooseMethod(opt.value)}
                />
                <div>
                  <div style={{ fontWeight: 700, fontSize: 14 }}>
                    {opt.label}{!available && !selected && <span className="pay-soon"> Not available yet</span>}
                  </div>
                  <div style={{ fontSize: 12.5, color: "var(--muted)" }}>{opt.hint}</div>
                </div>
              </label>
            );
          })}
        </div>
      </div>

      <div className="panel">
        <h4 style={{ marginBottom: 12 }}>
          {method === "GCash" ? "Pay with GCash" : method === "Credit / Debit Card" ? "Pay by card" : "Cash on Delivery"}
        </h4>
        {method === "GCash" && gcash && (
          <GcashPanel key={`${order.paymentStatus}-${order.paymentReference}`} order={order} gcash={gcash} onSubmitted={() => load()} />
        )}
        {method === "Credit / Debit Card" && <CardPanel order={order} available={methods[method] === true} />}
        {method === "Cash on Delivery" && <CodPanel order={order} />}
      </div>

      <div style={{ textAlign: "center", marginTop: 18 }}>
        <button type="button" className="link-btn" onClick={() => navigate("/account/orders?tab=to_pay")}>
          Pay later from My Orders
        </button>
      </div>
    </div>
  );
}
