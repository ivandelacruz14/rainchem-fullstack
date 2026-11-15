import { useCallback, useEffect, useState } from "react";
import client from "../../api/client";
import ConfirmDialog from "../../components/ConfirmDialog";
import { useAdminAuth } from "../../context/AdminAuthContext";
import { useToast } from "../../context/ToastContext";
import { downloadFile } from "../../utils/download";
import { formatDate, peso } from "../../utils/format";
import ImportSales from "../sales-records/ImportSales";
import RecordDetail from "../sales-records/RecordDetail";
import SalesReports from "../sales-records/SalesReports";

const EMPTY = { q: "", from: "", to: "", product_id: "", category: "", payment_status: "", order_status: "", state: "", source: "", sort: "date", dir: "desc", page: 1, per_page: 25 };
const COLUMNS = [
  ["date", "Date and time"], [null, "Order"], [null, "Reference"], ["customer", "Customer"], ["product", "Product"], [null, "SKU"], [null, "Category"],
  ["quantity", "Qty"], ["price", "Unit price"], [null, "Subtotal"], [null, "Discount"], ["total", "Line total"], [null, "Shipping"], ["order_total", "Order total"],
  [null, "Payment"], [null, "Order status"], [null, "Fulfillment"], [null, "State"],
];
const STATE_CLASS = { completed: "req-approved", pending: "req-pending", cancelled: "req-rejected", refunded: "req-rejected", returned: "req-rejected" };

function cleanParams(filters) {
  return Object.fromEntries(Object.entries(filters).filter(([, v]) => v !== "" && v !== null));
}

export default function SalesRecords() {
  const { admin } = useAdminAuth();
  const showToast = useToast();
  const [tab, setTab] = useState("records");
  const [filters, setFilters] = useState(EMPTY);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [openId, setOpenId] = useState(null);
  const [exporting, setExporting] = useState(false);
  const [importing, setImporting] = useState(false);
  const [confirmReconcile, setConfirmReconcile] = useState(false);

  const load = useCallback(() => {
    client.get("/api/admin/sales-records", { params: cleanParams(filters) })
      .then((res) => { setData(res.data); setError(""); })
      .catch((err) => setError(err.response?.data?.error || "The records could not be loaded."));
  }, [filters]);
  useEffect(() => { if (tab === "records") load(); }, [load, tab]);

  const set = (patch) => setFilters((p) => ({ ...p, page: 1, ...patch }));
  const sortBy = (key) => setFilters((p) => ({ ...p, page: 1, sort: key, dir: p.sort === key && p.dir === "desc" ? "asc" : "desc" }));

  async function exportCsv() {
    setExporting(true);
    try {
      const { page, per_page, ...rest } = cleanParams(filters);
      await downloadFile(client, "/api/admin/sales-records/export.csv", rest, "rainchem-sales-records.csv");
    } catch (err) {
      showToast(err.response?.data?.error || "The export could not be created", "error");
    } finally {
      setExporting(false);
    }
  }

  async function reconcile() {
    try {
      const res = await client.post("/api/admin/sales-records/reconcile");
      showToast(`Checked ${res.data.orders} orders. ${res.data.records} records.`, "success");
      setConfirmReconcile(false);
      load();
    } catch (err) {
      showToast(err.response?.data?.error || "Could not reconcile", "error");
      setConfirmReconcile(false);
    }
  }

  const t = data?.totals;
  const filtered = JSON.stringify(cleanParams({ ...filters, sort: "", dir: "", page: "", per_page: "" })) !== "{}";

  return (
    <div>
      <div className="admin-topbar">
        <div>
          <h1>Sales Records</h1>
          <p>Every product line of every order, filled in automatically. Read only: amounts come from the orders. Excel imports are marked "Imported".</p>
        </div>
        <div className="row-actions">
          {tab === "records" && <button type="button" className="btn btn-primary" disabled={exporting || !data?.total} onClick={exportCsv}>{exporting ? "Preparing..." : "Export CSV"}</button>}
          {admin?.isHead && tab === "records" && <button type="button" className="btn btn-outline" onClick={() => setImporting(true)}>Import Excel</button>}
          {admin?.isHead && <button type="button" className="btn btn-outline" onClick={() => setConfirmReconcile(true)}>Reconcile with orders</button>}
        </div>
      </div>

      <div className="tab-bar">
        <button type="button" className={`tab-btn ${tab === "records" ? "active" : ""}`} onClick={() => setTab("records")}>Records</button>
        <button type="button" className={`tab-btn ${tab === "reports" ? "active" : ""}`} onClick={() => setTab("reports")}>Summary and reports</button>
      </div>

      {tab === "reports" ? <SalesReports /> : (
        <>
          <div className="admin-panel sheet-filters">
            <div className="field"><label htmlFor="sr-q">Search</label><input id="sr-q" type="search" placeholder="Order, customer, product or SKU" value={filters.q} onChange={(e) => set({ q: e.target.value })} /></div>
            <div className="field"><label htmlFor="sr-from">From</label><input id="sr-from" type="date" value={filters.from} onChange={(e) => set({ from: e.target.value })} /></div>
            <div className="field"><label htmlFor="sr-to">To</label><input id="sr-to" type="date" value={filters.to} onChange={(e) => set({ to: e.target.value })} /></div>
            <div className="field"><label htmlFor="sr-source">Source</label>
              <select id="sr-source" value={filters.source} onChange={(e) => set({ source: e.target.value })}>
                <option value="">All records</option><option value="order">From orders</option><option value="import">Imported (Excel)</option>
              </select></div>
            <div className="field"><label htmlFor="sr-product">Product</label>
              <select id="sr-product" value={filters.product_id} onChange={(e) => set({ product_id: e.target.value })}>
                <option value="">All products</option>{data?.filters.products.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select></div>
            <div className="field"><label htmlFor="sr-cat">Category</label>
              <select id="sr-cat" value={filters.category} onChange={(e) => set({ category: e.target.value })}>
                <option value="">All categories</option>{data?.filters.categories.map((c) => <option key={c}>{c}</option>)}
              </select></div>
            <div className="field"><label htmlFor="sr-state">Sale state</label>
              <select id="sr-state" value={filters.state} onChange={(e) => set({ state: e.target.value })}>
                <option value="">All</option><option value="completed">Completed</option><option value="pending">Pending</option><option value="cancelled">Cancelled</option><option value="refunded">Refunded</option><option value="returned">Returned</option>
              </select></div>
            <div className="field"><label htmlFor="sr-pay">Payment</label>
              <select id="sr-pay" value={filters.payment_status} onChange={(e) => set({ payment_status: e.target.value })}>
                <option value="">All</option><option value="paid">Paid</option><option value="unpaid">Unpaid</option><option value="verifying">Verifying</option><option value="refund_pending">Refund pending</option><option value="refunded">Refunded</option>
              </select></div>
            <div className="field"><label htmlFor="sr-order">Order status</label>
              <select id="sr-order" value={filters.order_status} onChange={(e) => set({ order_status: e.target.value })}>
                <option value="">All</option><option value="pending_confirmation">Pending confirmation</option><option value="confirmed">Confirmed</option><option value="processing">Processing</option><option value="shipped">Shipped</option><option value="delivered">Delivered</option><option value="cancelled">Cancelled</option>
              </select></div>
            <div className="sheet-filter-actions">
              <button type="button" className="btn btn-outline btn-sm" disabled={!filtered} onClick={() => setFilters(EMPTY)}>Clear filters</button>
            </div>
          </div>

          {error && <div className="alert alert-error">{error}</div>}

          {t && (
            <div className="sheet-totals" aria-label="Totals for the rows shown">
              <span><strong>{t.rows}</strong> rows</span><span><strong>{t.units}</strong> units</span>
              <span>Subtotal <strong>{peso(t.subtotal)}</strong></span><span>Discounts <strong>{peso(t.discounts)}</strong></span><span>Line total <strong>{peso(t.lineTotal)}</strong></span>
            </div>
          )}

          <div className="sheet-wrap">
            <table className="sheet" aria-label="Sales records">
              <thead>
                <tr>
                  {COLUMNS.map(([key, label]) => (
                    <th key={label} aria-sort={key && filters.sort === key ? (filters.dir === "asc" ? "ascending" : "descending") : undefined}>
                      {key ? <button type="button" className="sort-btn" onClick={() => sortBy(key)}>{label}{filters.sort === key ? (filters.dir === "asc" ? " \u25B2" : " \u25BC") : ""}</button> : label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {!data ? <tr><td colSpan={COLUMNS.length}>Loading...</td></tr> : data.records.length === 0 ? (
                  <tr><td colSpan={COLUMNS.length} className="sheet-empty">{filtered ? "No records match these filters." : "No sales have been recorded yet. Records appear here automatically when orders are placed."}</td></tr>
                ) : data.records.map((r) => (
                  <tr key={r.id} className="sheet-row" tabIndex={0} onClick={() => setOpenId(r.id)} onKeyDown={(e) => { if (e.key === "Enter") setOpenId(r.id); }}>
                    <td>{formatDate(r.soldAt)}</td><td className="mono">{r.orderNumber}</td><td className="mono">{r.transactionRef}</td>
                    <td>{r.customerName}</td>
                    <td>{r.productName}{r.variant && <div className="muted">{r.variant}</div>}{r.source === "import" && <span className="pill import-pill">Imported</span>}</td>
                    <td className="mono">{r.sku || "-"}</td><td>{r.category || "-"}</td>
                    <td className="num">{r.quantity}</td><td className="num">{peso(r.unitPrice)}</td><td className="num">{peso(r.subtotal)}</td>
                    <td className="num">{peso(r.discountAmount)}</td><td className="num"><strong>{peso(r.lineTotal)}</strong></td><td className="num">{peso(r.shippingShare)}</td><td className="num">{peso(r.orderTotal)}</td>
                    <td>{r.paymentMethod}<div className="muted">{r.paymentStatus}</div></td><td>{r.orderStatus}</td><td>{r.fulfillmentStatus}</td>
                    <td><span className={`status-pill ${STATE_CLASS[r.state] || ""}`}>{r.state}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {data && data.total > 0 && (
            <div className="pager">
              <span>Page {data.page} of {data.pages}</span>
              <div className="row-actions">
                <button type="button" className="btn btn-outline btn-sm" disabled={data.page <= 1} onClick={() => setFilters((p) => ({ ...p, page: p.page - 1 }))}>Previous</button>
                <button type="button" className="btn btn-outline btn-sm" disabled={data.page >= data.pages} onClick={() => setFilters((p) => ({ ...p, page: p.page + 1 }))}>Next</button>
                <select aria-label="Rows per page" value={filters.per_page} onChange={(e) => set({ per_page: Number(e.target.value) })}>
                  {[10, 25, 50, 100].map((n) => <option key={n} value={n}>{n} per page</option>)}
                </select>
              </div>
            </div>
          )}
        </>
      )}

      {openId && <RecordDetail recordId={openId} isHead={Boolean(admin?.isHead)} onClose={() => setOpenId(null)} onChanged={load} />}
      {importing && <ImportSales onClose={() => setImporting(false)} onChanged={load} />}
      {confirmReconcile && (
        <ConfirmDialog title="Reconcile with orders?" confirmLabel="Reconcile" danger={false}
          message="Every order record is rebuilt from its order. Imported rows are not changed. Descriptive corrections you made are kept. This is safe to repeat." onCancel={() => setConfirmReconcile(false)} onConfirm={reconcile} />
      )}
    </div>
  );
}
