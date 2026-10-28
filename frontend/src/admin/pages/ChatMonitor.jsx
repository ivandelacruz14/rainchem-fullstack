import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import client from "../../api/client";
import ConfirmDialog from "../../components/ConfirmDialog";
import { useAdminAuth } from "../../context/AdminAuthContext";
import { useToast } from "../../context/ToastContext";
import { formatDate } from "../../utils/format";

const TABS = [["all", "All"], ["unanswered", "Unanswered"], ["resolved", "Resolved"]];

function badge(log) {
  if (log.adminResolved) return { text: "Marked resolved", cls: "req-approved" };
  if (log.resolved) return { text: "Resolved by AI", cls: "req-approved" };
  return { text: "Unanswered", cls: "req-pending" };
}

function ReviewDialog({ logId, canLiveChat, onClose, onResolve }) {
  const [data, setData] = useState(null);
  useEffect(() => {
    client.get(`/api/admin/chat-monitor/${logId}`).then((res) => setData(res.data)).catch(() => setData({ error: true }));
  }, [logId]);

  return (
    <div className="overlay" onClick={onClose}>
      <div className="modal wide" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h3 style={{ margin: 0 }}>Review question</h3>
          <button type="button" className="modal-close" onClick={onClose}>&times;</button>
        </div>
        <div className="modal-body">
          {!data ? <p className="field-hint">Loading...</p> : data.error ? <div className="alert alert-error">This record could not be loaded.</div> : (
            <>
              <p className="field-hint" style={{ marginTop: 0 }}>
                {data.log.user ? `Asked by ${data.log.user.name}` : "Asked by a guest"} on {formatDate(data.log.createdAt)}
                {" \u00b7 "}match confidence {data.log.confidence}%
              </p>
              <div className="review-block"><span className="chat-label">Customer asked</span><p>{data.log.question}</p></div>
              <div className="review-block"><span className="chat-label ai">AI answered</span><p>{data.log.answer}</p></div>
              {data.matchedQuestion && <p className="field-hint">Matched knowledge base entry: {data.matchedQuestion}</p>}
              {data.log.handedOff && <div className="alert alert-info">The customer sent this to the live chat.</div>}

              <h4 className="pd-extra-head">Conversation around it</h4>
              {data.context.length === 0 ? <p className="field-hint">No other questions from this customer nearby.</p> : (
                <ul className="context-list">
                  {data.context.map((c) => (
                    <li key={c.id}><strong>{c.question}</strong><span>{c.answer}</span><time>{formatDate(c.createdAt)}</time></li>
                  ))}
                </ul>
              )}
              <div className="form-actions">
                {data.hasLiveChat && canLiveChat && data.log.user && <Link className="btn btn-outline" to="/admin/live-chat">Open live chat</Link>}
                <button type="button" className="btn btn-primary" onClick={() => onResolve(data.log)}>
                  {data.log.adminResolved ? "Reopen" : "Mark as resolved"}
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default function ChatMonitor() {
  const { can } = useAdminAuth();
  const showToast = useToast();
  const [data, setData] = useState(null);
  const [view, setView] = useState("all");
  const [search, setSearch] = useState("");
  const [reviewing, setReviewing] = useState(null);
  const [toDelete, setToDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);

  const load = useCallback(() => {
    client.get("/api/admin/chat-monitor", { params: { view, search: search || undefined } })
      .then((res) => setData(res.data))
      .catch(() => setData({ logs: [], stats: { total: 0, resolved: 0, unresolved: 0, unanswered: 0, adminResolved: 0, handedOff: 0, averageConfidence: 0 } }));
  }, [view, search]);
  useEffect(() => { load(); }, [load]);

  async function setResolved(log, resolved) {
    try {
      await client.post(`/api/admin/chat-monitor/${log.id}/resolve`, { resolved });
      showToast(resolved ? "Marked as resolved" : "Reopened", "success");
      setReviewing(null);
      load();
    } catch (err) {
      showToast(err.response?.data?.error || "Could not update this record", "error");
    }
  }

  async function confirmDelete() {
    setDeleting(true);
    try {
      await client.delete(`/api/admin/chat-monitor/${toDelete.id}`);
      showToast("Record deleted", "success");
      setToDelete(null);
      load();
    } catch (err) {
      showToast(err.response?.data?.error || "Could not delete this record", "error");
      setToDelete(null);
    } finally {
      setDeleting(false);
    }
  }

  if (!data) return null;
  const { logs, stats } = data;

  return (
    <div>
      <div className="admin-topbar"><div><h1>Chat Monitor</h1><p>Review what the AI assistant answered, and the questions it could not answer well.</p></div></div>
      <div className="stat-grid">
        <div className="stat-box"><div className="label">Total Conversations</div><div className="value">{stats.total}</div></div>
        <div className="stat-box"><div className="label">Resolved by AI</div><div className="value">{stats.resolved}</div><div className="delta">{stats.total ? Math.round((stats.resolved / stats.total) * 100) : 0}% resolution rate</div></div>
        <div className="stat-box"><div className="label">Unanswered</div><div className="value">{stats.unanswered}</div><div className="delta muted">{stats.adminResolved} marked resolved by an admin</div></div>
        <div className="stat-box"><div className="label">Sent to live chat</div><div className="value">{stats.handedOff}</div></div>
        <div className="stat-box"><div className="label">Avg. Confidence</div><div className="value">{stats.averageConfidence}%</div></div>
      </div>
      <div className="admin-panel">
        <div className="panel-head">
          <div><h3 style={{ margin: 0 }}>Recent Conversations</h3><p style={{ margin: "2px 0 0", fontSize: 12.5, color: "var(--soft)" }}>Newest first</p></div>
          <div className="tab-bar" style={{ border: "none", margin: 0 }}>
            {TABS.map(([key, label]) => (
              <button key={key} className={`tab-btn ${view === key ? "active" : ""}`} onClick={() => setView(key)}>{label}</button>
            ))}
          </div>
        </div>
        <div className="field">
          <input type="search" aria-label="Search questions" placeholder="Search questions..." value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        {logs.length === 0 ? (
          <p style={{ color: "var(--soft)" }}>{search ? "No questions match." : "Nothing here yet. Once users chat on the storefront, their questions appear here."}</p>
        ) : (
          logs.map((log) => {
            const b = badge(log);
            return (
              <div className="monitor-row" key={log.id}>
                <div className="monitor-q"><span className={`status-pill ${b.cls}`}>{b.text}</span> {log.handedOff && <span className="status-pill req-cancelled">Sent to live chat</span>} {log.question}</div>
                <div className="monitor-a">{log.answer}</div>
                <div className="monitor-meta">
                  <span>{formatDate(log.createdAt)}</span>
                  <span>{log.user ? log.user.name : "Guest"}</span>
                  <span>Confidence: {log.confidence}%</span>
                </div>
                <div className="row-actions">
                  <button type="button" className="icon-action wide" onClick={() => setReviewing(log.id)}>Review</button>
                  <button type="button" className="icon-action wide" onClick={() => setResolved(log, !log.adminResolved)}>{log.adminResolved ? "Reopen" : "Mark resolved"}</button>
                  <button type="button" className="icon-action wide" onClick={() => setToDelete(log)}>Delete</button>
                </div>
              </div>
            );
          })
        )}
      </div>

      {reviewing && <ReviewDialog logId={reviewing} canLiveChat={can("livechat")} onClose={() => setReviewing(null)} onResolve={(log) => setResolved(log, !log.adminResolved)} />}
      {toDelete && (
        <ConfirmDialog
          title="Delete this record?" busy={deleting} confirmLabel="Delete record"
          message={`“${toDelete.question.slice(0, 120)}” will be removed from the monitor. The customer's chat history, orders and the knowledge base are not affected. This cannot be undone.`}
          onCancel={() => setToDelete(null)} onConfirm={confirmDelete}
        />
      )}
    </div>
  );
}
