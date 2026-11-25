import { useEffect, useRef } from "react";
import JsBarcode from "jsbarcode";
import { peso } from "../utils/format";

/**
 * Package sticker, 100 mm x 75 mm: red header with the order number, the customer, a COD or PAID bar,
 * then three boxes: QR code, barcode, and the customer's signature. Every section has a fixed height so
 * nothing overlaps when printed. Separate from the official receipt.
 */
export default function StickerDocument({ sticker, qrUrl }) {
  const barcodeRef = useRef(null);

  useEffect(() => {
    if (!barcodeRef.current || !sticker?.barcodeValue) return;
    JsBarcode(barcodeRef.current, sticker.barcodeValue, {
      format: "CODE128", displayValue: false, height: 60, width: 1.6, margin: 0,
    });
  }, [sticker?.barcodeValue]);

  if (!sticker) return null;
  const cod = sticker.payment.codAmountToCollect > 0;

  return (
    <div className="sticker" aria-label={`Sticker for ${sticker.orderNumber}`}>
      <div className="sticker-band">
        <span className="sticker-brand">RAINCHEM</span>
        <span className="sticker-order">{sticker.orderNumber}</span>
      </div>

      <div className="sticker-cust">
        <div className="sticker-name">{sticker.customer.name}</div>
        <div className="sticker-phone">{sticker.customer.phone} · {sticker.itemCount} item(s)</div>
        <div className="sticker-addr">{sticker.customer.address}</div>
      </div>

      <div className={`sticker-pay ${cod ? "cod" : "paid"}`}>
        {cod ? `CASH ON DELIVERY · COLLECT ${peso(sticker.payment.codAmountToCollect)}` : "PAID"}
      </div>

      <div className="sticker-row">
        <div className="sticker-box sticker-qrbox">
          {qrUrl ? <img src={qrUrl} alt={`QR code for ${sticker.orderNumber}`} /> : <div className="sticker-qr-empty">QR</div>}
          <span>Scan to verify</span>
        </div>
        <div className="sticker-box sticker-barbox">
          <svg ref={barcodeRef} role="img" aria-label={`Barcode ${sticker.barcodeValue}`} />
          <span>{sticker.barcodeValue}</span>
        </div>
        <div className="sticker-box sticker-signbox">
          <span>Customer signature</span>
        </div>
      </div>
    </div>
  );
}
