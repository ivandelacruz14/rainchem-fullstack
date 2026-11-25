import { useEffect, useState } from "react";
import client from "../../api/client";
import { useToast } from "../../context/ToastContext";
import { useAdminAuth } from "../../context/AdminAuthContext";
import ReceiptDocument from "../../components/ReceiptDocument";
import { peso, formatDate } from "../../utils/format";

const TABS = [
  { key: "pending_confirmation", label: "Pending Confirmation" },
  { key: "pending_verification", label: "Pending Verification" },
  { key: "verified", label: "Verified Deliveries" },
  { key: "rejected", label: "Rejected Receipts" },
];

const STAGE_LABEL = {
  awaiting_receipt: "Awaiting receipt", pending_verification: "Pending verification",
  verified: "Verified", delivered: "Delivered", not_out_for_delivery: "Not out for delivery",
};

/** Delivery Confirmation Management: receipts uploaded by riders, reviewed here before a delivery is recorded. */
export default function DeliveryConfirmations() {
  const showToast = useToast();
  const { can } = useAdminAuth();
  const canReview = can("manage_orders");
  const [tab, setTab] = useState("pending_verification");
  const [search, setSearch] = useState("");
  const [items, setItems] = useState(null);
  const [error, setError] = useState("");
  const [refresh, setRefresh] = useState(0);
  const [open, setOpen] = useState(null);
  const [check, setCheck] = useState({ code: "", result: null, error: "" });

  useEffect(() => {
    let active = true;
    setError("");
    Promise.resolve()
      .then(() => client.get("/api/admin/delivery-confirmations", { params: { status: tab, q: search || undefined } }))
      .then((res) => { if (active) setItems(res.data.items); })
      .catch((err) => { if (active) { setItems([]); setError(err.response?.data?.error || "Could not load the deliveries."); } });
    return () => { active = false; };
  }, [tab, search, refresh]);

  async function checkQr(e) {
    e.preventDefault();
    setCheck((c) => ({ ...c, result: null, error: "" }));
    try {
      const res = await client.post("/api/receipts/verify", { code: check.code.trim() });
      setCheck((c) => ({ ...c, result: res.data }));
    } catch (err) {
      setCheck((c) => ({ ...c, error: err.response?.data?.error || "This code does not match any order." }));
    }
  }

  return (
    <div className="delivery-confirm">
      <div className="page-head">
        <div>
          <h2 className="page-title">Delivery Confirmation</h2>
          <p className="page-sub">Riders upload the signed receipt. Verify it here before a delivery is recorded.</p>
        </div>
      </div>

      <section className="card qr-check">
        <form onSubmit={checkQr} className="qr-check-form">
          <div className="field">
            <label htmlFor="qr-code">Scan or enter a receipt code</label>
            <input id="qr-code" value={check.code} placeholder="Scan the QR code or type the order code"
              onChange={(e) => setCheck((c) => ({ ...c, code: e.target.value }))} />
          </div>
          <button type="submit" className="btn btn-outline" disabled={!check.code.trim()}>Check</button>
        </form>
        {check.error && <p className="field-error" role="alert">{check.error}</p>}
        {check.result && (
          <p className="qr-result" role="status">
            Order <strong>{check.result.orderNumber}</strong>: {STAGE_LABEL[check.result.deliveryStage] || check.result.deliveryStage}
            {check.result.receiptStatus !== "none" && ` · receipt ${check.result.receiptStatus.replace("_", " ")}`}
          </p>
        )}
      </section>

      <div className="tab-bar" role="tablist" aria-label="Delivery confirmation tabs">
        {TABS.map((t) => (
          <button key={t.key} type="button" role="tab" aria-selected={tab === t.key}
            className={`tab-btn ${tab === t.key ? "active" : ""}`} onClick={() => { setTab(t.key); setItems(null); }}>
            {t.label}
          </button>
        ))}
      </div>

      <div className="toolbar">
        <input type="search" aria-label="Search deliveries" placeholder="Search order number or customer"
          value={search} onChange={(e) => setSearch(e.target.value)} />
        <button type="button" className="btn btn-outline btn-sm" onClick={() => setRefresh((n) => n + 1)}>Refresh</button>
      </div>

      {error && <div className="alert alert-error" role="alert">{error}</div>}
      {items === null && <div className="loading-state" role="status"><span className="spinner" /> Loading deliveries...</div>}
      {items && items.length === 0 && !error && (
        <div className="empty-state"><strong>Nothing here yet</strong><span>No deliveries are waiting in this tab.</span></div>
      )}

      {items && items.length > 0 && (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Order</th><th>Customer</th><th>Rider</th><th>Payment</th><th className="num">COD to collect</th>
                <th>Delivery date</th><th>Receipt</th><th />
              </tr>
            </thead>
            <tbody>
              {items.map((i) => (
                <tr key={i.orderId}>
                  <td><strong>{i.orderNumber}</strong></td>
                  <td>{i.customerName}</td>
                  <td>{i.rider || "-"}</td>
                  <td>{i.paymentMethod}</td>
                  <td className="num">{i.codAmount > 0 ? peso(i.codAmount) : "-"}</td>
                  <td>{i.deliveryDate ? formatDate(i.deliveryDate) : "-"}</td>
                  <td>
                    <span className={`status-pill ${i.upload ? i.upload.status : "none"}`}>
                      {i.upload ? (i.upload.status === "pending_verification" ? "Pending verification" : i.upload.status === "verified" ? "Verified" : "Rejected") : "Not uploaded"}
                    </span>
                  </td>
                  <td className="actions">
                    <button type="button" className="btn btn-outline btn-sm" onClick={() => setOpen(i)}>Review</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {open && (
        <ReviewDialog item={open} canReview={canReview} onClose={() => setOpen(null)}
          onDone={(msg) => { showToast(msg, "success"); setOpen(null); setRefresh((n) => n + 1); }} />
      )}
    </div>
  );
}

function ReviewDialog({ item, canReview, onClose, onDone }) {
  const showToast = useToast();
  const [receipt, setReceipt] = useState(null);
  const [fileUrl, setFileUrl] = useState(null);
  const [sigUrl, setSigUrl] = useState(null);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const upload = item.upload;

  useEffect(() => {
    const urls = [];
    let active = true;
    const keep = (blob) => { const u = URL.createObjectURL(blob); urls.push(u); return u; };
    client.get(`/api/admin/orders/${item.orderId}/receipt`).then((r) => { if (active) setReceipt(r.data.receipt); }).catch(() => {});
    if (upload) {
      client.get(`/api/admin/delivery-confirmations/${upload.id}/file`, { responseType: "blob" })
        .then((r) => { if (active) setFileUrl(keep(r.data)); }).catch(() => {});
      client.get(`/api/admin/delivery-confirmations/${upload.id}/signature.png`, { responseType: "blob" })
        .then((r) => { if (active) setSigUrl(keep(r.data)); }).catch(() => {});
    }
    return () => { active = false; urls.forEach((u) => URL.revokeObjectURL(u)); };
  }, [item.orderId, upload?.id]);

  async function verify() {
    setBusy(true); setError("");
    try {
      await client.post(`/api/admin/delivery-confirmations/${upload.id}/verify`);
      onDone("Receipt verified. The rider can now record the delivery.");
    } catch (err) {
      setError(err.response?.data?.error || "Could not verify the receipt.");
    } finally { setBusy(false); }
  }

  async function reject() {
    if (reason.trim().length < 5) { setError("Give a clear reason for rejecting the receipt."); return; }
    setBusy(true); setError("");
    try {
      await client.post(`/api/admin/delivery-confirmations/${upload.id}/reject`, { reason: reason.trim() });
      showToast("Receipt rejected. The rider has been asked to upload a corrected one.", "success");
      onDone("Receipt rejected.");
    } catch (err) {
      setError(err.response?.data?.error || "Could not reject the receipt.");
    } finally { setBusy(false); }
  }

  const isPdf = upload?.mime === "application/pdf";
  return (
    <div className="overlay" onClick={onClose}>
      <div className="modal wide" role="dialog" aria-modal="true" aria-label={`Review ${item.orderNumber}`} onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h3 style={{ margin: 0 }}>Review {item.orderNumber}</h3>
          <button type="button" className="modal-close" onClick={onClose} aria-label="Close">&times;</button>
        </div>
        <div className="modal-body review-body">
          <div className="review-grid">
            <section className="review-col">
              <h4>Uploaded receipt</h4>
              {!upload && <div className="empty-state"><span>The rider has not uploaded the receipt yet.</span></div>}
              {upload && !fileUrl && <div className="loading-state" role="status"><span className="spinner" /> Loading the file...</div>}
              {upload && fileUrl && (isPdf
                ? <iframe title="Uploaded receipt" src={fileUrl} className="receipt-frame" sandbox="" />
                : <img src={fileUrl} alt="Uploaded signed receipt" className="receipt-image" />)}
              {upload && (
                <dl className="review-dl">
                  <dt>Printed name</dt><dd>{upload.printedName}</dd>
                  <dt>Acknowledged</dt><dd>{formatDate(upload.acknowledgedAt)}</dd>
                  <dt>Status</dt><dd>{upload.status.replace("_", " ")}</dd>
                  {upload.rejectReason && <><dt>Reject reason</dt><dd>{upload.rejectReason}</dd></>}
                </dl>
              )}
              {sigUrl && <div className="signature-view"><span>Customer signature</span><img src={sigUrl} alt="Customer signature" /></div>}
            </section>

            <section className="review-col">
              <h4>Order receipt</h4>
              {!receipt && <div className="loading-state" role="status"><span className="spinner" /> Loading the order...</div>}
              {receipt && <ReceiptDocument receipt={receipt} />}
            </section>
          </div>

          {error && <div className="alert alert-error" role="alert">{error}</div>}

          {upload?.status === "pending_verification" && canReview && (
            <div className="review-actions">
              <div className="field">
                <label htmlFor="reject-reason">Reason for rejecting (required if rejecting)</label>
                <textarea id="reject-reason" rows={2} maxLength={500} value={reason} onChange={(e) => setReason(e.target.value)} />
              </div>
              <div className="form-actions">
                <button type="button" className="btn btn-outline" onClick={reject} disabled={busy}>Reject receipt</button>
                <button type="button" className="btn btn-primary" onClick={verify} disabled={busy}>Verify receipt</button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
