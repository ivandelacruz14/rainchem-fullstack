import { useState } from "react";
import client from "../api/client";
import { useToast } from "../context/ToastContext";
import { downloadFile } from "../utils/download";

/** Official payment receipt (PDF). Only shown for a verified, paid order; the server checks this again. */
export default function PaymentReceiptButton({ order }) {
  const showToast = useToast();
  const [busy, setBusy] = useState(false);

  async function download() {
    setBusy(true);
    try {
      await downloadFile(client, `/api/receipts/orders/${order.id}.pdf`, {}, `${order.orderNumber}-payment-receipt.pdf`);
    } catch (err) {
      showToast(err.response?.data?.error || "The receipt could not be downloaded", "error");
    } finally {
      setBusy(false);
    }
  }

  if (order.paymentStatus !== "paid") return null;
  return (
    <button type="button" className="btn btn-outline btn-sm" onClick={download} disabled={busy}>
      {busy ? "Preparing..." : "Download payment receipt"}
    </button>
  );
}
