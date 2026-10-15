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
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit() {
    if (!rating) {
      setError("Please choose a star rating");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await client.post(`/api/orders/${order.id}/review`, { rating, comment });
      onDone("Thanks for your review!");
    } catch (err) {
      setError(err.response?.data?.error || "Could not save your review");
      setBusy(false);
    }
  }

  return (
    <Shell title="Rate your order" onClose={onClose}>
      <p style={{ marginTop: 0, fontSize: 13.5, color: "var(--muted)" }}>
        {order.orderNumber}: {order.items.map((i) => i.name).join(", ")}
      </p>
      {error && <div className="alert alert-error">{error}</div>}
      <StarPicker value={rating} onChange={setRating} />
      <div className="field" style={{ marginTop: 14 }}>
        <label>Comment (optional)</label>
        <textarea rows={3} maxLength={500} value={comment} onChange={(e) => setComment(e.target.value)} placeholder="How was the product and the delivery?" />
      </div>
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
