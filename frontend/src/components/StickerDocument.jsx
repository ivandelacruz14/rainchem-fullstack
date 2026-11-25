import { useEffect, useRef } from "react";
import JsBarcode from "jsbarcode";
import { peso } from "../utils/format";

/** The package sticker: QR code and barcode for the order, the customer, and whether cash is to be collected or the order is paid.
 *  Separate from the official receipt. Printed at 100 mm x 60 mm. */
export default function StickerDocument({ sticker, qrUrl }) {
  const barcodeRef = useRef(null);
  useEffect(() => {
    if (!barcodeRef.current || !sticker?.barcodeValue) return;
    JsBarcode(barcodeRef.current, sticker.barcodeValue, { format: "CODE128", displayValue: true, height: 40, margin: 0, fontSize: 11 });
  }, [sticker?.barcodeValue]);

  if (!sticker) return null;
  const cod = sticker.payment.codAmountToCollect > 0;
  return (
    <div className="sticker print-area" aria-label={`Sticker for ${sticker.orderNumber}`}>
      <div className="sticker-qr">
        {qrUrl ? <img src={qrUrl} alt={`QR code for ${sticker.orderNumber}`} /> : <div className="sticker-qr-empty">QR</div>}
      </div>
      <div className="sticker-body">
        <div className="sticker-order">{sticker.orderNumber}</div>
        <svg ref={barcodeRef} className="sticker-barcode" aria-label={`Barcode ${sticker.barcodeValue}`} />
        <div className="sticker-customer">
          <strong>{sticker.customer.name}</strong>
          <span>{sticker.customer.phone}</span>
          <span className="sticker-address">{sticker.customer.address}</span>
        </div>
        <div className={`sticker-pay ${cod ? "cod" : "paid"}`}>
          {cod ? <>CASH ON DELIVERY · COLLECT {peso(sticker.payment.codAmountToCollect)}</> : <>PAID</>}
        </div>
        <div className="sticker-foot">{sticker.itemCount} item(s) · Rainchem International, Inc.</div>
      </div>
    </div>
  );
}
