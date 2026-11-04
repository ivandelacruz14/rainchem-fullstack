import { useCallback, useEffect, useState } from "react";
import client from "../../api/client";
import { useAdminAuth } from "../../context/AdminAuthContext";
import { useToast } from "../../context/ToastContext";
import { formatDate } from "../../utils/format";
import AlertDetail from "../inventory/AlertDetail";

const STATUS_CLASS = { open: "req-rejected", under_review: "req-pending", resolved: "req-approved" };

function Alerts({ isHead }) {
  const showToast = useToast();
  const [filters, setFilters] = useState({ status: "unresolved", category: "", product_id: "", from: "", to: "", page: 1 });
  const [data, setData] = useState(null);
  const [products, setProducts] = useState([]);
  const [openId, setOpenId] = useState(null);
  const [scanning, setScanning] = useState(false);
  const [first, setFirst] = useState(true);

  const load = useCallback((refresh = false) => {
    const params = Object.fromEntries(Object.entries(filters).filter(([, v]) => v !== ""));
    if (refresh) params.refresh = 1;
    client.get("/api/admin/inventory/alerts", { params }).then((res) => setData(res.data)).catch(() => setData({ alerts: [], total: 0, counts: {}, categories: [] }));
  }, [filters]);
  useEffect(() => { load(first); setFirst(false); }, [load]); // the first load also runs the checks
  useEffect(() => { client.get("/api/admin/inventory/overview").then((res) => setProducts(res.data.products)).catch(() => {}); }, []);

  async function scan() {
    setScanning(true);
    try {
      const res = await client.post("/api/admin/inventory/scan");
      showToast(res.data.created ? `${res.data.created} new alert(s) found` : "No new problems found", res.data.created ? "error" : "success");
      load();
    } catch (err) {
      showToast(err.response?.data?.error || "The check could not run", "error");
    } finally {
      setScanning(false);
    }
  }

  const set = (patch) => setFilters((p) => ({ ...p, page: 1, ...patch }));
  const pages = data ? Math.max(1, Math.ceil(data.total / (data.perPage || 25))) : 1;

  return (
    <div>
      <div className="admin-panel filter-panel">
        <div className="sheet-filters">
          <div className="field"><label htmlFor="al-status">Status</label>
            <select id="al-status" value={filters.status} onChange={(e) => set({ status: e.target.value })}>
              <option value="unresolved">Unresolved</option><option value="open">Open</option><option value="under_review">Under review</option><option value="resolved">Resolved</option><option value="all">All</option>
            </select></div>
          <div className="field"><label htmlFor="al-cat">Type</label>
            <select id="al-cat" value={filters.category} onChange={(e) => set({ category: e.target.value })}>
              <option value="">All types</option>{data?.categories.map((c) => <option key={c.key} value={c.key}>{c.label}</option>)}
            </select></div>
          <div className="field"><label htmlFor="al-product">Product</label>
            <select id="al-product" value={filters.product_id} onChange={(e) => set({ product_id: e.target.value })}>
              <option value="">All products</option>{products.map((p) => <option key={p.productId} value={p.productId}>{p.name}</option>)}
            </select></div>
          <div className="field"><label htmlFor="al-from">Detected from</label><input id="al-from" type="date" value={filters.from} onChange={(e) => set({ from: e.target.value })} /></div>
          <div className="field"><label htmlFor="al-to">to</label><input id="al-to" type="date" value={filters.to} onChange={(e) => set({ to: e.target.value })} /></div>
          <div className="sheet-filter-actions"><button type="button" className="btn btn-primary btn-sm" disabled={scanning} onClick={scan}>{scanning ? "Checking..." : "Run check now"}</button></div>
        </div>
        <p className="field-hint" style={{ margin: 0 }}>
          The checks follow fixed rules (stock history, duplicate movements, repeated order processing, payment references, restored stock, unexplained adjustments, and sales records). They do not use machine learning, and they never change records on their own.
        </p>
      </div>

      {data && (
        <div className="sheet-totals">
          <span><strong>{data.counts.open ?? 0}</strong> open</span><span><strong>{data.counts.under_review ?? 0}</strong> under review</span><span><strong>{data.counts.resolved ?? 0}</strong> resolved</span>
        </div>
      )}

      <div className="admin-panel">
        <div className="table-wrap">
          <table className="admin-table stack">
            <thead><tr><th>Alert</th><th>Detected</th><th>Type</th><th>Product / order</th><th>Expected</th><th>Recorded</th><th>Difference</th><th>Status</th><th>Assigned</th><th></th></tr></thead>
            <tbody>
              {!data ? <tr><td colSpan={10}>Loading...</td></tr> : data.alerts.length === 0 ? (
                <tr><td colSpan={10}>No alerts here. Valid stock movements do not create alerts.</td></tr>
              ) : data.alerts.map((a) => (
                <tr key={a.id}>
                  <td data-label="Alert" className="mono">#{a.id}</td>
                  <td data-label="Detected">{formatDate(a.detectedAt)}</td>
                  <td data-label="Type" className="cell-name">{a.categoryLabel}</td>
                  <td data-label="Product / order" className="cell-wrap">{a.productName || "-"}{a.orderNumber && <div className="muted">{a.orderNumber}</div>}</td>
                  <td data-label="Expected">{a.expected ?? "-"}</td><td data-label="Recorded">{a.recorded ?? "-"}</td><td data-label="Difference">{a.difference ?? "-"}</td>
                  <td data-label="Status"><span className={`status-pill ${STATUS_CLASS[a.status]}`}>{a.status.replace("_", " ")}</span></td>
                  <td data-label="Assigned">{a.assignedTo || "-"}</td>
                  <td data-label="" className="row-cell"><button type="button" className="icon-action wide" onClick={() => setOpenId(a.id)}>{a.status === "resolved" ? "View" : "Investigate"}</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {data && data.total > 0 && (
          <div className="pager">
            <span>Page {filters.page} of {pages} &middot; {data.total} alerts</span>
            <div className="row-actions">
              <button type="button" className="btn btn-outline btn-sm" disabled={filters.page <= 1} onClick={() => setFilters((p) => ({ ...p, page: p.page - 1 }))}>Previous</button>
              <button type="button" className="btn btn-outline btn-sm" disabled={filters.page >= pages} onClick={() => setFilters((p) => ({ ...p, page: p.page + 1 }))}>Next</button>
            </div>
          </div>
        )}
      </div>
      {openId && <AlertDetail alertId={openId} isHead={isHead} onClose={() => setOpenId(null)} onChanged={() => load()} />}
    </div>
  );
}

function StockOverview({ isHead }) {
  const showToast = useToast();
  const [rows, setRows] = useState(null);
  const [form, setForm] = useState({ productId: "", type: "received", quantity: "", reason: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const load = () => client.get("/api/admin/inventory/overview").then((res) => setRows(res.data.products));
  useEffect(() => { load(); }, []);

  async function record(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await client.post("/api/admin/inventory/movements", { ...form, productId: Number(form.productId), quantity: Number(form.quantity) });
      showToast("Stock movement recorded", "success");
      setForm({ productId: "", type: "received", quantity: "", reason: "" });
      load();
    } catch (err) {
      setError(err.response?.data?.error || "The movement could not be recorded.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      {isHead && (
        <form className="admin-panel" onSubmit={record}>
          <h3>Record a stock movement</h3>
          {error && <div className="alert alert-error" role="alert">{error}</div>}
          <div className="sheet-filters">
            <div className="field"><label htmlFor="mv-product">Product</label>
              <select id="mv-product" required value={form.productId} onChange={(e) => setForm({ ...form, productId: e.target.value })}>
                <option value="">Choose a product</option>{rows?.map((p) => <option key={p.productId} value={p.productId}>{p.name}</option>)}
              </select></div>
            <div className="field"><label htmlFor="mv-type">Type</label>
              <select id="mv-type" value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}>
                <option value="received">Stock received</option><option value="write_off">Damaged or written off</option><option value="adjustment">Adjustment (use + or -)</option>
              </select></div>
            <div className="field"><label htmlFor="mv-qty">Units</label><input id="mv-qty" type="number" step="1" required value={form.quantity} onChange={(e) => setForm({ ...form, quantity: e.target.value })} /></div>
            <div className="field"><label htmlFor="mv-reason">Reason (required)</label><input id="mv-reason" required maxLength={255} value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} /></div>
            <div className="sheet-filter-actions"><button type="submit" className="btn btn-primary btn-sm" disabled={busy}>{busy ? "Saving..." : "Record"}</button></div>
          </div>
        </form>
      )}
      <div className="admin-panel">
        <p className="field-hint" style={{ marginTop: 0 }}>Expected stock = opening + received + returned or restored + adjustments &minus; issued to orders. Tracking started from each product's baseline.</p>
        <div className="table-wrap">
          <table className="admin-table stack">
            <thead><tr><th>Product</th><th>Opening</th><th>Received</th><th>Issued</th><th>Returned</th><th>Adjusted</th><th>Expected</th><th>Recorded</th><th>Difference</th></tr></thead>
            <tbody>
              {!rows ? <tr><td colSpan={9}>Loading...</td></tr> : rows.map((r) => (
                <tr key={r.productId} className={r.difference !== 0 ? "row-flag" : ""}>
                  <td data-label="Product" className="cell-name">{r.name}</td><td data-label="Opening">{r.opening}</td><td data-label="Received">{r.received}</td>
                  <td data-label="Issued">{r.issued}</td><td data-label="Returned">{r.returned}</td><td data-label="Adjusted">{r.adjusted}</td>
                  <td data-label="Expected">{r.expected}</td><td data-label="Recorded"><strong>{r.recorded}</strong></td>
                  <td data-label="Difference">{r.difference === 0 ? "-" : <span className="pill pill-low">{r.difference > 0 ? `+${r.difference}` : r.difference}</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function Movements() {
  const [data, setData] = useState(null);
  const [page, setPage] = useState(1);
  useEffect(() => { client.get("/api/admin/inventory/movements", { params: { page } }).then((res) => setData(res.data)); }, [page]);
  const pages = data ? Math.max(1, Math.ceil(data.total / data.perPage)) : 1;
  return (
    <div className="admin-panel">
      <div className="table-wrap">
        <table className="admin-table stack">
          <thead><tr><th>When</th><th>Product</th><th>Type</th><th>Change</th><th>Reference</th><th>Reason</th><th>By</th></tr></thead>
          <tbody>
            {!data ? <tr><td colSpan={7}>Loading...</td></tr> : data.movements.length === 0 ? <tr><td colSpan={7}>No movements yet.</td></tr> : data.movements.map((m) => (
              <tr key={m.id}><td data-label="When">{formatDate(m.at)}</td><td data-label="Product" className="cell-name">{m.productName}</td><td data-label="Type">{m.typeLabel}</td>
                <td data-label="Change">{m.change > 0 ? `+${m.change}` : m.change}</td><td data-label="Reference" className="mono">{m.reference || "-"}</td>
                <td data-label="Reason">{m.reason || <span className="muted">none</span>}</td><td data-label="By">{m.actor}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
      {data && data.total > 0 && (
        <div className="pager"><span>Page {page} of {pages}</span>
          <div className="row-actions">
            <button type="button" className="btn btn-outline btn-sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button>
            <button type="button" className="btn btn-outline btn-sm" disabled={page >= pages} onClick={() => setPage(page + 1)}>Next</button>
          </div></div>
      )}
    </div>
  );
}

export default function InventoryAlerts() {
  const { admin } = useAdminAuth();
  const [tab, setTab] = useState("alerts");
  return (
    <div>
      <div className="admin-topbar"><div><h1>Inventory Alerts</h1><p>Unusual stock and order records, found by fixed rules, for you to investigate.</p></div></div>
      <div className="tab-bar">
        {[["alerts", "Alerts"], ["stock", "Stock check"], ["movements", "Movement history"]].map(([key, label]) => (
          <button key={key} type="button" className={`tab-btn ${tab === key ? "active" : ""}`} onClick={() => setTab(key)}>{label}</button>
        ))}
      </div>
      {tab === "alerts" && <Alerts isHead={Boolean(admin?.isHead)} />}
      {tab === "stock" && <StockOverview isHead={Boolean(admin?.isHead)} />}
      {tab === "movements" && <Movements />}
    </div>
  );
}
