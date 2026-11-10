import { useEffect, useState } from "react";
import client from "../../api/client";
import ConfirmDialog from "../../components/ConfirmDialog";
import { useToast } from "../../context/ToastContext";
import { formatDate, peso } from "../../utils/format";

function Totals({ totals }) {
  return (
    <div className="sheet-totals">
      <span><strong>{totals.lines}</strong> lines</span>
      <span><strong>{totals.orders}</strong> orders</span>
      <span><strong>{totals.units}</strong> units</span>
      <span>Gross <strong>{peso(totals.gross)}</strong></span>
      <span>Discounts <strong>{peso(totals.discounts)}</strong></span>
      <span>Net <strong>{peso(totals.net)}</strong></span>
      <span>Refunds <strong>{peso(totals.refunds)}</strong></span>
    </div>
  );
}

/** Imports sales from a marketplace Excel file. The file is checked first; nothing is saved until confirmed. */
export default function ImportSales({ onClose, onChanged }) {
  const showToast = useToast();
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [batches, setBatches] = useState(null);
  const [toRemove, setToRemove] = useState(null);

  function loadBatches() {
    client.get("/api/admin/sales-records/imports").then((res) => setBatches(res.data.batches)).catch(() => setBatches([]));
  }
  useEffect(loadBatches, []);

  function pick(e) {
    setFile(e.target.files?.[0] || null);
    setPreview(null);
    setError("");
  }

  function sendFile(path, extra = {}) {
    const form = new FormData();
    form.append("file", file);
    Object.entries(extra).forEach(([k, v]) => form.append(k, v));
    return client.post(`/api/admin/sales-records${path}`, form);
  }

  async function check() {
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      const res = await sendFile("/import/preview");
      setPreview(res.data);
    } catch (err) {
      setPreview(null);
      setError(err.response?.data?.error || "The file could not be checked.");
    } finally {
      setBusy(false);
    }
  }

  async function importRows() {
    setBusy(true);
    setError("");
    try {
      const res = await sendFile("/import", { confirm: "yes" });
      showToast(`Imported ${res.data.rows} rows as batch ${res.data.batch}`, "success");
      setFile(null);
      setPreview(null);
      loadBatches();
      onChanged();
    } catch (err) {
      setError(err.response?.data?.error || "The import failed. Nothing was saved.");
    } finally {
      setBusy(false);
    }
  }

  async function removeBatch() {
    try {
      const res = await client.delete(`/api/admin/sales-records/imports/${toRemove.batch}`);
      showToast(`Removed ${res.data.removed} imported rows`, "success");
      setToRemove(null);
      loadBatches();
      onChanged();
    } catch (err) {
      showToast(err.response?.data?.error || "Could not remove the import", "error");
      setToRemove(null);
    }
  }

  const declaredNet = preview?.declared?.["Net sales"];
  const matches = declaredNet !== undefined && preview && Math.abs(declaredNet - preview.totals.net) < 0.01;

  return (
    <div className="overlay" onClick={onClose}>
      <div className="modal wide" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h3 style={{ margin: 0 }}>Import sales from Excel</h3>
          <button type="button" className="modal-close" onClick={onClose}>&times;</button>
        </div>
        <div className="modal-body">
          <p className="field-hint" style={{ marginTop: 0 }}>
            Upload an .xlsx file with an <strong>Orders</strong> sheet. Columns needed: Order No., Order Date, Product, Qty, Unit Price, Net Amount.
            The file is checked first. Imported rows are marked "Imported" and do not change real orders, payments, or stock.
          </p>
          {error && <div className="alert alert-error" role="alert">{error}</div>}

          <div className="import-pick">
            <input type="file" accept=".xlsx" aria-label="Excel file" onChange={pick} />
            <button type="button" className="btn btn-outline" disabled={!file || busy} onClick={check}>{busy ? "Checking..." : "Check file"}</button>
          </div>

          {preview && (
            <div className="import-preview">
              <div className="alert alert-info">
                Sheet <strong>{preview.sheet}</strong>: {preview.rows} rows. <strong>{preview.valid}</strong> will be imported,
                {" "}{preview.alreadyImported} already imported, <strong>{preview.errorCount}</strong> with errors.
              </div>
              <Totals totals={preview.totals} />
              {preview.declared && Object.keys(preview.declared).length > 0 && (
                <p className="field-hint">
                  The file's Summary sheet says net sales {peso(declaredNet)}.
                  {" "}{matches ? "This matches the rows." : "This does not match the rows that will be imported."}
                </p>
              )}
              {preview.errorCount > 0 && (
                <>
                  <h4 className="pd-extra-head">Rows that will be skipped</h4>
                  <ul className="import-errors">
                    {preview.errors.map((e) => <li key={`${e.row}-${e.message}`}>Row {e.row}: {e.message}</li>)}
                  </ul>
                  {preview.errorCount > preview.errors.length && <p className="field-hint">and {preview.errorCount - preview.errors.length} more</p>}
                </>
              )}
              <div className="form-actions">
                <button type="button" className="btn btn-primary" disabled={busy || preview.valid === 0} onClick={importRows}>
                  {busy ? "Importing..." : `Import ${preview.valid} rows`}
                </button>
              </div>
            </div>
          )}

          <h4 className="pd-extra-head">Imported batches</h4>
          {batches === null ? <p className="field-hint">Loading...</p> : batches.length === 0 ? (
            <p className="field-hint">No imports yet.</p>
          ) : (
            <div className="table-wrap">
              <table className="admin-table">
                <thead><tr><th>Imported</th><th>Rows</th><th>Orders</th><th>Net</th><th></th></tr></thead>
                <tbody>
                  {batches.map((b) => (
                    <tr key={b.batch}>
                      <td>{b.createdAt ? formatDate(b.createdAt) : "-"}</td><td>{b.rows}</td><td>{b.orders}</td><td>{peso(b.net)}</td>
                      <td><button type="button" className="icon-action wide" onClick={() => setToRemove(b)}>Remove</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
      {toRemove && (
        <ConfirmDialog
          title="Remove this import?" confirmLabel="Remove import"
          message={`All ${toRemove.rows} imported rows from this batch will be deleted. Real orders are not affected. This cannot be undone.`}
          onCancel={() => setToRemove(null)} onConfirm={removeBatch}
        />
      )}
    </div>
  );
}
