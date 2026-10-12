import { Link } from "react-router-dom";
import { peso, formatDate } from "../utils/format";

const STEPS = ["pending_confirmation", "confirmed", "processing", "shipped", "delivered"];

function Stars({ value }) {
  return (
    <span style={{ color: "#f5b301", letterSpacing: 1 }}>
      {"\u2605".repeat(value)}<span style={{ color: "#c9c4bc" }}>{"\u2605".repeat(5 - value)}</span>
    </span>
  );
}

export default function OrderCard({ order, onCancel, onPay, onReceive, onReview, onReturn }) {
  const isCancelled = order.status === "cancelled";
  const currentIndex = STEPS.indexOf(order.status);
  const ret = order.returnInfo;

  return (
    <div className="order-card">
      <div className="order-card-top">
        <div>
          <div className="mono" style={{ fontWeight: 700 }}>{order.orderNumber}</div>
          <div style={{ fontSize: 12, color: "#8a8580" }}>
            {formatDate(order.createdAt)} &middot; Tracking: <span className="mono">{order.trackingNumber}</span>
          </div>
        </div>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "flex-start" }}>
          <span className={`pay-pill pay-${order.paymentStatus}`}>{order.paymentStatusLabel}</span>
          <span className={`status-pill status-${order.status}`}>{order.statusLabel}</span>
        </div>
      </div>

      {!isCancelled && (
        <div className="track-steps">
          {STEPS.map((step, i) => (
            <div key={step} className={`track-step ${i <= currentIndex ? "done" : ""}`}>
              <div className="dot">{i <= currentIndex ? "\u2713" : ""}</div>
              {step === "pending_confirmation" ? "Placed" : step.charAt(0).toUpperCase() + step.slice(1)}
            </div>
          ))}
        </div>
      )}

      <div style={{ marginTop: 14, fontSize: 13.5, color: "#57524c" }}>
        {order.items.map((it) => `${it.name} x ${it.quantity}`).join(", ")}
      </div>
      <div style={{ fontSize: 12.5, color: "#8a8580", marginTop: 6 }}>Payment: {order.paymentMethod}</div>

      {order.canPay && (
        <div className="order-note warn">Waiting for your {order.paymentMethod} payment. Please pay so we can process this order.</div>
      )}
      {order.paymentStatus === "refund_pending" && (
        <div className="order-note">Your refund is being processed by our team.</div>
      )}
      {ret && ret.status !== "none" && (
        <div className="order-note">
          <strong>{ret.statusLabel}.</strong> Reason: {ret.reason}
          {ret.note && <div style={{ marginTop: 4 }}>Note from Rainchem: {ret.note}</div>}
        </div>
      )}
      {order.review && (
        <div className="order-note">Your review: <Stars value={order.review.rating} />{order.review.comment ? ` "${order.review.comment}"` : ""}</div>
      )}

      <div className="cart-summary-row total" style={{ marginTop: 10 }}>
        <span>Total</span><span>{peso(order.total)}</span>
      </div>

      <div style={{ display: "flex", gap: 10, marginTop: 12, flexWrap: "wrap" }}>
        {order.canPay && onPay && (
          <button className="btn btn-primary btn-sm" onClick={() => onPay(order.id)}>Pay Now</button>
        )}
        {order.canReceive && onReceive && (
          <button className="btn btn-primary btn-sm" onClick={() => onReceive(order.id)}>Order Received</button>
        )}
        {order.canReview && onReview && (
          <button className="btn btn-primary btn-sm" onClick={() => onReview(order)}>Rate Order</button>
        )}
        {order.canReturn && onReturn && (
          <button className="btn btn-outline btn-sm" onClick={() => onReturn(order)}>Return</button>
        )}
        {order.canCancel && onCancel && (
          <button className="btn btn-outline btn-sm" style={{ borderColor: "var(--red-700)", color: "var(--red-700)" }} onClick={() => onCancel(order.id)}>
            Cancel Order
          </button>
        )}
        {order.hasReceipt && (
          <Link to={`/receipt/${order.id}`} className="btn btn-outline btn-sm">Print Receipt</Link>
        )}
      </div>
    </div>
  );
}
