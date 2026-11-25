import { useEffect, useRef } from "react";
import JsBarcode from "jsbarcode";
import { peso } from "../utils/format";

export default function StickerDocument({ sticker, qrUrl }) {
  const barcodeRef = useRef(null);

  useEffect(() => {
    if (!barcodeRef.current || !sticker?.barcodeValue) return;
    JsBarcode(barcodeRef.current, sticker.barcodeValue, { format: "CODE128", displayValue: false, height: 34, margin: 0 });
  }, [sticker?.barcodeValue]);

  if (!sticker) return null;
  const cod = sticker.payment.codAmountToCollect > 0;

  return (
    <div className="sticker" aria-label={`Sticker for ${sticker.orderNumber}`}>
      <div className="sticker-top">
        <div className="sticker-qr">
          {qrUrl ? <img src={qrUrl} alt={`QR code for ${sticker.orderNumber}`} /> : <div className="sticker-qr-empty">QR</div>}
        </div>
        <div className="sticker-id">
          <div className="sticker-order">{sticker.orderNumber}</div>
          <svg ref={barcodeRef} className="sticker-barcode" role="img" aria-label={`Barcode ${sticker.barcodeValue}`} />
          <div className="sticker-barcode-text">{sticker.barcodeValue}</div>
        </div>
      </div>

      <div className="sticker-customer">
        <div className="sticker-name">{sticker.customer.name}</div>
        <div className="sticker-phone">{sticker.customer.phone}</div>
        <div className="sticker-address">{sticker.customer.address}</div>
      </div>

      <div className="sticker-bottom">
        <div className={`sticker-pay ${cod ? "cod" : "paid"}`}>
          {cod ? <>CASH ON DELIVERY<br />COLLECT {peso(sticker.payment.codAmountToCollect)}</> : <>PAID</>}
          <div className="sticker-items">{sticker.itemCount} item(s)</div>
        </div>
        <div className="sticker-sign">
          <span>Customer signature</span>
        </div>
      </div>
    </div>
  );
}
