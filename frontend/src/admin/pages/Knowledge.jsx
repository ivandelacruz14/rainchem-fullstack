import { useState, useEffect } from "react";
import client from "../../api/client";
import { formatDate } from "../../utils/format";
import { useToast } from "../../context/ToastContext";

const CATEGORIES = ["Oil & Maintenance", "Coolant", "Orders & Shipping", "Services", "Brakes", "Maintenance", "General"];
const TABS = ["All", "Pending", "Approved"];

export default function Knowledge() {
  const [entries, setEntries] = useState([]);
  const [tab, setTab] = useState("All");
  const [form, setForm] = useState(null);
  const showToast = useToast();

  function load() {
    const status = tab === "All" ? undefined : tab;
    client.get("/api/admin/knowledge", { params: { status } }).then((res) => setEntries(res.data.entries));
  }
  useEffect(load, [tab]);

  function openAdd() {
    setForm({ question: "", answer: "", category: CATEGORIES[0], status: "pending" });
  }
  function openEdit(entry) {
    setForm({ id: entry.id, question: entry.question, answer: entry.answer, category: entry.category, status: entry.status });
  }

  async function handleSave(e) {
    e.preventDefault();
    if (form.id) {
      await client.put(`/api/admin/knowledge/${form.id}`, form);
      showToast("Knowledge entry updated", "success");
    } else {
      await client.post("/api/admin/knowledge", form);
      showToast(form.status === "approved" ? "Knowledge added and live to users" : "Knowledge added as pending", "success");
    }
    setForm(null);
    load();
  }

  async function handleApprove(id) {
    await client.post(`/api/admin/knowledge/${id}/approve`);
    showToast("Knowledge approved, now live to the AI assistant", "success");
    load();
  }

  async function handleDelete(id) {
    if (!window.confirm("Delete this knowledge entry?")) return;
    await client.delete(`/api/admin/knowledge/${id}`);
    showToast("Knowledge entry deleted", "error");
    load();
  }

  const pendingCount = entries.filter((e) => e.status === "pending").length;
  const ranked = [...entries].filter((e) => e.status === "approved").sort((a, b) => b.hits - a.hits).slice(0, 8);
  const maxHits = Math.max(1, ...ranked.map((e) => e.hits));

  return (
    <div>
      <div className="admin-topbar">
        <div><h1>AI Knowledge Base</h1><p>Add and approve Q&amp;A pairs that power the chatbot's answers.</p></div>
        <button className="btn btn-primary" onClick={openAdd}>+ Add Knowledge</button>
      </div>
      <div className="two-col">
        <div>
          <div className="tab-bar">
            {TABS.map((t) => (
              <button key={t} className={`tab-btn ${tab === t ? "active" : ""}`} onClick={() => setTab(t)}>
                {t}{t === "Pending" ? ` (${pendingCount})` : ""}
              </button>
            ))}
          </div>
          {entries.map((entry) => (
            <div className="faq-item" key={entry.id}>
              <div className="faq-item-top">
                <div>
                  <div className="faq-q">{entry.question}</div>
                  <span className={`pill ${entry.status === "approved" ? "pill-approved" : "pill-pending"}`}>{entry.status}</span>
                  <span className="badge" style={{ marginLeft: 6 }}>{entry.category}</span>
                </div>
                <div className="row-actions">
                  {entry.status === "pending" && <button className="icon-action" onClick={() => handleApprove(entry.id)}>Approve</button>}
                  <button className="icon-action" onClick={() => openEdit(entry)}>Edit</button>
                  <button className="icon-action" onClick={() => handleDelete(entry.id)}>Delete</button>
                </div>
              </div>
              <p className="faq-a">{entry.answer}</p>
              <div className="faq-meta"><span>Asked {entry.hits} time{entry.hits === 1 ? "" : "s"}</span><span>Added {formatDate(entry.createdAt).split(",")[0]}</span></div>
            </div>
          ))}
        </div>
        <div className="admin-panel">
          <div className="panel-head"><div><h3 style={{ margin: 0 }}>Most Frequently Asked</h3><p style={{ margin: "2px 0 0", fontSize: 12.5, color: "#8a8580" }}>Ranked by how often users trigger this answer</p></div></div>
          {ranked.map((e) => (
            <div key={e.id} style={{ marginBottom: 14 }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12.5, fontWeight: 600 }}><span>{e.question}</span><span className="mono">{e.hits}</span></div>
              <div className="hit-bar-track"><div className="hit-bar-fill" style={{ width: `${(e.hits / maxHits) * 100}%` }} /></div>
            </div>
          ))}
        </div>
      </div>

      {form && (
        <div className="overlay" onClick={() => setForm(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head"><h3 style={{ margin: 0 }}>{form.id ? "Edit Knowledge" : "Add Knowledge"}</h3><button className="modal-close" onClick={() => setForm(null)}>&times;</button></div>
            <div className="modal-body">
              <form onSubmit={handleSave}>
                <div className="field"><label>Question</label><input required value={form.question} onChange={(e) => setForm({ ...form, question: e.target.value })} /></div>
                <div className="field"><label>Answer</label><textarea required rows="4" value={form.answer} onChange={(e) => setForm({ ...form, answer: e.target.value })} /></div>
                <div className="field-row">
                  <div className="field">
                    <label>Category</label>
                    <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
                      {CATEGORIES.map((c) => <option key={c}>{c}</option>)}
                    </select>
                  </div>
                  <div className="field">
                    <label>Status</label>
                    <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
                      <option value="pending">Pending Review</option>
                      <option value="approved">Approved (live to users)</option>
                    </select>
                  </div>
                </div>
                <div className="form-actions">
                  <button type="button" className="btn btn-outline" onClick={() => setForm(null)}>Cancel</button>
                  <button type="submit" className="btn btn-primary">{form.id ? "Save Changes" : "Add Knowledge"}</button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
