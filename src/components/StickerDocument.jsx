import { useEffect, useRef } from "react";
import JsBarcode from "jsbarcode";
import { peso } from "../utils/format";

/**
 * Package sticker, 100 mm x 75 mm. Each part sits at a fixed position in millimetres, so it prints the same
 * everywhere. Only borders and dark text are used, so it looks right with or without background graphics.
 * Separate from the official receipt.
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
    <div className="stk" aria-label={`Sticker for ${sticker.orderNumber}`}>
      <div className="stk-brand">RAINCHEM</div>
      <div className="stk-order">{sticker.orderNumber}</div>
      <div className="stk-rule" />

      <div className="stk-name">{sticker.customer.name}</div>
      <div className="stk-phone">{sticker.customer.phone} · {sticker.itemCount} item(s)</div>
      <div className="stk-addr">{sticker.customer.address}</div>

      <div className={`stk-pay ${cod ? "cod" : "paid"}`}>
        {cod ? `CASH ON DELIVERY · COLLECT ${peso(sticker.payment.codAmountToCollect)}` : "PAID"}
      </div>

      <div className="stk-box stk-qr">
        {qrUrl ? <img src={qrUrl} alt={`QR code for ${sticker.orderNumber}`} /> : <div className="stk-qr-empty">QR</div>}
        <span>Scan to verify</span>
      </div>

      <div className="stk-box stk-bar">
        <svg ref={barcodeRef} role="img" aria-label={`Barcode ${sticker.barcodeValue}`} />
        <span className="stk-bar-text">{sticker.barcodeValue}</span>
      </div>

      <div className="stk-box stk-sign">
        <span>Customer signature</span>
      </div>
    </div>
  );
}
