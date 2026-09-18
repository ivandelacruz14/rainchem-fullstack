import { useState, useEffect } from "react";
import client from "../../api/client";
import { peso, formatDate } from "../../utils/format";
import { useToast } from "../../context/ToastContext";

const STATUSES = ["All", "pending_confirmation", "confirmed", "processing", "shipped", "delivered", "cancelled"];
const LABELS = {
  All: "All", pending_confirmation: "Pending Confirmation", confirmed: "Confirmed",
  processing: "Processing", shipped: "Shipped", delivered: "Delivered", cancelled: "Cancelled",
};

export default function Orders() {
  const [orders, setOrders] = useState([]);
  const [tab, setTab] = useState("All");
  const [selected, setSelected] = useState(null);
  const showToast = useToast();

  function loadOrders() {
    const params = tab === "All" ? {} : { status: tab };
    client.get("/api/admin/orders", { params }).then((res) => setOrders(res.data.orders));
  }
  useEffect(loadOrders, [tab]);

  async function handleConfirm(orderId) {
    try {
      await client.post(`/api/admin/orders/${orderId}/confirm`);
      showToast("Order confirmed and receipt generated", "success");
      loadOrders();
      setSelected(null);
    } catch (err) {
      showToast(err.response?.data?.error || "Could not confirm this order", "error");
    }
  }

  async function handleStatusChange(orderId, status) {
    try {
      await client.post(`/api/admin/orders/${orderId}/status`, { status });
      showToast("Order updated", "success");
      loadOrders();
      setSelected(null);
    } catch (err) {
      showToast(err.response?.data?.error || "Could not update this order", "error");
    }
  }

  return (
    <div>
      <div className="admin-topbar"><div><h1>Orders</h1><p>Confirm new orders and track fulfillment status.</p></div></div>
      <div className="tab-bar">
        {STATUSES.map((s) => (
          <button key={s} className={`tab-btn ${tab === s ? "active" : ""}`} onClick={() => setTab(s)}>{LABELS[s]}</button>
        ))}
      </div>
      <div className="admin-panel">
        <div className="table-wrap">
          <table className="admin-table">
            <thead><tr><th>Order</th><th>Customer</th><th>Date</th><th>Items</th><th>Total</th><th>Status</th><th>Tracking</th><th></th></tr></thead>
            <tbody>
              {orders.length === 0 ? (
                <tr><td colSpan={8}>No orders in this status.</td></tr>
              ) : (
                orders.map((o) => (
                  <tr key={o.id}>
                    <td className="mono">{o.orderNumber}</td>
                    <td>{o.customer.name}</td>
                    <td>{formatDate(o.createdAt).split(",")[0]}</td>
                    <td>{o.items.reduce((s, i) => s + i.quantity, 0)} item(s)</td>
                    <td>{peso(o.total)}</td>
                    <td><span className={`status-pill status-${o.status}`}>{o.statusLabel}</span></td>
                    <td className="mono" style={{ fontSize: 12 }}>{o.trackingNumber}</td>
                    <td><button className="icon-action" onClick={() => setSelected(o)}>View</button></td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {selected && (
        <div className="overlay" onClick={() => setSelected(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head"><h3 style={{ margin: 0 }}>Order Detail</h3><button className="modal-close" onClick={() => setSelected(null)}>&times;</button></div>
            <div className="modal-body">
              <div className="mono" style={{ fontWeight: 700, fontSize: 16 }}>{selected.orderNumber}</div>
              <div style={{ fontSize: 12, color: "#8a8580", marginBottom: 14 }}>Placed {formatDate(selected.createdAt)}</div>
              <div className="panel" style={{ background: "var(--fog)", border: "none" }}>
                <strong>Customer</strong>
                <p style={{ margin: "6px 0 0" }}>{selected.customer.name}<br />{selected.customer.phone}<br />{selected.customer.email}</p>
                <strong>Delivery Address</strong>
                <p style={{ margin: "6px 0 0" }}>{selected.address.line1}, {selected.address.city}, {selected.address.province}, {selected.address.region} {selected.address.zip}</p>
                <strong>Payment</strong>
                <p style={{ margin: "6px 0 0" }}>{selected.paymentMethod}</p>
              </div>
              <strong>Items</strong>
              {selected.items.map((it, i) => (
                <div className="cart-summary-row" key={i}><span>{it.name} x {it.quantity}</span><span>{peso(it.lineTotal)}</span></div>
              ))}
              <div className="cart-summary-row total"><span>Total</span><span>{peso(selected.total)}</span></div>

              {selected.status === "pending_confirmation" && (
                <button className="btn btn-primary btn-block" style={{ marginTop: 16 }} onClick={() => handleConfirm(selected.id)}>
                  Confirm Order &amp; Generate Receipt
                </button>
              )}

              {["confirmed", "processing", "shipped", "delivered"].includes(selected.status) && (
                <div className="field" style={{ marginTop: 16 }}>
                  <label>Update Status</label>
                  <select defaultValue={selected.status} onChange={(e) => handleStatusChange(selected.id, e.target.value)}>
                    <option value="confirmed">Confirmed</option>
                    <option value="processing">Processing</option>
                    <option value="shipped">Shipped</option>
                    <option value="delivered">Delivered</option>
                  </select>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
