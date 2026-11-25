import { useEffect, useRef, useState } from "react";
import client from "../../api/client";
import { useToast } from "../../context/ToastContext";
import { peso } from "../../utils/format";
import ScanConfirm from "../../components/ScanConfirm";

const CARD_KEYS = [
  { key: "total", label: "Assigned to me" },
  { key: "pending", label: "Pending" },
  { key: "outForDelivery", label: "Out for delivery" },
  { key: "delivered", label: "Delivered" },
  { key: "failed", label: "Failed" },
];

const ACCEPTED = ["image/jpeg", "image/png", "image/webp"];
const MAX_BYTES = 5 * 1024 * 1024;

/** Rider dashboard: find an order, check its details, scan the units, take the delivery photo, then mark it
 *  Delivered or Failed. The server checks every step, so the buttons only help; they do not decide. */
export default function RiderDeliveries() {
  const showToast = useToast();
  const [summary, setSummary] = useState(null);
  const [orders, setOrders] = useState(null);
  const [loadError, setLoadError] = useState("");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [busy, setBusy] = useState(false);
  const [scanCode, setScanCode] = useState("");
  const [scanning, setScanning] = useState(false);
  const [photo, setPhoto] = useState(null);
  const [photoError, setPhotoError] = useState("");
  const [failing, setFailing] = useState(false);
  const [failReason, setFailReason] = useState("");
  const detailRef = useRef(null);

  function loadList() {
    Promise.resolve()
      .then(() => Promise.all([client.get("/api/rider/summary"), client.get("/api/rider")]))
      .then(([s, o]) => { setSummary(s.data.summary); setOrders(o.data.orders); setLoadError(""); })
      .catch((err) => { setOrders([]); setLoadError(err.response?.data?.error || "Your deliveries could not be loaded. Check your connection and refresh."); });
  }
  useEffect(() => { loadList(); }, []);

  useEffect(() => {
    const q = query.trim();
    if (q.length < 2) { setResults(null); return undefined; }
    const t = setTimeout(() => {
      client.get("/api/rider/search", { params: { q } })
        .then((r) => setResults(r.data.orders))
        .catch(() => setResults([]));
    }, 250);
    return () => clearTimeout(t);
  }, [query]);

  function loadDetail(id) {
    setSelectedId(id);
    setDetail(null);
    setScanning(false);
    setFailing(false);
    setPhoto(null);
    client.get(`/api/rider/${id}`)
      .then((r) => { setDetail(r.data.order); setTimeout(() => detailRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 50); })
      .catch((err) => showToast(err.response?.data?.error || "This order could not be opened.", "error"));
  }

  async function run(path, body, message) {
    setBusy(true);
    try {
      const r = await client.post(`/api/rider/${selectedId}/${path}`, body || {});
      if (r.data?.order) setDetail(r.data.order);
      if (message) showToast(message, "success");
      loadList();
      return r.data;
    } catch (err) {
      showToast(err.response?.data?.error || "Something went wrong. Try again.", "error");
      return null;
    } finally {
      setBusy(false);
    }
  }

  async function scanUnit(code) {
    const value = String(code || "").trim();
    if (!value) return;
    setBusy(true);
    try {
      const r = await client.post(`/api/rider/${selectedId}/scan`, { code: value });
      setDetail(r.data.order);
      setScanCode("");
      showToast(r.data.message, r.data.accepted ? "success" : "error");
    } catch (err) {
      const data = err.response?.data;
      if (data?.order) setDetail(data.order);
      showToast(data?.message || data?.error || "This code could not be scanned.", "error");
    } finally {
      setBusy(false);
    }
  }

  function pickPhoto(e) {
    const f = e.target.files?.[0] || null;
    setPhotoError("");
    if (f && !ACCEPTED.includes(f.type)) { setPhotoError("Use a JPG, PNG, or WEBP photo."); setPhoto(null); return; }
    if (f && f.size > MAX_BYTES) { setPhotoError("The photo is larger than 5 MB. Take it again, or use a lower resolution."); setPhoto(null); return; }
    setPhoto(f);
  }

  async function uploadPhoto() {
    if (!photo) return;
    const form = new FormData();
    form.append("image", photo);
    setBusy(true);
    try {
      const r = await client.post(`/api/rider/${selectedId}/proof`, form);
      setDetail(r.data.order);
      setPhoto(null);
      showToast("Photo saved. You can now mark the order as Delivered.", "success");
      loadList();
    } catch (err) {
      showToast(err.response?.data?.error || "The photo could not be uploaded.", "error");
    } finally {
      setBusy(false);
    }
  }

  const status = detail?.status;
  const allScanned = detail && (!detail.missing || detail.missing.length === 0);
  const canDeliver = status === "shipped" && allScanned && detail?.hasProof && !busy;

  return (
    <div className="rd-page">
      <header className="rd-top">
        <div>
          <h1 className="rd-title">My Deliveries</h1>
          <p className="rd-sub">Find an order, confirm the items, take the delivery photo, then mark it Delivered or Failed.</p>
        </div>
      </header>

      <section className="rd-search" aria-label="Find an order">
        <label htmlFor="rd-q" className="rd-search-label">Find an order</label>
        <input id="rd-q" type="search" autoComplete="off" value={query} placeholder="Customer name, order number, or phone number"
          onChange={(e) => setQuery(e.target.value)} />
        {query.trim().length === 1 && <p className="field-hint">Type at least 2 characters.</p>}
        {results && results.length === 0 && <p className="rd-empty-note" role="status">No assigned order matches "{query.trim()}".</p>}
        {results && results.length > 0 && (
          <ul className="rd-results">
            {results.map((o) => (
              <li key={o.id}>
                <button type="button" onClick={() => loadDetail(o.id)}>
                  <strong>{o.customerName}</strong>
                  <span>{o.orderNumber} · {o.customerPhone}</span>
                  <em className={`rd-badge s-${o.status}`}>{o.statusLabel}</em>
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      {summary && (
        <section className="rd-cards" aria-label="Summary">
          {CARD_KEYS.map((c) => (
            <div key={c.key} className={`rd-card rd-card-${c.key}`}>
              <span>{c.label}</span>
              <strong>{summary[c.key]}</strong>
            </div>
          ))}
        </section>
      )}

      <section className="rd-list-wrap" aria-label="Assigned orders">
        <h2 className="rd-h2">Assigned orders</h2>
        {loadError && <div className="alert alert-error" role="alert">{loadError}</div>}
        {orders === null && <div className="loading-state" role="status"><span className="spinner" /> Loading...</div>}
        {orders && orders.length === 0 && !loadError && (
          <div className="empty-state"><strong>No deliveries assigned</strong><span>New assignments from the office appear here.</span></div>
        )}
        {orders && orders.length > 0 && (
          <ul className="rd-list">
            {orders.map((o) => (
              <li key={o.id} className={selectedId === o.id ? "selected" : ""}>
                <button type="button" className="rd-row" onClick={() => loadDetail(o.id)}>
                  <span className="rd-row-main">
                    <strong>{o.customer.name}</strong>
                    <span>{o.orderNumber} · {o.customer.phone}</span>
                    <span className="rd-row-addr">{o.address}</span>
                  </span>
                  <em className={`rd-badge s-${o.status}`}>{o.statusLabel}</em>
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      {selectedId && (
        <section className="rd-detail" ref={detailRef} aria-label="Delivery details">
          {!detail && <div className="loading-state" role="status"><span className="spinner" /> Opening the order...</div>}
          {detail && (
            <>
              <div className="rd-detail-head">
                <div>
                  <h2>{detail.customer.name}</h2>
                  <p>Order <strong>{detail.orderNumber}</strong></p>
                </div>
                <em className={`rd-badge s-${detail.status}`}>{detail.statusLabel}</em>
              </div>

              <div className="rd-grid">
                <div className="rd-box">
                  <h3>Customer</h3>
                  <p className="rd-strong">{detail.customer.name}</p>
                  <p><a href={`tel:${detail.customer.phone}`}>{detail.customer.phone}</a></p>
                  <p>{detail.address}</p>
                </div>
                <div className="rd-box">
                  <h3>Order</h3>
                  <ul className="rd-items">
                    {detail.items.map((i, idx) => <li key={`${i.productId}-${idx}`}><span>{i.quantity} ×</span> {i.name}</li>)}
                  </ul>
                  <p><strong>Total:</strong> {peso(detail.total)}</p>
                  <p><strong>Payment:</strong> {detail.paymentMethod}{detail.paymentStatus === "paid" ? " · Paid" : ""}</p>
                  {detail.amountToCollect > 0 && <p className="rd-collect">Collect cash: {peso(detail.amountToCollect)}</p>}
                </div>
                <div className="rd-box">
                  <h3>Delivery</h3>
                  <p><strong>Status:</strong> {detail.statusLabel}</p>
                  {detail.rescheduledFor && <p><strong>New date:</strong> {detail.rescheduledFor}</p>}
                  {detail.failedReason && <p><strong>Failed because:</strong> {detail.failedReason}</p>}
                </div>
              </div>

              {status === "ready_for_delivery" && (
                <div className="rd-action">
                  <p>When you leave the warehouse with the package, start the delivery.</p>
                  <button type="button" className="btn btn-primary btn-block rd-big" disabled={busy} onClick={() => run("start", {}, "Delivery started")}>Start delivery</button>
                </div>
              )}

              {status === "rescheduled" && (
                <div className="rd-action">
                  <p>This delivery was rescheduled{detail.rescheduledFor ? ` for ${detail.rescheduledFor}` : ""}. Start it on that day.</p>
                  <button type="button" className="btn btn-primary btn-block rd-big" disabled={busy} onClick={() => run("start", {}, "Delivery started")}>Start delivery</button>
                </div>
              )}

              {status === "shipped" && (
                <>
                  <div className="rd-step">
                    <h3><span>1</span> Scan every item</h3>
                    {detail.missing && detail.missing.length > 0 ? (
                      <ul className="rd-missing">
                        {detail.missing.map((m) => <li key={m.name}>{m.name}: {m.scanned} of {m.required} scanned</li>)}
                      </ul>
                    ) : <p className="rd-ok">All items are scanned.</p>}
                    {scanning ? (
                      <ScanConfirm onDetected={(code) => { setScanning(false); scanUnit(code); }} onClose={() => setScanning(false)} />
                    ) : (
                      <button type="button" className="btn btn-outline btn-block rd-big" onClick={() => setScanning(true)} disabled={busy}>Scan QR or barcode</button>
                    )}
                    <form className="rd-scan-form" onSubmit={(e) => { e.preventDefault(); scanUnit(scanCode); }}>
                      <input aria-label="Scanned code" autoComplete="off" value={scanCode} placeholder="Or type the code, or use a barcode scanner"
                        onChange={(e) => setScanCode(e.target.value)} />
                      <button type="submit" className="btn btn-outline" disabled={busy || !scanCode.trim()}>Add</button>
                    </form>
                  </div>

                  <div className="rd-step">
                    <h3><span>2</span> Take the delivery photo</h3>
                    <p className="rd-hint">Take a clear photo of the item at the delivery location, with the customer's signature visible.</p>
                    {detail.hasProof ? (
                      <p className="rd-ok">The photo is saved.</p>
                    ) : (
                      <>
                        <input id="rd-photo" type="file" accept="image/jpeg,image/png,image/webp" capture="environment" onChange={pickPhoto} />
                        {photoError && <p className="field-error" role="alert">{photoError}</p>}
                        {photo && <img className="rd-preview" alt="Preview of the delivery photo" src={URL.createObjectURL(photo)} />}
                        <button type="button" className="btn btn-primary btn-block rd-big" disabled={!photo || busy} onClick={uploadPhoto}>Save photo</button>
                      </>
                    )}
                  </div>

                  <div className="rd-step">
                    <h3><span>3</span> Confirm the result</h3>
                    <button type="button" className="btn btn-primary btn-block rd-big rd-delivered" disabled={!canDeliver}
                      onClick={() => run("deliver", {}, "Marked as delivered")}>
                      Delivered
                    </button>
                    {!canDeliver && <p className="rd-hint">Scan every item and save the photo first.</p>}
                    {!failing ? (
                      <button type="button" className="btn btn-outline btn-block rd-big rd-failed" disabled={busy} onClick={() => setFailing(true)}>
                        Failed, could not deliver today
                      </button>
                    ) : (
                      <div className="rd-fail-box">
                        <label htmlFor="rd-reason">Why could the delivery not be made? The admin will see this.</label>
                        <textarea id="rd-reason" rows={3} maxLength={500} value={failReason} placeholder="For example: heavy traffic, emergency in the area, customer not available"
                          onChange={(e) => setFailReason(e.target.value)} />
                        <div className="form-actions">
                          <button type="button" className="btn btn-outline" onClick={() => setFailing(false)}>Back</button>
                          <button type="button" className="btn btn-primary" disabled={busy || failReason.trim().length < 5}
                            onClick={async () => {
                              const ok = await run("fail", { reason: failReason.trim() }, "Reported as failed. The admin will confirm the new date.");
                              if (ok) { setFailing(false); setFailReason(""); }
                            }}>
                            Send failed report
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                </>
              )}

              {status === "delivery_failed" && (
                <div className="rd-action">
                  <p>You reported this delivery as failed. The admin will confirm it and set a new date.</p>
                </div>
              )}

              {status === "delivered" && (
                <div className="rd-action"><p className="rd-ok">This order was delivered.</p></div>
              )}
            </>
          )}
        </section>
      )}
    </div>
  );
}
