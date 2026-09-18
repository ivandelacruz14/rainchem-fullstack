import { Link } from "react-router-dom";
import { peso, formatDate } from "../utils/format";

const STEPS = ["pending_confirmation", "confirmed", "processing", "shipped", "delivered"];

export default function OrderCard({ order, onCancel }) {
  const isCancelled = order.status === "cancelled";
  const currentIndex = STEPS.indexOf(order.status);

  return (
    <div className="order-card">
      <div className="order-card-top">
        <div>
          <div className="mono" style={{ fontWeight: 700 }}>{order.orderNumber}</div>
          <div style={{ fontSize: 12, color: "#8a8580" }}>
            {formatDate(order.createdAt)} &middot; Tracking: <span className="mono">{order.trackingNumber}</span>
          </div>
        </div>
        <span className={`status-pill status-${order.status}`}>{order.statusLabel}</span>
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
      <div className="cart-summary-row total" style={{ marginTop: 10 }}>
        <span>Total</span><span>{peso(order.total)}</span>
      </div>

      <div style={{ display: "flex", gap: 10, marginTop: 12 }}>
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
