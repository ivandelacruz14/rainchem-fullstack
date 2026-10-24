import { useEffect, useState } from "react";
import client from "../../api/client";
import { formatDate, peso } from "../../utils/format";

export default function DistributorOrders() {
  const [orders, setOrders] = useState(null);

  useEffect(() => {
    client.get("/api/admin/orders").then((res) => setOrders(res.data.orders)).catch(() => setOrders([]));
  }, []);

  return (
    <div>
      <div className="admin-topbar"><div><h1>Orders</h1><p>Orders that include your products. Customer contact and payment details are not shown.</p></div></div>
      <div className="admin-panel">
        <div className="table-wrap">
          <table className="admin-table">
            <thead><tr><th>Order</th><th>Date</th><th>Your items</th><th>Your total</th><th>Area</th><th>Status</th></tr></thead>
            <tbody>
              {!orders && <tr><td colSpan={6}>Loading...</td></tr>}
              {orders?.length === 0 && <tr><td colSpan={6}>No orders include your products yet.</td></tr>}
              {orders?.map((o) => (
                <tr key={o.id}>
                  <td className="mono">{o.orderNumber}</td>
                  <td>{formatDate(o.createdAt).split(",")[0]}</td>
                  <td className="wrap-cell">{o.items.map((i) => `${i.name} x ${i.quantity}`).join(", ")}</td>
                  <td>{peso(o.ownItemsTotal)}</td>
                  <td className="wrap-cell">{[o.address.city, o.address.province].filter(Boolean).join(", ")}</td>
                  <td><span className={`status-pill status-${o.status}`}>{o.statusLabel}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
