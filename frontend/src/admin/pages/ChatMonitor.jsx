import { useState, useEffect } from "react";
import client from "../../api/client";
import { formatDate } from "../../utils/format";

const TABS = ["All", "Resolved", "Unresolved"];

export default function ChatMonitor() {
  const [data, setData] = useState(null);
  const [tab, setTab] = useState("All");

  useEffect(() => {
    const resolved = tab === "Resolved" ? "true" : tab === "Unresolved" ? "false" : undefined;
    client.get("/api/admin/chat-monitor", { params: { resolved } }).then((res) => setData(res.data));
  }, [tab]);

  if (!data) return null;
  const { logs, stats } = data;

  return (
    <div>
      <div className="admin-topbar"><div><h1>Chat Monitor</h1><p>Review live questions and answers the chatbot has given to users.</p></div></div>
      <div className="stat-grid">
        <div className="stat-box"><div className="label">Total Conversations</div><div className="value">{stats.total}</div></div>
        <div className="stat-box"><div className="label">Resolved by AI</div><div className="value">{stats.resolved}</div><div className="delta">{stats.total ? Math.round((stats.resolved / stats.total) * 100) : 0}% resolution rate</div></div>
        <div className="stat-box"><div className="label">Unresolved / Fallback</div><div className="value">{stats.unresolved}</div></div>
        <div className="stat-box"><div className="label">Avg. Confidence</div><div className="value">{stats.averageConfidence}%</div></div>
      </div>
      <div className="admin-panel">
        <div className="panel-head">
          <div><h3 style={{ margin: 0 }}>Recent Conversations</h3><p style={{ margin: "2px 0 0", fontSize: 12.5, color: "#8a8580" }}>Newest first</p></div>
          <div className="tab-bar" style={{ border: "none", margin: 0 }}>
            {TABS.map((t) => (
              <button key={t} className={`tab-btn ${tab === t ? "active" : ""}`} onClick={() => setTab(t)}>{t}</button>
            ))}
          </div>
        </div>
        {logs.length === 0 ? (
          <p style={{ color: "#8a8580" }}>No conversations yet, once users chat on the storefront, they'll appear here.</p>
        ) : (
          logs.map((log) => (
            <div className="monitor-row" key={log.id}>
              <div className="monitor-q">{log.resolved ? "Resolved" : "Unresolved"} - {log.question}</div>
              <div className="monitor-a">{log.answer}</div>
              <div className="monitor-meta">
                <span>{formatDate(log.createdAt)}</span>
                <span>User: {log.userId ?? "guest"}</span>
                <span>Confidence: {log.confidence}%</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
