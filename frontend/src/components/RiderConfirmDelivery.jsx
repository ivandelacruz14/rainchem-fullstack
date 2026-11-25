import { useEffect, useMemo, useState } from "react";
import client from "../api/client";
import { useToast } from "../context/ToastContext";
import ReceiptDocument from "./ReceiptDocument";
import ErrorBox from "./ErrorBox";
import ScanConfirm from "./ScanConfirm";

const ACCEPTED = ["image/jpeg", "image/png", "image/webp", "application/pdf"];
const MAX_BYTES = 5 * 1024 * 1024;

/**
 * Rider's delivery confirmation, in order:
 *   1. Check the customer and order number, then scan the receipt's QR code or barcode.
 *   2. Take a photo of the printed receipt, signed by the customer and the rider, and upload it.
 */
export default function RiderConfirmDelivery({ order, onClose, onChanged }) {
  const showToast = useToast();
  const [receipt, setReceipt] = useState(null);
  const [loadError, setLoadError] = useState("");
  const [step, setStep] = useState(1);
  const [code, setCode] = useState("");
  const [scanError, setScanError] = useState("");
  const [scanning, setScanning] = useState(false);
  const [confirmedCode, setConfirmedCode] = useState("");
  const [printedName, setPrintedName] = useState("");
  const [acknowledged, setAcknowledged] = useState(false);
  const [file, setFile] = useState(null);
  const [fileError, setFileError] = useState("");
  const [busy, setBusy] = useState(false);
  const [showReceipt, setShowReceipt] = useState(false);

  useEffect(() => {
    let active = true;
    Promise.resolve()
      .then(() => client.get(`/api/rider/orders/${order.id}/receipt`))
      .then((res) => {
        if (!active) return;
        setReceipt(res.data.receipt);
        setPrintedName((p) => p || res.data.receipt.customer.name);
      })
      .catch((err) => { if (active) setLoadError(err.response?.data?.error || "The receipt could not be loaded. Check your connection and try again."); });
    return () => { active = false; };
  }, [order.id]);

  const upload = receipt?.upload;
  const locked = upload && (upload.status === "pending_verification" || upload.status === "verified");
  const previewUrl = useMemo(() => (file && file.type !== "application/pdf" ? URL.createObjectURL(file) : null), [file]);
  useEffect(() => () => { if (previewUrl) URL.revokeObjectURL(previewUrl); }, [previewUrl]);

  async function confirmCode(value) {
    const trimmed = String(value || "").trim();
    if (!trimmed) return;
    setScanError("");
    try {
      await client.post(`/api/rider/orders/${order.id}/confirm-scan`, { code: trimmed });
      setConfirmedCode(trimmed);
      setScanning(false);
      setStep(2);
    } catch (err) {
      setScanError(err.response?.data?.error || "This code does not belong to this order.");
    }
  }

  function pickFile(e) {
    const f = e.target.files?.[0] || null;
    setFileError("");
    if (f && !ACCEPTED.includes(f.type)) { setFileError("Only JPG, PNG, WEBP, or PDF files are accepted."); setFile(null); return; }
    if (f && f.size > MAX_BYTES) { setFileError("The file is larger than 5 MB. Take the photo again at a lower resolution."); setFile(null); return; }
    setFile(f);
  }

  const canSubmit = !busy && !locked && file && printedName.trim().length >= 2 && acknowledged && confirmedCode;

  async function submit(e) {
    e.preventDefault();
    if (!canSubmit) return;
    setBusy(true);
    const form = new FormData();
    form.append("file", file);
    form.append("printedName", printedName.trim());
    form.append("acknowledged", "yes");
    form.append("scanCode", confirmedCode);
    try {
      await client.post(`/api/rider/orders/${order.id}/receipt-upload`, form);
      showToast("Photo uploaded. The admin will verify it.", "success");
      onChanged?.();
      onClose();
    } catch (err) {
      showToast(err.response?.data?.error || "The photo could not be uploaded.", "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="overlay" onClick={onClose}>
      <div className="modal wide confirm-delivery" role="dialog" aria-modal="true" aria-label="Confirm delivery" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <div>
            <h3 style={{ margin: 0 }}>Confirm delivery</h3>
            <p className="field-hint" style={{ margin: "4px 0 0" }}>{order.orderNumber} · {order.customer.name}</p>
          </div>
          <button type="button" className="modal-close" onClick={onClose} aria-label="Close">&times;</button>
        </div>

        <ol className="steps" aria-label="Confirmation steps">
          <li className={step === 1 ? "current" : "done"}><span>1</span> Scan the receipt</li>
          <li className={step === 2 ? "current" : ""}><span>2</span> Photo of the signed receipt</li>
        </ol>

        <div className="modal-body">
          {loadError && <ErrorBox><span>{loadError}</span></ErrorBox>}
          {!receipt && !loadError && <div className="loading-state" role="status"><span className="spinner" /> Loading the order...</div>}

          {receipt && upload?.status === "verified" && <div className="alert alert-info">This delivery has already been verified.</div>}
          {receipt && upload?.status === "pending_verification" && <div className="alert alert-info">The photo is waiting for the admin to verify it.</div>}
          {receipt && upload?.status === "rejected" && (
            <div className="alert alert-error" role="alert">The last photo was rejected: {upload.rejectReason}. Upload a corrected photo.</div>
          )}

          {receipt && step === 1 && (
            <section className="confirm-section">
              <div className="confirm-summary">
                <div><span>Customer</span><strong>{receipt.customer.name}</strong></div>
                <div><span>Order number</span><strong>{receipt.orderNumber}</strong></div>
                <div><span>Address</span><strong>{receipt.customer.address}</strong></div>
              </div>

              <p className="confirm-help">
                Scan the QR code or barcode on the printed receipt to confirm this is the right order.
                A barcode scanner works here too. You can also type the order number.
              </p>

              {scanning ? (
                <ScanConfirm onDetected={confirmCode} onClose={() => setScanning(false)} />
              ) : (
                <div className="scan-actions">
                  <button type="button" className="btn btn-outline" onClick={() => setScanning(true)}>Scan with camera</button>
                </div>
              )}

              <form onSubmit={(e) => { e.preventDefault(); confirmCode(code); }} className="scan-form">
                <div className="field">
                  <label htmlFor="scan-code">Scanned code or order number</label>
                  <input id="scan-code" autoFocus autoComplete="off" value={code} placeholder="Scan here or type the order number"
                    onChange={(e) => setCode(e.target.value)} />
                </div>
                <button type="submit" className="btn btn-primary" disabled={!code.trim()}>Confirm this order</button>
              </form>
              {scanError && <p className="field-error" role="alert">{scanError}</p>}

              <button type="button" className="link-btn" onClick={() => setShowReceipt((v) => !v)}>
                {showReceipt ? "Hide receipt" : "Show receipt"}
              </button>
              {showReceipt && (
                <ErrorBox><ReceiptDocument receipt={receipt} /></ErrorBox>
              )}
            </section>
          )}

          {receipt && step === 2 && (
            <form onSubmit={submit} className="confirm-section">
              <div className="alert alert-info">Order <strong>{receipt.orderNumber}</strong> confirmed by scan.</div>
              <ol className="photo-rules">
                <li>Print the receipt, then have the customer and the rider sign it on paper.</li>
                <li>Take one clear photo of the whole signed receipt. Both signatures must be visible.</li>
                <li>Upload the photo below.</li>
              </ol>

              <div className="field">
                <label htmlFor="cf-name">Customer's printed name</label>
                <input id="cf-name" required maxLength={120} value={printedName} onChange={(e) => setPrintedName(e.target.value)} />
              </div>

              <div className="field">
                <label htmlFor="cf-file">Photo of the signed receipt</label>
                <input id="cf-file" type="file" accept="image/jpeg,image/png,image/webp,application/pdf" capture="environment" onChange={pickFile} />
                {fileError && <p className="field-error" role="alert">{fileError}</p>}
                {previewUrl && <img src={previewUrl} alt="Preview of the signed receipt" className="photo-preview" />}
                {file && file.type === "application/pdf" && <p className="field-hint">PDF selected: {file.name}</p>}
              </div>

              <label className="check-row">
                <input type="checkbox" checked={acknowledged} onChange={(e) => setAcknowledged(e.target.checked)} />
                The customer confirmed the items were received in good condition.
              </label>

              <div className="form-actions">
                <button type="button" className="btn btn-outline" onClick={() => setStep(1)}>Back</button>
                <button type="submit" className="btn btn-primary" disabled={!canSubmit}>{busy ? "Uploading..." : "Upload photo"}</button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
