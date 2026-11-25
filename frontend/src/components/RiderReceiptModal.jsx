import { useEffect, useState } from "react";
import client from "../api/client";
import { useToast } from "../context/ToastContext";
import ReceiptDocument from "./ReceiptDocument";
import SignaturePad from "./SignaturePad";

const ACCEPTED = ["image/jpeg", "image/png", "image/webp", "application/pdf"];
const MAX_BYTES = 5 * 1024 * 1024;

/** The rider's receipt for one order: view and print it, then capture the customer's signature and upload the signed receipt. */
export default function RiderReceiptModal({ order, onClose, onChanged }) {
  const showToast = useToast();
  const [receipt, setReceipt] = useState(null);
  const [error, setError] = useState("");
  const [qrUrl, setQrUrl] = useState(null);
  const [signature, setSignature] = useState(null);
  const [printedName, setPrintedName] = useState("");
  const [acknowledged, setAcknowledged] = useState(false);
  const [file, setFile] = useState(null);
  const [fileError, setFileError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let url = null;
    let active = true;
    Promise.resolve()
      .then(() => client.get(`/api/rider/orders/${order.id}/receipt`))
      .then((res) => { if (active) setReceipt(res.data.receipt); })
      .catch((err) => { if (active) setError(err.response?.data?.error || "The receipt could not be loaded."); });
    client.get(`/api/rider/orders/${order.id}/receipt/qr.png`, { responseType: "blob" })
      .then((r) => { url = URL.createObjectURL(r.data); if (active) setQrUrl(url); })
      .catch(() => {});
    return () => { active = false; if (url) URL.revokeObjectURL(url); };
  }, [order.id]);

  const upload = receipt?.upload;
  const locked = upload && (upload.status === "pending_verification" || upload.status === "verified");
  const canSubmit = !busy && !locked && file && signature && printedName.trim().length >= 2 && acknowledged;

  function pickFile(e) {
    const f = e.target.files?.[0] || null;
    setFileError("");
    if (f && !ACCEPTED.includes(f.type)) { setFileError("Only JPG, PNG, WEBP, or PDF files are accepted."); setFile(null); return; }
    if (f && f.size > MAX_BYTES) { setFileError("The file is larger than 5 MB."); setFile(null); return; }
    setFile(f);
  }

  async function submit(e) {
    e.preventDefault();
    if (!canSubmit) return;
    setBusy(true);
    const form = new FormData();
    form.append("file", file);
    form.append("signature", signature);
    form.append("printedName", printedName.trim());
    form.append("acknowledged", "yes");
    try {
      await client.post(`/api/rider/orders/${order.id}/receipt-upload`, form);
      showToast("Receipt uploaded. Waiting for admin verification.", "success");
      onChanged?.();
      onClose();
    } catch (err) {
      showToast(err.response?.data?.error || "The receipt could not be uploaded.", "error");
    } finally {
      setBusy(false);
    }
  }

  function printReceipt() { window.print(); }

  return (
    <div className="overlay" onClick={onClose}>
      <div className="modal wide receipt-modal" role="dialog" aria-modal="true" aria-label="Delivery receipt" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h3 style={{ margin: 0 }}>Receipt for {order.orderNumber}</h3>
          <button type="button" className="modal-close" onClick={onClose} aria-label="Close">&times;</button>
        </div>
        <div className="modal-body">
          {error && <div className="alert alert-error" role="alert">{error}</div>}
          {!receipt && !error && <div className="loading-state" role="status"><span className="spinner" /> Loading the receipt...</div>}

          {receipt && (
            <>
              {upload?.status === "rejected" && (
                <div className="alert alert-error" role="alert">
                  The last receipt was rejected: {upload.rejectReason}. Capture the signature again and upload a corrected receipt.
                </div>
              )}
              {upload?.status === "pending_verification" && <div className="alert alert-info">Your receipt is waiting for admin verification.</div>}
              {upload?.status === "verified" && <div className="alert alert-info">This delivery has been verified by the admin.</div>}

              <div className="receipt-actions">
                <button type="button" className="btn btn-outline" onClick={printReceipt}>Print receipt</button>
              </div>
              <ReceiptDocument receipt={receipt} qrUrl={qrUrl} />

              {!locked && (
                <form onSubmit={submit} className="receipt-upload">
                  <h4>Customer confirmation</h4>
                  <div className="field">
                    <label htmlFor="rc-name">Customer's printed name</label>
                    <input id="rc-name" required maxLength={120} value={printedName} onChange={(e) => setPrintedName(e.target.value)} />
                  </div>
                  <div className="field">
                    <label>Customer's signature</label>
                    <SignaturePad onChange={setSignature} />
                  </div>
                  <label className="check-row">
                    <input type="checkbox" checked={acknowledged} onChange={(e) => setAcknowledged(e.target.checked)} />
                    The customer confirmed the items were received in good condition.
                  </label>
                  <div className="field">
                    <label htmlFor="rc-file">Signed receipt (photo or PDF)</label>
                    <input id="rc-file" type="file" accept="image/jpeg,image/png,image/webp,application/pdf" capture="environment" onChange={pickFile} />
                    {fileError && <p className="field-error">{fileError}</p>}
                  </div>
                  <div className="form-actions">
                    <button type="button" className="btn btn-outline" onClick={onClose}>Cancel</button>
                    <button type="submit" className="btn btn-primary" disabled={!canSubmit}>
                      {busy ? "Uploading..." : "Upload receipt"}
                    </button>
                  </div>
                </form>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
