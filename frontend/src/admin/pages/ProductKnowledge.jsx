import { useEffect, useState } from "react";
import client from "../../api/client";
import RecommendationCards from "../../components/chat/RecommendationCards";
import ConfirmDialog from "../../components/ConfirmDialog";
import { useAdminAuth } from "../../context/AdminAuthContext";
import { useToast } from "../../context/ToastContext";
import { formatDate } from "../../utils/format";

const FACT_FIELDS = [
  ["viscosity_grades", "Viscosity grades", "10W-40, 20W-50"], ["standards", "Standards and specifications", "API SN, JASO MA2"],
  ["applications", "Applications", "engine oil, 4-stroke motorcycle engines"], ["equipment", "Equipment or vehicles", "motorcycle, scooter"],
  ["engine_types", "Engine types", "4-stroke, gasoline"], ["compatible_with", "Compatible with", "wet clutch"],
  ["not_for", "Not for (documented exclusions)", "2-stroke, diesel"], ["warnings", "Warnings to show customers", "Do not mix with 2-stroke oil"],
];
const EMPTY = { productId: "", title: "", docType: "technical_data_sheet", version: "", source: "", content: "", facts: {} };

function Tester() {
  const [text, setText] = useState("");
  const [context, setContext] = useState(null);
  const [reply, setReply] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function run(e) {
    e.preventDefault();
    if (!text.trim()) return;
    setBusy(true);
    setError("");
    try {
      const res = await client.post("/api/admin/product-docs/test", { message: text, context });
      setReply(res.data);
      setContext(res.data.context);
      setText("");
    } catch (err) {
      setError(err.response?.data?.error || "The test could not run.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="admin-panel">
      <h3>Try the assistant</h3>
      <p className="field-hint" style={{ marginTop: 0 }}>See exactly what customers would be told, using only verified documents. Nothing is saved.</p>
      {error && <div className="alert alert-error">{error}</div>}
      <form className="tester-form" onSubmit={run}>
        <input aria-label="Customer message" value={text} maxLength={500} onChange={(e) => setText(e.target.value)} placeholder="e.g. Recommend engine oil for my 4-stroke motorcycle" />
        <button type="submit" className="btn btn-primary" disabled={busy || !text.trim()}>{busy ? "Working..." : "Ask"}</button>
        <button type="button" className="btn btn-outline" onClick={() => { setReply(null); setContext(null); }}>Start over</button>
      </form>
      {reply && (
        <div className="review-block">
          <span className="chat-label ai">Assistant ({reply.status.replace("_", " ")})</span>
          <p>{reply.answer}</p>
          <RecommendationCards recommendation={reply} />
        </div>
      )}
    </div>
  );
}

export default function ProductKnowledge() {
  const { admin } = useAdminAuth();
  const showToast = useToast();
  const [data, setData] = useState(null);
  const [state, setState] = useState("");
  const [editing, setEditing] = useState(null); // a document, or "new"
  const [form, setForm] = useState(EMPTY);
  const [factText, setFactText] = useState({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [toDelete, setToDelete] = useState(null);
  const [stats, setStats] = useState(null);

  function load() {
    client.get("/api/admin/product-docs", { params: state ? { state } : {} }).then((res) => setData(res.data));
    client.get("/api/admin/product-docs/stats").then((res) => setStats(res.data)).catch(() => {});
  }
  useEffect(load, [state]);

  async function openForm(doc) {
    setError("");
    if (!doc) {
      setEditing("new");
      setForm(EMPTY);
      setFactText({});
      return;
    }
    const full = (await client.get(`/api/admin/product-docs/${doc.id}`)).data.document;
    setEditing(full);
    setForm({ productId: full.productId || "", title: full.title, docType: full.docType, version: full.version || "", source: full.source || "", content: full.content });
    setFactText(Object.fromEntries(Object.entries(full.facts || {}).map(([k, v]) => [k, v.join(", ")])));
  }

  async function save(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const payload = { ...form, productId: Number(form.productId), facts: factText };
    try {
      if (editing === "new") await client.post("/api/admin/product-docs", payload);
      else await client.put(`/api/admin/product-docs/${editing.id}`, payload);
      showToast(editing === "new" ? "Document saved. It must be verified before the assistant can use it." : "Saved. Verification was withdrawn; verify it again.", "success");
      setEditing(null);
      load();
    } catch (err) {
      setError(err.response?.data?.error || "The document could not be saved.");
    } finally {
      setBusy(false);
    }
  }

  async function act(promise, message) {
    try {
      await promise;
      showToast(message, "success");
      load();
    } catch (err) {
      showToast(err.response?.data?.error || "That did not work", "error");
    }
  }

  async function fromListing(productId) {
    if (!productId) return;
    await act(client.post("/api/admin/product-docs/from-listing", { productId: Number(productId) }), "Draft created from the product listing. Review it, then verify it.");
  }

  async function confirmDelete() {
    await act(client.delete(`/api/admin/product-docs/${toDelete.id}`), "Document deleted");
    setToDelete(null);
  }

  return (
    <div>
      <div className="admin-topbar">
        <div><h1>Product Knowledge</h1><p>The documents the AI assistant may use to recommend products. Only documents a Head Admin has verified and authorised are used.</p></div>
        <button type="button" className="btn btn-primary" onClick={() => openForm(null)}>+ Add document</button>
      </div>

      {stats && (
        <div className="sheet-totals">
          <span><strong>{stats.usableDocuments}</strong> in use</span><span><strong>{stats.allDocuments - stats.usableDocuments}</strong> not in use</span>
          <span><strong>{stats.total}</strong> recommendations given</span>{stats.total > 0 && <span>Average {stats.averageMs} ms</span>}
        </div>
      )}

      <Tester />

      <div className="admin-panel">
        <div className="panel-head">
          <div className="tab-bar" style={{ border: "none", margin: 0 }}>
            {[["", "All"], ["usable", "In use"], ["unverified", "Not verified"]].map(([key, label]) => (
              <button key={key} type="button" className={`tab-btn ${state === key ? "active" : ""}`} onClick={() => setState(key)}>{label}</button>
            ))}
          </div>
          <select aria-label="Create a draft from a product listing" defaultValue="" onChange={(e) => { fromListing(e.target.value); e.target.value = ""; }}>
            <option value="">Create a draft from a product listing...</option>
            {data?.products.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </div>
        <div className="table-wrap">
          <table className="admin-table stack">
            <thead><tr><th>Document</th><th>Product</th><th>Type</th><th>Version</th><th>Status</th><th></th></tr></thead>
            <tbody>
              {!data ? <tr><td colSpan={6}>Loading...</td></tr> : data.documents.length === 0 ? (
                <tr><td colSpan={6}>No documents yet. Add a technical data sheet or manufacturer recommendation. Until a verified document exists, the assistant will refer product questions to a person.</td></tr>
              ) : data.documents.map((d) => (
                <tr key={d.id}>
                  <td data-label="Document" className="cell-name">{d.title}{d.source && <div className="muted">{d.source}</div>}</td>
                  <td data-label="Product">{d.productName || "-"}</td><td data-label="Type">{d.docTypeLabel}</td><td data-label="Version">{d.version || "-"}</td>
                  <td data-label="Status">
                    {d.usable ? <span className="status-pill req-approved">In use</span> : d.verified ? <span className="status-pill req-pending">Verified, not authorised</span> : <span className="status-pill req-cancelled">Not verified</span>}
                    {d.verifiedBy && <div className="muted">{d.verifiedBy}, {formatDate(d.verifiedAt)}</div>}
                  </td>
                  <td data-label="" className="row-cell"><div className="row-actions">
                    <button type="button" className="icon-action wide" onClick={() => openForm(d)}>Edit</button>
                    {admin?.isHead && !d.usable && <button type="button" className="icon-action wide" onClick={() => act(client.post(`/api/admin/product-docs/${d.id}/verify`, {}), "Verified and authorised for the assistant")}>Verify and authorise</button>}
                    {admin?.isHead && d.verified && <button type="button" className="icon-action wide" onClick={() => act(client.post(`/api/admin/product-docs/${d.id}/unverify`, {}), "Withdrawn from the assistant")}>Withdraw</button>}
                    <button type="button" className="icon-action wide" onClick={() => setToDelete(d)}>Delete</button>
                  </div></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {editing && (
        <div className="overlay" onClick={() => setEditing(null)}>
          <div className="modal wide" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head"><h3 style={{ margin: 0 }}>{editing === "new" ? "Add document" : "Edit document"}</h3><button type="button" className="modal-close" onClick={() => setEditing(null)}>&times;</button></div>
            <form className="modal-body" onSubmit={save}>
              {error && <div className="alert alert-error" role="alert">{error}</div>}
              {editing !== "new" && editing.usable && <div className="alert alert-info">Saving changes withdraws the verification. A Head Admin must verify the document again.</div>}
              <div className="field-row">
                <div className="field"><label htmlFor="pk-product">Product</label>
                  <select id="pk-product" required value={form.productId} onChange={(e) => setForm({ ...form, productId: e.target.value })}>
                    <option value="">Choose a product</option>{data?.products.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                  </select></div>
                <div className="field"><label htmlFor="pk-type">Document type</label>
                  <select id="pk-type" value={form.docType} onChange={(e) => setForm({ ...form, docType: e.target.value })}>
                    {data?.types.map((t) => <option key={t.key} value={t.key}>{t.label}</option>)}
                  </select></div>
              </div>
              <div className="field"><label htmlFor="pk-title">Title</label><input id="pk-title" required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></div>
              <div className="field-row">
                <div className="field"><label htmlFor="pk-version">Version or date</label><input id="pk-version" value={form.version} onChange={(e) => setForm({ ...form, version: e.target.value })} placeholder="e.g. 2024-03" /></div>
                <div className="field"><label htmlFor="pk-source">Source</label><input id="pk-source" value={form.source} onChange={(e) => setForm({ ...form, source: e.target.value })} placeholder="File name or manufacturer reference" /></div>
              </div>
              <div className="field"><label htmlFor="pk-content">Document text</label><textarea id="pk-content" rows={8} required value={form.content} onChange={(e) => setForm({ ...form, content: e.target.value })} /></div>
              <p className="field-hint">Specifications used for matching. Separate values with commas. Copy them exactly from the document.</p>
              {FACT_FIELDS.map(([key, label, example]) => (
                <div className="field" key={key}><label htmlFor={`fact-${key}`}>{label}</label>
                  <input id={`fact-${key}`} value={factText[key] || ""} placeholder={example} onChange={(e) => setFactText({ ...factText, [key]: e.target.value })} /></div>
              ))}
              <div className="form-actions">
                <button type="button" className="btn btn-outline" onClick={() => setEditing(null)}>Cancel</button>
                <button type="submit" className="btn btn-primary" disabled={busy}>{busy ? "Saving..." : "Save document"}</button>
              </div>
            </form>
          </div>
        </div>
      )}
      {toDelete && <ConfirmDialog title="Delete this document?" confirmLabel="Delete document" message={`“${toDelete.title}” will be removed and the assistant will stop using it. A record of the deletion is kept in the audit log.`} onCancel={() => setToDelete(null)} onConfirm={confirmDelete} />}
    </div>
  );
}
