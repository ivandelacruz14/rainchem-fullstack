import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import client from "../api/client";
import { peso, formatDate } from "../utils/format";

export default function Receipt() {
  const { orderId } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    client
      .get(`/api/orders/${orderId}/receipt`)
      .then((res) => setData(res.data))
      .catch((err) => setError(err.response?.data?.error || "Receipt not available"));
  }, [orderId]);

  if (error) {
    return (
      <div className="container" style={{ padding: "60px 24px", textAlign: "center" }}>
        <div className="alert alert-error" style={{ maxWidth: 420, margin: "0 auto" }}>{error}</div>
        <button className="btn btn-outline" style={{ marginTop: 16 }} onClick={() => navigate("/account/orders")}>Back to My Orders</button>
      </div>
    );
  }

  if (!data) return null;
  const { order, receipt } = data;

  return (
    <div className="container">
      <div className="receipt-page">
        <div className="no-print" style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginBottom: 16 }}>
          <button className="btn btn-outline btn-sm" onClick={() => navigate("/account/orders")}>Back</button>
          <button className="btn btn-primary btn-sm" onClick={() => window.print()}>Print Receipt</button>
        </div>

        <div className="receipt-header">
          <div>
            <div className="brand" style={{ fontSize: 20 }}><span className="dot"></span>Rain<span className="sub">chem</span></div>
            <p style={{ fontSize: 12, color: "#75706a", margin: "4px 0 0" }}>Rainchem International Inc.<br />Paranaque City, Metro Manila</p>
          </div>
          <div style={{ textAlign: "right" }}>
            <h3 style={{ margin: 0 }}>Official Receipt</h3>
            <p className="mono" style={{ fontSize: 13, margin: "4px 0 0" }}>{receipt.receiptNumber}</p>
            <p style={{ fontSize: 12, color: "#75706a" }}>{formatDate(receipt.issuedAt)}</p>
          </div>
        </div>

        <div className="field-row">
          <div>
            <strong style={{ fontSize: 12.5 }}>Billed To</strong>
            <p style={{ fontSize: 13.5, margin: "4px 0 0" }}>
              {order.customer.name}<br />{order.customer.phone}<br />{order.customer.email}
            </p>
          </div>
          <div>
            <strong style={{ fontSize: 12.5 }}>Order Details</strong>
            <p style={{ fontSize: 13.5, margin: "4px 0 0" }}>
              Order: {order.orderNumber}<br />Tracking: {order.trackingNumber}<br />Payment: {order.paymentMethod}
            </p>
          </div>
        </div>

        <table className="receipt-table">
          <thead>
            <tr><th>Item</th><th>Qty</th><th>Unit Price</th><th>Total</th></tr>
          </thead>
          <tbody>
            {receipt.items.map((item, i) => (
              <tr key={i}>
                <td>{item.name}</td>
                <td>{item.quantity}</td>
                <td>{peso(item.unitPrice)}</td>
                <td>{peso(item.lineTotal)}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <div style={{ marginLeft: "auto", maxWidth: 260 }}>
          <div className="cart-summary-row"><span>Subtotal</span><span>{peso(receipt.subtotal)}</span></div>
          <div className="cart-summary-row"><span>Shipping</span><span>{receipt.shippingFee === 0 ? "FREE" : peso(receipt.shippingFee)}</span></div>
          <div className="cart-summary-row total"><span>Total</span><span>{peso(receipt.total)}</span></div>
        </div>

        <p style={{ fontSize: 12, color: "#8a8580", marginTop: 24, textAlign: "center" }}>
          Thank you for choosing Rainchem. This receipt was generated after your order was confirmed.
        </p>
      </div>
    </div>
  );
}
