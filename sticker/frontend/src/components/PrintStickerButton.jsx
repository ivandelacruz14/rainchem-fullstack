import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import client from "../api/client";
import { useToast } from "../context/ToastContext";
import StickerDocument from "./StickerDocument";

/** Loads the order's sticker and shows it in a preview first, like the receipt. The admin checks it,
 *  then taps Print sticker. While the preview is open, printing shows only the sticker (see site.css). */
export default function PrintStickerButton({ orderId, label = "Print sticker" }) {
  const showToast = useToast();
  const [sticker, setSticker] = useState(null);
  const [qrUrl, setQrUrl] = useState(null);
  const [busy, setBusy] = useState(false);

  async function prepare() {
    setBusy(true);
    try {
      const [s, q] = await Promise.all([
        client.get(`/api/admin/orders/${orderId}/sticker`),
        client.get(`/api/admin/orders/${orderId}/receipt/qr.png`, { responseType: "blob" }),
      ]);
      setQrUrl(URL.createObjectURL(q.data));
      setSticker(s.data.sticker);
    } catch (err) {
      showToast(err.response?.data?.error || "The sticker could not be prepared.", "error");
    } finally {
      setBusy(false);
    }
  }

  function close() {
    setSticker(null);
    if (qrUrl) URL.revokeObjectURL(qrUrl);
    setQrUrl(null);
  }

  // While the preview is open, printing shows only the sticker.
  const open = Boolean(sticker && qrUrl);
  useEffect(() => {
    if (!open) return undefined;
    document.body.classList.add("printing-sticker");
    return () => document.body.classList.remove("printing-sticker");
  }, [open]);

  return (
    <>
      <button type="button" className="btn btn-primary btn-sm" disabled={busy} onClick={prepare}>
        {busy ? "Preparing..." : label}
      </button>
      {open && createPortal(
        <div className="sticker-overlay" role="dialog" aria-label={`Sticker preview for ${sticker.orderNumber}`}>
          <div className="sticker-sheet">
            <div className="no-print receipt-toolbar">
              <strong>Sticker preview</strong>
              <div style={{ display: "flex", gap: 10 }}>
                <button type="button" className="btn btn-outline btn-sm" onClick={close}>Close</button>
                <button type="button" className="btn btn-primary btn-sm" onClick={() => window.print()}>Print sticker</button>
              </div>
            </div>
            <p className="no-print sticker-tip">Check the details first. In the print window, choose paper size 4 x 6 in, Margins: None, and turn off Headers and footers.</p>
            <div className="sticker-stage"><StickerDocument sticker={sticker} qrUrl={qrUrl} /></div>
          </div>
        </div>,
        document.body
      )}
    </>
  );
}
