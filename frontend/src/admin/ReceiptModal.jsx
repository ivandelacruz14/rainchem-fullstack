import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import client from "../api/client";
import ReceiptView from "../components/ReceiptView";

/** Shows an order's receipt to the admin with a Print button. Opens right after
 *  an order is confirmed, and from the order detail for any confirmed order. */
export default function ReceiptModal({ orderId, onClose }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    client
      .get(`/api/admin/orders/${orderId}/receipt`)
      .then((res) => setData(res.data))
      .catch((err) => setError(err.response?.data?.error || "Could not load the receipt"));
  }, [orderId]);

  // While open, printing shows only the receipt (see "@media print" in site.css).
  useEffect(() => {
    document.body.classList.add("print-receipt");
    return () => document.body.classList.remove("print-receipt");
  }, []);

  return createPortal(
    <div className="receipt-overlay">
      <div className="receipt-sheet">
        <div className="no-print receipt-toolbar">
          <strong>Receipt</strong>
          <div style={{ display: "flex", gap: 10 }}>
            <button type="button" className="btn btn-outline btn-sm" onClick={onClose}>Close</button>
            <button type="button" className="btn btn-primary btn-sm" disabled={!data} onClick={() => window.print()}>
              Print Receipt
            </button>
          </div>
        </div>
        {error && <div className="alert alert-error no-print">{error}</div>}
        {!data && !error && <p className="no-print" style={{ textAlign: "center", color: "var(--soft)" }}>Loading receipt...</p>}
        {data && <ReceiptView order={data.order} receipt={data.receipt} />}
      </div>
    </div>,
    document.body,
  );
}
