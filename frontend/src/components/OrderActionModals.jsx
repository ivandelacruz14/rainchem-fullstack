import { useState } from "react";
import client from "../api/client";

function StarPicker({ value, onChange }) {
  const [hover, setHover] = useState(0);
  const labels = ["Poor", "Fair", "Good", "Very good", "Excellent"];
  return (
    <div>
      <div className="star-picker" onMouseLeave={() => setHover(0)}>
        {[1, 2, 3, 4, 5].map((n) => (
          <button
            key={n} type="button" aria-label={`${n} star${n > 1 ? "s" : ""}`}
            className={n <= (hover || value) ? "on" : ""}
            onMouseEnter={() => setHover(n)} onClick={() => onChange(n)}
          >
            &#9733;
          </button>
        ))}
      </div>
      <div className="field-hint">{value ? labels[value - 1] : "Tap a star to rate"}</div>
    </div>
  );
}

function Shell({ title, onClose, children }) {
  return (
    <div className="overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h3 style={{ margin: 0, fontSize: 19 }}>{title}</h3>
          <button type="button" className="modal-close" onClick={onClose}>&times;</button>
        </div>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  );
}

export function ReviewModal({ order, onClose, onDone }) {
  const items = order.reviewableItems || [];
  const [entries, setEntries] = useState(() => Object.fromEntries(items.map((i) => [i.productId, { rating: 0, comment: "" }])));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  function change(productId, patch) {
    setEntries((prev) => ({ ...prev, [productId]: { ...prev[productId], ...patch } }));
  }

  async function submit() {
    const reviews = items
      .filter((i) => entries[i.productId].rating > 0)
      .map((i) => ({ productId: i.productId, ...entries[i.productId] }));
    if (reviews.length === 0) {
      setError("Please choose a star rating for at least one product");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await client.post(`/api/orders/${order.id}/reviews`, { reviews });
      onDone("Thanks for your review!");
    } catch (err) {
      setError(err.response?.data?.error || "Could not save your review");
      setBusy(false);
    }
  }

  return (
    <Shell title="Rate your products" onClose={onClose}>
      <p style={{ marginTop: 0, fontSize: 13.5, color: "var(--muted)" }}>
        Order {order.orderNumber}. Each product can be reviewed once.
      </p>
      {error && <div className="alert alert-error">{error}</div>}
      {items.map((item) => (
        <div className="review-form-item" key={item.productId}>
          <strong>{item.name}</strong>
          <StarPicker value={entries[item.productId].rating} onChange={(rating) => change(item.productId, { rating })} />
          <textarea
            rows={2} maxLength={500} value={entries[item.productId].comment}
            onChange={(e) => change(item.productId, { comment: e.target.value })}
            placeholder="Share how this product worked for you (optional)"
          />
        </div>
      ))}
      <button className="btn btn-primary btn-block" disabled={busy} onClick={submit}>{busy ? "Sending..." : "Submit review"}</button>
    </Shell>
  );
}

const REASONS = ["Item is damaged", "Wrong item received", "Item is not as described", "Missing item(s)", "Other"];

export function ReturnModal({ order, onClose, onDone }) {
  const [reason, setReason] = useState(REASONS[0]);
  const [details, setDetails] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit() {
    const text = details.trim() ? `${reason}: ${details.trim()}` : reason;
    setBusy(true);
    setError("");
    try {
      await client.post(`/api/orders/${order.id}/return`, { reason: text });
      onDone("Return request sent. We'll review it and email you.");
    } catch (err) {
      setError(err.response?.data?.error || "Could not send your return request");
      setBusy(false);
    }
  }

  return (
    <Shell title="Request a return" onClose={onClose}>
      <p style={{ marginTop: 0, fontSize: 13.5, color: "var(--muted)" }}>
        {order.orderNumber}. Returns can be requested within {order.returnWindowDays} days after delivery.
      </p>
      {error && <div className="alert alert-error">{error}</div>}
      <div className="field">
        <label>Reason</label>
        <select value={reason} onChange={(e) => setReason(e.target.value)}>
          {REASONS.map((r) => <option key={r}>{r}</option>)}
        </select>
      </div>
      <div className="field">
        <label>Details (optional)</label>
        <textarea rows={3} maxLength={400} value={details} onChange={(e) => setDetails(e.target.value)} placeholder="Tell us what happened" />
      </div>
      <button className="btn btn-primary btn-block" disabled={busy} onClick={submit}>{busy ? "Sending..." : "Submit return request"}</button>
    </Shell>
  );
}
