import { useState } from "react";
import client from "../../api/client";
import OrderCard from "../../components/OrderCard";

export default function AccountTrack() {
  const [trackingNumber, setTrackingNumber] = useState("");
  const [order, setOrder] = useState(null);
  const [error, setError] = useState("");

  async function handleTrack() {
    setError("");
    setOrder(null);
    try {
      const res = await client.get(`/api/orders/track/${trackingNumber.trim()}`);
      setOrder(res.data.order);
    } catch (err) {
      setError(err.response?.data?.error || "No order found with that tracking number.");
    }
  }

  return (
    <div>
      <h2>Track an Order</h2>
      <div className="field" style={{ maxWidth: 360 }}>
        <label>Tracking Number</label>
        <input
          value={trackingNumber}
          onChange={(e) => setTrackingNumber(e.target.value)}
          placeholder="e.g. RC-TRK-88213"
        />
      </div>
      <button className="btn btn-primary" onClick={handleTrack}>Track</button>
      <div style={{ marginTop: 20 }}>
        {error && <div className="alert alert-error">{error}</div>}
        {order && <OrderCard order={order} />}
      </div>
    </div>
  );
}
