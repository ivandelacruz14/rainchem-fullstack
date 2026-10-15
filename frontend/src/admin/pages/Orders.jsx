import { useState, useEffect } from "react";
import client from "../../api/client";
import { peso, formatDate } from "../../utils/format";
import { useToast } from "../../context/ToastContext";
import ReceiptModal from "../ReceiptModal";

const STATUSES = ["All", "verifying", "pending_confirmation", "confirmed", "processing", "shipped", "delivered", "cancelled", "returns"];
const LABELS = {
  All: "All", verifying: "Verify Payment", pending_confirmation: "Pending Confirmation", confirmed: "Confirmed",
  processing: "Processing", shipped: "Shipped", delivered: "Delivered", cancelled: "Cancelled", returns: "Returns",
};

export default function Orders() {
  const [orders, setOrders] = useState([]);
  const [tab, setTab] = useState("All");
  const [selected, setSelected] = useState(null);
  const [returnNote, setReturnNote] = useState("");
  const [receiptFor, setReceiptFor] = useState(null);
  const [proofImage, setProofImage] = useState(null);
  const showToast = useToast();

  function loadOrders() {
    const params = tab === "All" ? {} : { status: tab };
    client.get("/api/admin/orders", { params }).then((res) => setOrders(res.data.orders));
  }
  useEffect(loadOrders, [tab]);

  async function handleConfirm(orderId) {
    try {
      await client.post(`/api/admin/orders/${orderId}/confirm`);
      showToast("Order confirmed. The receipt is ready to print.", "success");
      loadOrders();
      setSelected(null);
      setReceiptFor(orderId); // open the receipt right away so it can be printed
    } catch (err) {
      showToast(err.response?.data?.error || "Could not confirm this order", "error");
    }
  }

  async function handleReturnDecision(orderId, decision) {
    try {
      await client.post(`/api/admin/orders/${orderId}/return/${decision}`, { note: returnNote });
      showToast(decision === "approve" ? "Return approved and items restocked" : "Return rejected", "success");
      setReturnNote("");
      loadOrders();
      setSelected(null);
    } catch (err) {
      showToast(err.response?.data?.error || "Could not update this return", "error");
    }
  }

  async function handleVerifyPayment(orderId) {
    try {
      const res = await client.post(`/api/admin/orders/${orderId}/payment/verify`);
      showToast("Payment marked as received. You can now confirm the order.", "success");
      setSelected(res.data.order);
      loadOrders();
    } catch (err) {
      showToast(err.response?.data?.error || "Could not update this payment", "error");
    }
  }

  async function handleRejectPayment(orderId) {
    const note = window.prompt("Tell the customer why (optional), e.g. \"No payment found for that reference\":", "");
    if (note === null) return;
    try {
      const res = await client.post(`/api/admin/orders/${orderId}/payment/reject`, { note });
      showToast("Payment rejected. The customer was emailed.", "success");
      setSelected(res.data.order);
      loadOrders();
    } catch (err) {
      showToast(err.response?.data?.error || "Could not reject this payment", "error");
    }
  }

  async function handleViewProof(orderId) {
    try {
      const res = await client.get(`/api/admin/orders/${orderId}/payment-proof`);
      if (res.data.proof) setProofImage(res.data.proof);
      else showToast("No screenshot was uploaded", "error");
    } catch (err) {
      showToast(err.response?.data?.error || "Could not load the screenshot", "error");
    }
  }

  async function handleRefunded(orderId) {
    try {
      await client.post(`/api/admin/orders/${orderId}/refunded`);
      showToast("Marked as refunded", "success");
      loadOrders();
      setSelected(null);
    } catch (err) {
      showToast(err.response?.data?.error || "Could not update this order", "error");
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
            <thead><tr><th>Order</th><th>Customer</th><th>Date</th><th>Items</th><th>Total</th><th>Payment</th><th>Status</th><th>Tracking</th><th></th></tr></thead>
            <tbody>
              {orders.length === 0 ? (
                <tr><td colSpan={9}>No orders in this status.</td></tr>
              ) : (
                orders.map((o) => (
                  <tr key={o.id}>
                    <td className="mono">{o.orderNumber}</td>
                    <td>{o.customer.name}</td>
                    <td>{formatDate(o.createdAt).split(",")[0]}</td>
                    <td>{o.items.reduce((s, i) => s + i.quantity, 0)} item(s)</td>
                    <td>{peso(o.total)}</td>
                    <td><span className={`pay-pill pay-${o.paymentStatus}`}>{o.paymentStatusLabel}</span></td>
                    <td>
                      <span className={`status-pill status-${o.status}`}>{o.statusLabel}</span>
                      {o.returnInfo.status === "requested" && <div style={{ fontSize: 11, color: "var(--warn-fg)", marginTop: 4, fontWeight: 700 }}>Return requested</div>}
                    </td>
                    <td className="mono" style={{ fontSize: 12 }}>{o.trackingNumber}</td>
                    <td style={{ whiteSpace: "nowrap" }}>
                      <button className="icon-action" style={{ width: "auto", padding: "0 10px" }} onClick={() => { setReturnNote(""); setSelected(o); }}>View</button>
                      {o.hasReceipt && (
                        <button className="icon-action" style={{ width: "auto", padding: "0 10px", marginLeft: 6 }} onClick={() => setReceiptFor(o.id)}>Print</button>
                      )}
                    </td>
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
              <div style={{ fontSize: 12, color: "var(--soft)", marginBottom: 14 }}>Placed {formatDate(selected.createdAt)}</div>
              <div className="panel" style={{ background: "var(--fog)", border: "none" }}>
                <strong>Customer</strong>
                <p style={{ margin: "6px 0 0" }}>{selected.customer.name}<br />{selected.customer.phone}<br />{selected.customer.email}</p>
                <strong>Delivery Address</strong>
                <p style={{ margin: "6px 0 0" }}>{selected.address.line1}, {selected.address.city}, {selected.address.province}, {selected.address.region} {selected.address.zip}</p>
                <strong>Payment</strong>
                <p style={{ margin: "6px 0 0" }}>{selected.paymentMethod} &middot; <span className={`pay-pill pay-${selected.paymentStatus}`}>{selected.paymentStatusLabel}</span></p>
              </div>
              <strong>Items</strong>
              {selected.items.map((it, i) => (
                <div className="cart-summary-row" key={i}><span>{it.name} x {it.quantity}</span><span>{peso(it.lineTotal)}</span></div>
              ))}
              <div className="cart-summary-row total"><span>Total</span><span>{peso(selected.total)}</span></div>

              {selected.review && (
                <div className="order-note" style={{ marginTop: 12 }}>
                  Customer review: {"\u2605".repeat(selected.review.rating)}{"\u2606".repeat(5 - selected.review.rating)}
                  {selected.review.comment ? ` "${selected.review.comment}"` : ""}
                </div>
              )}

              {selected.returnInfo.status !== "none" && (
                <div className="order-note warn" style={{ marginTop: 12 }}>
                  <strong>{selected.returnInfo.statusLabel}</strong>: {selected.returnInfo.reason}
                  {selected.returnInfo.note && <div style={{ marginTop: 4 }}>Your note: {selected.returnInfo.note}</div>}
                </div>
              )}
              {selected.returnInfo.status === "requested" && (
                <div style={{ marginTop: 10 }}>
                  <div className="field"><label>Note to customer (optional)</label>
                    <input value={returnNote} maxLength={500} onChange={(e) => setReturnNote(e.target.value)} />
                  </div>
                  <div style={{ display: "flex", gap: 10 }}>
                    <button className="btn btn-primary" onClick={() => handleReturnDecision(selected.id, "approve")}>Approve return</button>
                    <button className="btn btn-outline" onClick={() => handleReturnDecision(selected.id, "reject")}>Reject</button>
                  </div>
                </div>
              )}

              {selected.paymentStatus === "refund_pending" && (
                <button className="btn btn-outline btn-block" style={{ marginTop: 14 }} onClick={() => handleRefunded(selected.id)}>
                  Mark payment as refunded
                </button>
              )}

              {selected.paymentMethod === "GCash" && selected.paymentStatus !== "paid" && selected.status !== "cancelled" && (
                <div className="order-note warn" style={{ marginTop: 16 }}>
                  {selected.paymentStatus === "verifying" ? (
                    <>
                      <strong>GCash payment submitted.</strong> Reference: <span className="mono">{selected.paymentReference}</span>
                      {selected.paymentSubmittedAt && <> &middot; {formatDate(selected.paymentSubmittedAt)}</>}
                      <div style={{ marginTop: 4 }}>Check it in your GCash account for {peso(selected.total)}, then mark it as received.</div>
                    </>
                  ) : (
                    <>The customer has not sent a GCash reference number yet. If you already received the payment, you can mark it as received.</>
                  )}
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 10 }}>
                    {selected.hasPaymentProof && (
                      <button type="button" className="btn btn-outline btn-sm" onClick={() => handleViewProof(selected.id)}>View screenshot</button>
                    )}
                    <button type="button" className="btn btn-primary btn-sm" onClick={() => handleVerifyPayment(selected.id)}>Mark payment as received</button>
                    {selected.paymentStatus === "verifying" && (
                      <button type="button" className="btn btn-outline btn-sm" onClick={() => handleRejectPayment(selected.id)}>Reject</button>
                    )}
                  </div>
                </div>
              )}
              {selected.status === "pending_confirmation" && selected.paymentMethod !== "Cash on Delivery" && selected.paymentMethod !== "GCash" && selected.paymentStatus !== "paid" && (
                <div className="order-note warn" style={{ marginTop: 16 }}>
                  Waiting for the customer's {selected.paymentMethod} payment. You can confirm this order once it is paid.
                </div>
              )}
              {selected.status === "pending_confirmation" && (selected.paymentMethod === "Cash on Delivery" || selected.paymentStatus === "paid") && (
                <button className="btn btn-primary btn-block" style={{ marginTop: 16 }} onClick={() => handleConfirm(selected.id)}>
                  Confirm Order &amp; Generate Receipt
                </button>
              )}

              {(selected.hasReceipt || ["confirmed", "processing", "shipped", "delivered"].includes(selected.status)) && (
                <button className="btn btn-outline btn-block" style={{ marginTop: 16 }} onClick={() => setReceiptFor(selected.id)}>
                  Print Receipt
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

      {receiptFor && <ReceiptModal orderId={receiptFor} onClose={() => setReceiptFor(null)} />}

      {proofImage && (
        <div className="overlay" style={{ zIndex: 800 }} onClick={() => setProofImage(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head"><h3 style={{ margin: 0 }}>Payment screenshot</h3><button className="modal-close" onClick={() => setProofImage(null)}>&times;</button></div>
            <div className="modal-body"><img src={proofImage} alt="GCash payment screenshot" style={{ width: "100%", borderRadius: 8 }} /></div>
          </div>
        </div>
      )}
    </div>
  );
}
