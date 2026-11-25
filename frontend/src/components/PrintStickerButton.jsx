import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import client from "../api/client";
import { useToast } from "../context/ToastContext";
import StickerDocument from "./StickerDocument";

/** Loads the order's sticker and prints only that sticker. The app page is hidden while printing. */
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

  // Print when the sticker is on the page. Keep it there until the print dialog closes.
  useEffect(() => {
    if (!sticker || !qrUrl) return undefined;
    document.body.classList.add("printing-sticker");
    const t = setTimeout(() => window.print(), 250);
    const clear = () => setSticker(null);
    window.addEventListener("afterprint", clear);
    return () => {
      clearTimeout(t);
      window.removeEventListener("afterprint", clear);
      document.body.classList.remove("printing-sticker");
    };
  }, [sticker, qrUrl]);

  useEffect(() => {
    if (sticker || !qrUrl) return;
    URL.revokeObjectURL(qrUrl);
    setQrUrl(null);
  }, [sticker, qrUrl]);

  return (
    <>
      <button type="button" className="btn btn-primary btn-sm" disabled={busy} onClick={prepare}>
        {busy ? "Preparing..." : label}
      </button>
      {sticker && qrUrl && createPortal(
        <div className="print-root"><StickerDocument sticker={sticker} qrUrl={qrUrl} /></div>,
        document.body
      )}
    </>
  );
}
