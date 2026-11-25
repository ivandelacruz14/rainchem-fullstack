import { useEffect, useState } from "react";
import client from "../../api/client";
import { useToast } from "../../context/ToastContext";
import { useAdminAuth } from "../../context/AdminAuthContext";
import ReceiptDocument from "../../components/ReceiptDocument";
import ErrorBox from "../../components/ErrorBox";
import { peso, formatDate } from "../../utils/format";

const TABS = [
  { key: "pending_confirmation", label: "Awaiting photo", help: "Orders out for delivery that do not have a photo of the signed receipt yet." },
  { key: "pending_verification", label: "To verify", help: "Photos uploaded by riders. Check them, then verify or reject." },
  { key: "verified", label: "Verified", help: "Deliveries whose signed receipt has been verified." },
  { key: "rejected", label: "Rejected", help: "Photos that were rejected. The rider must upload a corrected one." },
];

const STAGE = {
  awaiting_receipt: "Awaiting photo", pending_verification: "To verify", verified: "Verified",
  delivered: "Delivered", not_out_for_delivery: "Not out for delivery",
};

function receiptStatus(i) {
  if (!i.upload) return { label: "No photo yet", tone: "none" };
  if (i.upload.status === "pending_verification") return { label: "To verify", tone: "pending" };
  if (i.upload.status === "verified") return { label: "Verified", tone: "verified" };
  return { label: "Rejected", tone: "rejected" };
}

/** Delivery Confirmation: riders' signed-receipt photos, reviewed here before a delivery is recorded. */
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
  const [printing, setPrinting] = useState(null);
  const [check, setCheck] = useState({ code: "", result: null, error: "" });
  const activeTab = TABS.find((t) => t.key === tab);

  useEffect(() => {
    let active = true;
    setError("");
    Promise.resolve()
      .then(() => client.get("/api/admin/delivery-confirmations", { params: { status: tab, q: search.trim() || undefined } }))
      .then((res) => { if (active) setItems(res.data.items); })
      .catch((err) => { if (active) { setItems([]); setError(err.response?.data?.error || "The list could not be loaded. Check your connection and refresh."); } });
    return () => { active = false; };
  }, [tab, search, refresh]);

  async function checkCode(e) {
    e.preventDefault();
    setCheck((c) => ({ ...c, result: null, error: "" }));
    try {
      const res = await client.post("/api/receipts/verify", { code: check.code.trim() });
      setCheck((c) => ({ ...c, result: res.data }));
    } catch (err) {
      setCheck((c) => ({ ...c, error: err.response?.data?.error || "This code does not match any order." }));
    }
  }

  async function printFor(item) {
    setPrinting(item);
  }

  useEffect(() => {
    if (!printing) return undefined;
    const t = setTimeout(() => { window.print(); setPrinting(null); }, 300);
    return () => clearTimeout(t);
  }, [printing]);

  return (
    <div className="dc-page">
      <header className="dc-header">
        <div>
          <p className="dc-kicker">Sales and orders</p>
          <h2 className="dc-title">Delivery Confirmation</h2>
          <p className="dc-sub">Riders photograph the signed receipt. Check each photo here, then verify it or reject it with a reason.</p>
        </div>
      </header>

      <section className="dc-panel dc-check">
        <div className="dc-panel-head">
          <h3>Check a receipt code</h3>
          <p>Scan the QR code or barcode on a printed receipt, or type the order number.</p>
        </div>
        <form onSubmit={checkCode} className="dc-check-form">
          <input aria-label="Receipt code" value={check.code} placeholder="Scan here or type the order number"
            onChange={(e) => setCheck((c) => ({ ...c, code: e.target.value }))} />
          <button type="submit" className="btn btn-primary" disabled={!check.code.trim()}>Check code</button>
        </form>
        {check.error && <p className="field-error" role="alert">{check.error}</p>}
        {check.result && (
          <p className="dc-result" role="status">
            <strong>{check.result.orderNumber}</strong> is <strong>{STAGE[check.result.deliveryStage] || check.result.deliveryStage}</strong>
            {check.result.receiptStatus !== "none" && <> · photo {check.result.receiptStatus.replace("_", " ")}</>}
          </p>
        )}
      </section>

      <section className="dc-panel">
        <nav className="dc-tabs" role="tablist" aria-label="Delivery confirmation tabs">
          {TABS.map((t) => (
            <button key={t.key} type="button" role="tab" aria-selected={tab === t.key}
              className={`dc-tab ${tab === t.key ? "active" : ""}`} onClick={() => { setTab(t.key); setItems(null); }}>
              {t.label}
            </button>
          ))}
        </nav>
        <div className="dc-tab-help">{activeTab.help}</div>

        <div className="dc-toolbar">
          <input type="search" aria-label="Search deliveries" placeholder="Search by order number or customer"
            value={search} onChange={(e) => setSearch(e.target.value)} />
          <button type="button" className="btn btn-outline btn-sm" onClick={() => setRefresh((n) => n + 1)}>Refresh</button>
        </div>

        {error && <div className="alert alert-error" role="alert">{error}</div>}
        {items === null && <div className="loading-state" role="status"><span className="spinner" /> Loading...</div>}
        {items && items.length === 0 && !error && (
          <div className="empty-state"><strong>Nothing in this tab</strong><span>{search ? "No order matches your search." : "No deliveries are waiting here right now."}</span></div>
        )}

        {items && items.length > 0 && (
          <div className="dc-table-wrap">
            <table className="dc-table">
              <thead>
                <tr>
                  <th>Order</th><th>Customer</th><th>Rider</th><th>Payment</th>
                  <th className="num">Cash to collect</th><th>Delivered</th><th>Photo</th><th className="act">Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map((i) => {
                  const st = receiptStatus(i);
                  return (
                    <tr key={i.orderId}>
                      <td className="strong">{i.orderNumber}</td>
                      <td>{i.customerName}</td>
                      <td>{i.rider || "-"}</td>
                      <td>{i.paymentMethod}</td>
                      <td className="num">{i.codAmount > 0 ? peso(i.codAmount) : "-"}</td>
                      <td>{i.deliveryDate ? formatDate(i.deliveryDate) : "-"}</td>
                      <td><span className={`dc-pill ${st.tone}`}>{st.label}</span></td>
                      <td className="act">
                        <button type="button" className="btn btn-outline btn-sm" onClick={() => printFor(i)}>Print</button>
                        {i.upload && <button type="button" className="btn btn-primary btn-sm" onClick={() => setOpen(i)}>Review</button>}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {printing && <PrintSheet orderId={printing.orderId} />}

      {open && (
        <ReviewDialog item={open} canReview={canReview} onClose={() => setOpen(null)}
          onDone={(msg) => { showToast(msg, "success"); setOpen(null); setRefresh((n) => n + 1); }} />
      )}
    </div>
  );
}

/** Loads the order's receipt and prints it. The print layout shows only the receipt. */
function PrintSheet({ orderId }) {
  const [receipt, setReceipt] = useState(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    client.get(`/api/admin/orders/${orderId}/receipt`)
      .then((r) => setReceipt(r.data.receipt))
      .catch(() => setFailed(true));
  }, [orderId]);
  if (failed) return <div className="alert alert-error" role="alert">The receipt could not be prepared for printing.</div>;
  if (!receipt) return null;
  return <div className="dc-print-only"><ReceiptDocument receipt={receipt} /></div>;
}

function ReviewDialog({ item, canReview, onClose, onDone }) {
  const [receipt, setReceipt] = useState(null);
  const [receiptError, setReceiptError] = useState("");
  const [fileUrl, setFileUrl] = useState(null);
  const [fileError, setFileError] = useState("");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState("");
  const upload = item.upload;

  useEffect(() => {
    const urls = [];
    let active = true;
    client.get(`/api/admin/orders/${item.orderId}/receipt`)
      .then((r) => { if (active) setReceipt(r.data.receipt); })
      .catch((err) => { if (active) setReceiptError(err.response?.data?.error || "The order details could not be loaded."); });
    if (upload) {
      client.get(`/api/admin/delivery-confirmations/${upload.id}/file`, { responseType: "blob" })
        .then((r) => { const u = URL.createObjectURL(r.data); urls.push(u); if (active) setFileUrl(u); })
        .catch(() => { if (active) setFileError("The photo could not be opened. Try again, or check that the file still exists."); });
    }
    return () => { active = false; urls.forEach((u) => URL.revokeObjectURL(u)); };
  }, [item.orderId, upload?.id]);

  async function verify() {
    setBusy(true); setActionError("");
    try {
      await client.post(`/api/admin/delivery-confirmations/${upload.id}/verify`);
      onDone("Photo verified. The rider can now record the delivery.");
    } catch (err) {
      setActionError(err.response?.data?.error || "The photo could not be verified.");
    } finally { setBusy(false); }
  }

  async function reject() {
    if (reason.trim().length < 5) { setActionError("Write a clear reason (at least 5 characters) for rejecting the photo."); return; }
    setBusy(true); setActionError("");
    try {
      await client.post(`/api/admin/delivery-confirmations/${upload.id}/reject`, { reason: reason.trim() });
      onDone("Photo rejected. The rider has been asked to upload a corrected one.");
    } catch (err) {
      setActionError(err.response?.data?.error || "The photo could not be rejected.");
    } finally { setBusy(false); }
  }

  const isPdf = upload?.mime === "application/pdf";
  const canAct = canReview && upload?.status === "pending_verification";

  return (
    <div className="overlay" onClick={onClose}>
      <div className="modal wide dc-review" role="dialog" aria-modal="true" aria-label={`Review ${item.orderNumber}`} onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <div>
            <h3 style={{ margin: 0 }}>Review {item.orderNumber}</h3>
            <p className="field-hint" style={{ margin: "4px 0 0" }}>{item.customerName} · rider: {item.rider || "-"}</p>
          </div>
          <button type="button" className="modal-close" onClick={onClose} aria-label="Close">&times;</button>
        </div>

        <div className="modal-body dc-review-body">
          <section className="dc-review-col">
            <h4>1. Photo from the rider</h4>
            {!upload && <div className="empty-state"><span>No photo uploaded yet.</span></div>}
            {upload && !fileUrl && !fileError && <div className="loading-state" role="status"><span className="spinner" /> Loading the photo...</div>}
            {fileError && <div className="alert alert-error" role="alert">{fileError}</div>}
            {upload && fileUrl && !isPdf && <img src={fileUrl} alt="Photo of the signed receipt" className="dc-photo" />}
            {upload && fileUrl && isPdf && (
              <object data={fileUrl} type="application/pdf" className="dc-pdf">
                <a href={fileUrl} target="_blank" rel="noreferrer">Open the PDF</a>
              </object>
            )}
            {upload && (
              <dl className="dc-facts">
                <dt>Printed name</dt><dd>{upload.printedName}</dd>
                <dt>Acknowledged</dt><dd>{formatDate(upload.acknowledgedAt)}</dd>
                <dt>Status</dt><dd>{receiptStatus(item).label}</dd>
                {upload.rejectReason && <><dt>Rejected for</dt><dd>{upload.rejectReason}</dd></>}
              </dl>
            )}
          </section>

          <section className="dc-review-col">
            <h4>2. Order receipt</h4>
            {receiptError && <ErrorBox><span>{receiptError}</span></ErrorBox>}
            {!receipt && !receiptError && <div className="loading-state" role="status"><span className="spinner" /> Loading the order...</div>}
            {receipt && <ErrorBox><ReceiptDocument receipt={receipt} /></ErrorBox>}
          </section>
        </div>

        {(actionError || canAct) && (
          <footer className="dc-review-foot">
            {actionError && <div className="alert alert-error" role="alert">{actionError}</div>}
            {canAct && (
              <div className="dc-decide">
                <div className="field">
                  <label htmlFor="reject-reason">If the photo is wrong, write the reason here</label>
                  <textarea id="reject-reason" rows={2} maxLength={500} value={reason} onChange={(e) => setReason(e.target.value)} />
                </div>
                <div className="form-actions">
                  <button type="button" className="btn btn-outline" onClick={reject} disabled={busy}>Reject photo</button>
                  <button type="button" className="btn btn-primary" onClick={verify} disabled={busy}>Verify photo</button>
                </div>
              </div>
            )}
          </footer>
        )}
      </div>
    </div>
  );
}
