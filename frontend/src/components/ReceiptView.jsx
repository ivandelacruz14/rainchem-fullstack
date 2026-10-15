import { peso, formatDate } from "../utils/format";
import Brand from "./Brand";

/** The printable receipt. Used on the customer's receipt page and in the admin
 *  "Print receipt" window, so both always look the same. */
export default function ReceiptView({ order, receipt }) {
  const addr = order.address;
  return (
    <div className="receipt-page">
      <div className="receipt-header">
        <div>
          <div className="brand"><Brand height={80} /></div>
          <p style={{ fontSize: 12, color: "var(--soft)", margin: "4px 0 0" }}>
            Rainchem International Inc.<br />Paranaque City, Metro Manila
          </p>
        </div>
        <div style={{ textAlign: "right" }}>
          <h3 style={{ margin: 0 }}>Official Receipt</h3>
          <p className="mono" style={{ fontSize: 13, margin: "4px 0 0" }}>{receipt.receiptNumber}</p>
          <p style={{ fontSize: 12, color: "var(--soft)" }}>{formatDate(receipt.issuedAt)}</p>
        </div>
      </div>

      <div className="field-row">
        <div>
          <strong style={{ fontSize: 12.5 }}>Billed To</strong>
          <p style={{ fontSize: 13.5, margin: "4px 0 0" }}>
            {order.customer.name}<br />{order.customer.phone}<br />{order.customer.email}
          </p>
          <strong style={{ fontSize: 12.5, display: "block", marginTop: 10 }}>Deliver To</strong>
          <p style={{ fontSize: 13.5, margin: "4px 0 0" }}>
            {addr.line1}<br />{addr.city}, {addr.province}<br />{addr.region} {addr.zip}
          </p>
        </div>
        <div>
          <strong style={{ fontSize: 12.5 }}>Order Details</strong>
          <p style={{ fontSize: 13.5, margin: "4px 0 0" }}>
            Order: {order.orderNumber}<br />
            Tracking: {order.trackingNumber}<br />
            Payment: {order.paymentMethod}<br />
            Payment status: {order.paymentStatusLabel}
            {order.paymentReference && <><br />Reference: {order.paymentReference}</>}
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

      <p style={{ fontSize: 12, color: "var(--soft)", marginTop: 24, textAlign: "center" }}>
        Thank you for choosing Raimol. This receipt was generated after your order was confirmed.
      </p>
    </div>
  );
}
