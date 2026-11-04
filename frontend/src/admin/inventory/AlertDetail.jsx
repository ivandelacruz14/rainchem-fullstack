import { useEffect, useState } from "react";
import client from "../../api/client";
import { useToast } from "../../context/ToastContext";
import { formatDate, peso } from "../../utils/format";

export default function AlertDetail({ alertId, isHead, onClose, onChanged }) {
  const showToast = useToast();
  const [data, setData] = useState(null);
  const [note, setNote] = useState("");
  const [mode, setMode] = useState("align_to_history");
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function load() {
    client.get(`/api/admin/inventory/alerts/${alertId}`).then((res) => setData(res.data)).catch(() => setData({ error: true }));
  }
  useEffect(load, [alertId]);

  async function act(path, body, done) {
    setBusy(true);
    setError("");
    try {
      await client.post(`/api/admin/inventory/alerts/${alertId}/${path}`, body);
      showToast(done, "success");
      setNote("");
      setReason("");
      load();
      onChanged();
    } catch (err) {
      setError(err.response?.data?.error || "That did not work. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  const alert = data?.alert;
  const open = alert && alert.status !== "resolved";

  return (
    <div className="overlay" onClick={onClose}>
      <div className="modal wide" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head"><h3 style={{ margin: 0 }}>Alert #{alertId}</h3><button type="button" className="modal-close" onClick={onClose}>&times;</button></div>
        <div className="modal-body">
          {!data ? <p className="field-hint">Loading...</p> : data.error ? <div className="alert alert-error">This alert could not be loaded.</div> : (
            <>
              <p className="alert-explain"><strong>{alert.categoryLabel}.</strong> {alert.explanation}</p>
              <dl className="detail-grid">
                <div><dt>Product</dt><dd>{alert.productName || "-"}</dd></div>
                <div><dt>Order</dt><dd>{alert.orderNumber || "-"}</dd></div>
                <div><dt>Expected</dt><dd>{alert.expected ?? "-"}</dd></div>
                <div><dt>Recorded</dt><dd>{alert.recorded ?? "-"}</dd></div>
                <div><dt>Difference</dt><dd>{alert.difference ?? "-"}</dd></div>
                <div><dt>Detected</dt><dd>{formatDate(alert.detectedAt)}</dd></div>
                <div><dt>Status</dt><dd>{alert.status.replace("_", " ")}</dd></div>
                <div><dt>Assigned to</dt><dd>{alert.assignedTo || "-"}</dd></div>
                {alert.resolvedAt && <div><dt>Resolved</dt><dd>{formatDate(alert.resolvedAt)} by {alert.resolvedBy}</dd></div>}
              </dl>
              {data.stillApplies === true && <div className="alert alert-error">The condition still exists right now.</div>}
              {data.stillApplies === false && open && <div className="alert alert-info">The condition no longer exists. You can resolve this alert with a note.</div>}

              {data.order && (
                <div className="review-block"><span className="chat-label">Original order</span>
                  <p>{data.order.orderNumber} &middot; {data.order.status} &middot; payment {data.order.paymentStatus} &middot; {peso(data.order.total)} &middot; reference {data.order.paymentReference || "none"}</p></div>
              )}

              {data.movements.length > 0 && (
                <>
                  <h4 className="pd-extra-head">Stock movement history</h4>
                  <div className="table-wrap"><table className="admin-table">
                    <thead><tr><th>When</th><th>Type</th><th>Change</th><th>Reference</th><th>Reason</th><th>By</th></tr></thead>
                    <tbody>{data.movements.map((m) => (
                      <tr key={m.id}><td>{formatDate(m.at)}</td><td>{m.typeLabel}</td><td>{m.change > 0 ? `+${m.change}` : m.change}</td><td className="mono">{m.reference || "-"}</td><td>{m.reason || <span className="muted">none</span>}</td><td>{m.actor}</td></tr>
                    ))}</tbody>
                  </table></div>
                </>
              )}

              {alert.resolutionNote && <><h4 className="pd-extra-head">Notes</h4><pre className="notes-pre">{alert.resolutionNote}</pre></>}
              {data.history.length > 0 && (
                <ul className="context-list">{data.history.map((h) => <li key={h.id}><strong>{h.action.replace(/_/g, " ")}</strong><span>{h.admin}</span><time>{formatDate(h.at)}</time></li>)}</ul>
              )}

              {error && <div className="alert alert-error" role="alert">{error}</div>}

              {open && (
                <>
                  <div className="form-actions" style={{ justifyContent: "flex-start" }}>
                    {alert.status === "open" && <button type="button" className="btn btn-outline" disabled={busy} onClick={() => act("review", {}, "Review started")}>Start review</button>}
                  </div>
                  <div className="field">
                    <label htmlFor="alert-note">Note</label>
                    <textarea id="alert-note" rows={2} value={note} maxLength={500} onChange={(e) => setNote(e.target.value)} />
                  </div>
                  <div className="form-actions" style={{ justifyContent: "flex-start" }}>
                    <button type="button" className="btn btn-outline" disabled={busy || !note.trim()} onClick={() => act("note", { note }, "Note added")}>Add note</button>
                    <button type="button" className="btn btn-primary" disabled={busy || !note.trim()} onClick={() => act("resolve", { note }, "Alert resolved")}>Resolve with this note</button>
                  </div>
                  <p className="field-hint">Resolving closes the alert only. It never changes stock, orders or payments.</p>

                  {isHead && alert.category === "stock_mismatch" && data.stillApplies !== false && (
                    <fieldset className="correct-box">
                      <legend>Correct the stock (Head Admin)</legend>
                      <label className="perm-item"><input type="radio" name="mode" checked={mode === "align_to_history"} onChange={() => setMode("align_to_history")} />
                        <span>The history is right. Set the recorded stock to {alert.expected}.</span></label>
                      <label className="perm-item"><input type="radio" name="mode" checked={mode === "accept_recorded"} onChange={() => setMode("accept_recorded")} />
                        <span>The recorded stock ({alert.recorded}) is right. Add the missing adjustment to the history.</span></label>
                      <div className="field"><label htmlFor="correct-reason">Reason (required, kept in the audit log)</label>
                        <input id="correct-reason" value={reason} maxLength={300} onChange={(e) => setReason(e.target.value)} /></div>
                      <button type="button" className="btn btn-primary" disabled={busy || !reason.trim()} onClick={() => act("correct", { mode, reason }, "Stock corrected")}>Apply correction</button>
                    </fieldset>
                  )}
                </>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
