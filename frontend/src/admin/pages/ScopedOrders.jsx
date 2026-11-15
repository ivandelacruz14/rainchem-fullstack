import { useEffect, useState } from "react";
import client from "../../api/client";
import { formatDate, peso } from "../../utils/format";

export default function ScopedOrders() {
  const [orders, setOrders] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    client.get("/api/admin/orders")
      .then((res) => setOrders(res.data.orders))
      .catch(() => setError("Orders could not be loaded."));
  }, []);

  return (
    <div>
      <div className="admin-topbar">
        <div>
          <h1>Orders</h1>
          <p>Orders that include your products. You see your items, the customer's first name and the delivery area only.</p>
        </div>
      </div>
      {error && <div className="alert alert-error">{error}</div>}
      <div className="admin-panel">
        <div className="table-wrap">
          <table className="admin-table stack">
            <thead><tr><th>Order</th><th>Date</th><th>Customer</th><th>Area</th><th>Your items</th><th>Your subtotal</th><th>Status</th></tr></thead>
            <tbody>
              {orders === null ? (
                <tr><td colSpan={7}>Loading...</td></tr>
              ) : orders.length === 0 ? (
                <tr><td colSpan={7}>No orders include your products yet.</td></tr>
              ) : (
                orders.map((o) => (
                  <tr key={o.id}>
                    <td data-label="Order" className="mono">{o.orderNumber}</td>
                    <td data-label="Date">{formatDate(o.createdAt)}</td>
                    <td data-label="Customer">{o.customerFirstName}</td>
                    <td data-label="Area">{o.area}</td>
                    <td data-label="Your items">{o.items.map((i) => `${i.name} x ${i.quantity}`).join(", ")}</td>
                    <td data-label="Your subtotal">{peso(o.subtotal)}</td>
                    <td data-label="Status"><span className={`status-pill status-${o.status}`}>{o.statusLabel}</span></td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
