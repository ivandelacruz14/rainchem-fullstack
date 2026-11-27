import { useEffect, useRef } from "react";
import JsBarcode from "jsbarcode";
import { formatDate, peso } from "../utils/format";

const MAX_ROWS = 4;

/**
 * Package sticker, 4 x 6 in (portrait), laid out like the Delivery Receipt: red header, order bar,
 * customer information, item table with the total, QR code and barcode, and the customer acknowledgment
 * with a signature box. The signature box takes whatever height is left, so the label has no empty gaps.
 * The size is set in the stylesheet (--sticker-w and --sticker-h). Use the same label size in the printer.
 */
export default function StickerDocument({ sticker, qrUrl }) {
  const barcodeRef = useRef(null);

  useEffect(() => {
    if (!barcodeRef.current || !sticker?.barcodeValue) return;
    JsBarcode(barcodeRef.current, sticker.barcodeValue, {
      format: "CODE128", displayValue: false, height: 60, width: 2, margin: 0,
    });
  }, [sticker?.barcodeValue]);

  if (!sticker) return null;
  const cod = sticker.payment.codAmountToCollect > 0;
  const items = sticker.items || [];
  const shown = items.slice(0, MAX_ROWS);
  const hidden = items.length - shown.length;
  const total = sticker.total ?? items.reduce((sum, i) => sum + (i.subtotal || 0), 0);

  return (
    <div className="sticker" aria-label={`Sticker for ${sticker.orderNumber}`}>
      <div className="st-head">
        <div className="st-brand">
          <strong>RAINCHEM</strong>
          <span>INTERNATIONAL, INC.</span>
          <em>Drive Clean. Go Further.</em>
        </div>
        <div className="st-title">
          <strong>DELIVERY RECEIPT</strong>
          <em>PROOF OF DELIVERY</em>
        </div>
      </div>

      <div className="st-bar">
        <div><span>ORDER NUMBER</span><strong>{sticker.orderNumber}</strong></div>
        <div><span>ORDER DATE</span><strong>{sticker.orderDate ? formatDate(sticker.orderDate) : "-"}</strong></div>
        <div className={`st-badge ${cod ? "cod" : "paid"}`}>{cod ? "COD" : "PAID"}</div>
      </div>

      <div className="st-sec">CUSTOMER INFORMATION</div>
      <dl className="st-cust">
        <dt>Full Name</dt><dd className="st-strong">{sticker.customer.name}</dd>
        <dt>Contact Number</dt><dd className="st-strong">{sticker.customer.phone}</dd>
        <dt>Delivery Address</dt><dd>{sticker.customer.address}</dd>
      </dl>

      <div className="st-sec">ITEM INFORMATION</div>
      <table className="st-items">
        <thead><tr><th>Product</th><th>SKU</th><th>Qty</th><th>Price</th><th>Subtotal</th></tr></thead>
        <tbody>
          {shown.map((i, idx) => (
            <tr key={`${i.productId}-${idx}`}>
              <td className="st-prod">{i.name}</td>
              <td>{i.sku || "-"}</td>
              <td>{i.quantity}</td>
              <td>{peso(i.unitPrice)}</td>
              <td>{peso(i.subtotal)}</td>
            </tr>
          ))}
          {hidden > 0 && <tr><td colSpan={5} className="st-more">+ {hidden} more item(s) on the receipt</td></tr>}
          {items.length === 0 && <tr><td colSpan={5} className="st-more">{sticker.itemCount} item(s)</td></tr>}
        </tbody>
      </table>

      <div className="st-total"><span>TOTAL AMOUNT</span><strong>{peso(total)}</strong></div>
      <div className="st-pay">
        <span>Payment Method: <b>{sticker.payment.method}</b></span>
        {cod && <span>COD to be collected: <b>{peso(sticker.payment.codAmountToCollect)}</b></span>}
      </div>

      <div className="st-codes">
        <div className="st-box st-qrbox">
          <div className="st-boxhead">QR CODE</div>
          {qrUrl ? <img src={qrUrl} alt={`QR code for ${sticker.orderNumber}`} /> : <div className="st-qr-empty">QR</div>}
          <span>Scan to verify this order</span>
        </div>
        <div className="st-box st-barbox">
          <div className="st-boxhead">BARCODE</div>
          <svg ref={barcodeRef} role="img" aria-label={`Barcode ${sticker.barcodeValue}`} />
          <span>{sticker.barcodeValue}</span>
        </div>
      </div>

      <div className="st-sec">CUSTOMER ACKNOWLEDGMENT</div>
      <p className="st-ack">I acknowledge that I have received the items listed above in good condition.</p>
      <div className="st-sign">
        <div className="st-signbox"><span>Customer Signature</span></div>
        <div className="st-signinfo">
          <div><span>Printed Name</span><i /></div>
          <div><span>Date &amp; Time</span><i /></div>
        </div>
      </div>

      <div className="st-foot">
        <strong>Thank you for choosing Rainchem!</strong>
        <span>Rainchem International, Inc.</span>
      </div>
    </div>
  );
}
