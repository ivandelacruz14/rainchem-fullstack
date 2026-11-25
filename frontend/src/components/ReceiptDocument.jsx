import { useEffect, useRef } from "react";
import JsBarcode from "jsbarcode";
import { peso, formatDate } from "../utils/format";

/** The delivery receipt. Every value comes from the server, which reads it from the stored order. */
export default function ReceiptDocument({ receipt, qrUrl, signatureUrl }) {
  const barcodeRef = useRef(null);

  useEffect(() => {
    if (!barcodeRef.current || !receipt?.barcodeValue) return;
    JsBarcode(barcodeRef.current, receipt.barcodeValue, { format: "CODE128", displayValue: true, height: 56, margin: 0, fontSize: 14 });
  }, [receipt?.barcodeValue]);

  if (!receipt) return null;
  const payment = receipt.payment;
  const stage = { awaiting_receipt: "Awaiting receipt", pending_verification: "Pending verification", verified: "Verified", delivered: "Delivered", not_out_for_delivery: "Not yet out for delivery" }[receipt.deliveryStage] || receipt.deliveryStage;

  return (
    <article className="receipt-doc print-area" aria-label="Delivery receipt">
      <header className="receipt-head">
        <div>
          <div className="receipt-brand">RAINCHEM INTERNATIONAL, INC.</div>
          <div className="receipt-tag">Drive clean. Go further.</div>
        </div>
        <div className="receipt-title">
          <strong>DELIVERY RECEIPT</strong>
          <span>Proof of Delivery</span>
        </div>
      </header>

      <section className="receipt-meta">
        <div><span>Order number</span><strong>{receipt.orderNumber}</strong></div>
        <div><span>Order date</span><strong>{receipt.orderDate ? formatDate(receipt.orderDate) : "-"}</strong></div>
        <div><span>Delivery date</span><strong>{receipt.deliveryDate ? formatDate(receipt.deliveryDate) : "-"}</strong></div>
        <div><span>Status</span><strong>{stage}</strong></div>
      </section>

      <section className="receipt-block">
        <h4>Customer information</h4>
        <dl className="receipt-dl">
          <dt>Full name</dt><dd>{receipt.customer.name}</dd>
          <dt>Contact number</dt><dd>{receipt.customer.phone}</dd>
          <dt>Delivery address</dt><dd>{receipt.customer.address}</dd>
        </dl>
      </section>

      <section className="receipt-block">
        <h4>Items</h4>
        <table className="receipt-table">
          <thead>
            <tr><th>Product</th><th>SKU</th><th className="num">Qty</th><th className="num">Unit price</th><th className="num">Subtotal</th></tr>
          </thead>
          <tbody>
            {receipt.items.map((i, idx) => (
              <tr key={`${i.productId}-${idx}`}>
                <td>{i.name}{i.discountRate > 0 && <div className="receipt-note">{Math.round(i.discountRate * 100)}% discount applied</div>}</td>
                <td>{i.sku || "-"}</td>
                <td className="num">{i.quantity}</td>
                <td className="num">{peso(i.unitPrice)}</td>
                <td className="num">{peso(i.subtotal)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="receipt-totals">
          <div><span>Subtotal</span><span>{peso(receipt.subtotal)}</span></div>
          {receipt.discount > 0 && <div><span>Discount</span><span>-{peso(receipt.discount)}</span></div>}
          <div><span>Shipping fee</span><span>{peso(receipt.shippingFee)}</span></div>
          <div className="receipt-grand"><span>Total amount</span><span>{peso(receipt.total)}</span></div>
        </div>
      </section>

      <section className="receipt-pay">
        <div>
          <span>Payment method</span>
          <strong>{payment.method}{payment.isPrepaid ? " (prepaid)" : " (cash on delivery)"}</strong>
          <span>Payment status: {payment.isPaid ? "Paid" : "Unpaid"}</span>
        </div>
        {payment.codAmountToCollect > 0 ? (
          <div className="receipt-cod"><span>Amount to collect from customer</span><strong>{peso(payment.codAmountToCollect)}</strong></div>
        ) : (
          <div className="receipt-cod receipt-cod-paid"><span>Nothing to collect</span><strong>Paid in advance</strong></div>
        )}
      </section>

      <section className="receipt-codes">
        <div className="receipt-code-box">
          {qrUrl ? <img src={qrUrl} alt={`QR code for order ${receipt.orderNumber}`} /> : <div className="receipt-code-empty">QR</div>}
          <span>Scan to verify this order</span>
        </div>
        <div className="receipt-code-box receipt-barcode">
          <svg ref={barcodeRef} aria-label={`Barcode ${receipt.barcodeValue}`} />
        </div>
      </section>

      <section className="receipt-block receipt-ack">
        <h4>Customer acknowledgement</h4>
        <p>I acknowledge that I have received the items listed above in good condition.</p>
        <div className="receipt-sign-row">
          <div className="receipt-sign-box">
            {signatureUrl ? <img src={signatureUrl} alt="Customer signature" /> : <div className="receipt-sign-empty" />}
            <span>Customer signature</span>
          </div>
          <dl className="receipt-dl">
            <dt>Printed name</dt><dd>{receipt.upload?.printedName || "________________"}</dd>
            <dt>Date and time</dt><dd>{receipt.upload?.acknowledgedAt ? formatDate(receipt.upload.acknowledgedAt) : "________________"}</dd>
            <dt>Delivered by</dt><dd>{receipt.rider || "________________"}</dd>
          </dl>
        </div>
      </section>

      <footer className="receipt-foot">Thank you for choosing Rainchem.</footer>
    </article>
  );
}
