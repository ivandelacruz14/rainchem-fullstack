import { useEffect, useState } from "react";
import client from "../../api/client";
import { useToast } from "../../context/ToastContext";
import { formatDate, peso } from "../../utils/format";

const FIELDS = [
  ["Record ID", "id"], ["Order", "orderNumber"], ["Transaction reference", "transactionRef"], ["Customer", "customerName"],
  ["Product", "productName"], ["SKU", "sku"], ["Category", "category"], ["Quantity", "quantity"],
  ["Payment method", "paymentMethod"], ["Payment status", "paymentStatus"], ["Order status", "orderStatus"],
  ["Fulfillment", "fulfillmentStatus"], ["Refund", "refundStatus"], ["Return", "returnStatus"], ["Sale state", "state"], ["Notes", "notes"],
];
const MONEY = [
  ["List price", "listUnitPrice"], ["Unit price paid", "unitPrice"], ["Subtotal", "subtotal"], ["Discount", "discountAmount"],
  ["Line total", "lineTotal"], ["Shipping share", "shippingShare"], ["Tax", "taxAmount"], ["Order total", "orderTotal"],
];

export default function RecordDetail({ recordId, isHead, onClose, onChanged }) {
  const showToast = useToast();
  const [data, setData] = useState(null);
  const [form, setForm] = useState({ field: "category", value: "", reason: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function load() {
    client.get(`/api/admin/sales-records/${recordId}`).then((res) => setData(res.data)).catch(() => setData({ error: true }));
  }
  useEffect(load, [recordId]);

  async function correct(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await client.post(`/api/admin/sales-records/${recordId}/correction`, form);
      showToast("Correction saved and recorded in the audit log", "success");
      setForm({ field: "category", value: "", reason: "" });
      load();
      onChanged();
    } catch (err) {
      setError(err.response?.data?.error || "The correction could not be saved.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="overlay" onClick={onClose}>
      <div className="modal wide" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head"><h3 style={{ margin: 0 }}>Transaction details</h3><button type="button" className="modal-close" onClick={onClose}>&times;</button></div>
        <div className="modal-body">
          {!data ? <p className="field-hint">Loading...</p> : data.error ? <div className="alert alert-error">This record could not be loaded.</div> : (
            <>
              <p className="field-hint" style={{ marginTop: 0 }}>
                Read only. Amounts are copied from the order at the time of sale and cannot be edited here.
                {data.order && <> Ordered {formatDate(data.order.createdAt)}{data.order.paidAt ? `, paid ${formatDate(data.order.paidAt)}` : ""}.</>}
              </p>
              <dl className="detail-grid">
                {FIELDS.map(([label, key]) => <div key={key}><dt>{label}</dt><dd>{data.record[key] ?? "-"}</dd></div>)}
                {MONEY.map(([label, key]) => <div key={key}><dt>{label}</dt><dd>{peso(data.record[key])}</dd></div>)}
              </dl>
              {data.record.corrected && <div className="alert alert-info">Some descriptive fields were corrected. See the history below.</div>}

              <h4 className="pd-extra-head">Lines in this order</h4>
              <div className="table-wrap">
                <table className="admin-table">
                  <thead><tr><th>Product</th><th>Qty</th><th>Unit price</th><th>Line total</th><th>State</th></tr></thead>
                  <tbody>{data.lines.map((l) => <tr key={l.id}><td>{l.productName}</td><td>{l.quantity}</td><td>{peso(l.unitPrice)}</td><td>{peso(l.lineTotal)}</td><td>{l.state}</td></tr>)}</tbody>
                </table>
              </div>

              {data.corrections.length > 0 && (
                <>
                  <h4 className="pd-extra-head">Correction history</h4>
                  <ul className="context-list">
                    {data.corrections.map((c) => (
                      <li key={c.id}>
                        <strong>{c.admin}</strong><span>{Object.keys(c.new)[0]}: {String(Object.values(c.old)[0] ?? "-")} &rarr; {String(Object.values(c.new)[0] ?? "-")}</span>
                        <span>Reason: {c.reason}</span><time>{formatDate(c.at)}</time>
                      </li>
                    ))}
                  </ul>
                </>
              )}

              {isHead && (
                <form onSubmit={correct} className="correction-form">
                  <h4 className="pd-extra-head">Correct a descriptive field</h4>
                  {error && <div className="alert alert-error" role="alert">{error}</div>}
                  <div className="field-row">
                    <div className="field"><label htmlFor="corr-field">Field</label>
                      <select id="corr-field" value={form.field} onChange={(e) => setForm({ ...form, field: e.target.value })}>
                        <option value="category">Category</option><option value="sku">SKU</option><option value="notes">Notes</option>
                      </select></div>
                    <div className="field"><label htmlFor="corr-value">New value</label><input id="corr-value" value={form.value} onChange={(e) => setForm({ ...form, value: e.target.value })} /></div>
                  </div>
                  <div className="field"><label htmlFor="corr-reason">Reason (required)</label><input id="corr-reason" value={form.reason} maxLength={500} onChange={(e) => setForm({ ...form, reason: e.target.value })} /></div>
                  <button type="submit" className="btn btn-outline" disabled={busy || !form.reason.trim()}>{busy ? "Saving..." : "Save correction"}</button>
                </form>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
