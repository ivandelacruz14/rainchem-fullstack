import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import client from "../../api/client";
import OrderJourney from "../../components/journey/OrderJourney";
import { useUI } from "../../context/UIContext";
import { peso } from "../../utils/format";

export default function AccountTrack() {
  const [params, setParams] = useSearchParams();
  const { openLiveChat } = useUI();
  const [query, setQuery] = useState(params.get("order") || "");
  const [order, setOrder] = useState(null);
  const [orders, setOrders] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const lookup = useCallback(async (value) => {
    const term = value.trim();
    if (!term) return;
    setLoading(true);
    setError("");
    try {
      const res = await client.get(`/api/orders/track/${encodeURIComponent(term)}`);
      setOrder(res.data.order);
    } catch (err) {
      setOrder(null);
      setError(err.response?.status === 404
        ? "We could not find an order with that number in your account. Check the order number or tracking number and try again."
        : err.response?.data?.error || "The order could not be loaded. Please try again.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    client.get("/api/orders").then((res) => setOrders(res.data.orders)).catch(() => {});
  }, []);

  useEffect(() => {
    const fromLink = params.get("order");
    if (fromLink) {
      setQuery(fromLink);
      lookup(fromLink);
    }
  }, [params, lookup]);

  function submit(e) {
    e.preventDefault();
    if (query.trim()) setParams({ order: query.trim() });
  }

  return (
    <div className="track-page">
      <h2>Track My Order</h2>
      <p className="field-hint" style={{ marginTop: 0 }}>See where your Rainchem order is on its journey. Only orders in your own account can be tracked.</p>

      <form className="track-search" onSubmit={submit}>
        <input
          value={query} onChange={(e) => setQuery(e.target.value)} aria-label="Order number or tracking number"
          placeholder="Order number or tracking number"
        />
        <button type="submit" className="btn btn-primary" disabled={loading || !query.trim()}>{loading ? "Looking..." : "Track"}</button>
      </form>

      {orders.length > 0 && (
        <div className="track-recent">
          <span>Your orders</span>
          {orders.slice(0, 6).map((o) => (
            <button
              key={o.id} type="button" className={`chip ${order?.id === o.id ? "active" : ""}`}
              onClick={() => setParams({ order: o.orderNumber })}
            >
              {o.orderNumber} &middot; {o.journey?.headline || o.statusLabel}
            </button>
          ))}
        </div>
      )}

      {error && <div className="alert alert-error" role="alert">{error}</div>}

      {order && (
        <>
          <OrderJourney order={order} />

          <div className="journey-details">
            <div className="journey-card">
              <h3>Products ordered</h3>
              <ul className="journey-items">
                {order.items.map((item) => (
                  <li key={item.id || item.name}>
                    <span>{item.name} <span className="muted">x {item.quantity}</span></span>
                    <strong>{peso(item.lineTotal)}</strong>
                  </li>
                ))}
              </ul>
              <div className="journey-total"><span>Total</span><strong>{peso(order.total)}</strong></div>
            </div>
            <div className="journey-card">
              <h3>Delivery details</h3>
              <p className="journey-address">
                <strong>{order.customer.name}</strong><br />
                {order.customer.phone}<br />
                {order.address.line1}<br />
                {[order.address.city, order.address.province].filter(Boolean).join(", ")} {order.address.zip}<br />
                {order.address.region}
              </p>
              <h3 style={{ marginTop: 14 }}>Payment</h3>
              <p className="journey-address">{order.paymentMethod} &middot; {order.paymentStatusLabel}</p>
            </div>
          </div>

          <div className="journey-help">
            <span>Questions about this order?</span>
            <button type="button" className="btn btn-outline btn-sm" onClick={() => openLiveChat({ topic: "order", orderId: order.id })}>
              Message the admin about this order
            </button>
          </div>
        </>
      )}
    </div>
  );
}
