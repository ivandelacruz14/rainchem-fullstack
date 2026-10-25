import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import client from "../../api/client";
import { useToast } from "../../context/ToastContext";
import { formatDate, peso } from "../../utils/format";

export default function AccountServices() {
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const showToast = useToast();

  function load() {
    client.get("/api/services/bookings").then((res) => setBookings(res.data.bookings)).finally(() => setLoading(false));
  }
  useEffect(load, []);

  async function cancel(id) {
    if (!window.confirm("Cancel this service request?")) return;
    try {
      await client.post(`/api/services/bookings/${id}/cancel`);
      showToast("Request cancelled", "success");
      load();
    } catch (err) {
      showToast(err.response?.data?.error || "Could not cancel this request", "error");
    }
  }

  return (
    <div>
      <h2>Service Requests</h2>
      {loading ? null : bookings.length === 0 ? (
        <div className="empty-state">
          No service requests yet. <Link to="/services" style={{ color: "var(--red-700)", fontWeight: 600 }}>Browse services</Link>
        </div>
      ) : (
        bookings.map((b) => (
          <div className="order-card" key={b.id}>
            <div className="order-card-top">
              <div>
                <div className="mono" style={{ fontWeight: 700 }}>{b.bookingNumber}</div>
                <div style={{ fontSize: 12, color: "var(--soft)" }}>{formatDate(b.createdAt)}</div>
              </div>
              <span className={`status-pill booking-${b.status}`}>{b.statusLabel}</span>
            </div>
            <div style={{ fontWeight: 600 }}>{b.serviceName}</div>
            <div style={{ fontSize: 13.5, color: "var(--muted)" }}>{b.area} &middot; {b.address}</div>
            {b.preferredDate && <div style={{ fontSize: 13, color: "var(--soft)" }}>Preferred date: {b.preferredDate}</div>}
            <div className="cart-summary-row total" style={{ marginTop: 10 }}><span>Price</span><span>{peso(b.price)}</span></div>
            {b.canCancel && (
              <button className="btn btn-outline btn-sm" style={{ marginTop: 10 }} onClick={() => cancel(b.id)}>Cancel request</button>
            )}
          </div>
        ))
      )}
    </div>
  );
}
