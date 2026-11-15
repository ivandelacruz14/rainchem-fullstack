import { useState } from "react";
import client from "../api/client";

/** The store changes a customer's account type. A reason is required; the change is recorded in the audit log. */
export default function AccountTypeDialog({ user, onClose, onSaved }) {
  const [form, setForm] = useState({
    accountType: user.accountType === "business" ? "business" : "personal",
    businessName: user.businessName || "",
    reason: "",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function save(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const res = await client.put(`/api/admin/users/${user.id}/account-type`, form);
      onSaved(res.data.user);
    } catch (err) {
      setError(err.response?.data?.error || "Could not change the account type.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 460 }}>
        <div className="modal-head">
          <h3 style={{ margin: 0 }}>Change account type</h3>
          <button type="button" className="modal-close" onClick={onClose}>&times;</button>
        </div>
        <div className="modal-body">
          <p className="field-hint" style={{ marginTop: 0 }}>{user.name} ({user.email}). Customers cannot change this themselves.</p>
          {error && <div className="alert alert-error" role="alert">{error}</div>}
          <form onSubmit={save}>
            <div className="field">
              <label htmlFor="at-type">Account type</label>
              <select id="at-type" value={form.accountType} onChange={(e) => setForm({ ...form, accountType: e.target.value })}>
                <option value="personal">Personal</option>
                <option value="business">Business</option>
              </select>
            </div>
            {form.accountType === "business" && (
              <div className="field">
                <label htmlFor="at-biz">Business name</label>
                <input id="at-biz" required value={form.businessName} onChange={(e) => setForm({ ...form, businessName: e.target.value })} />
              </div>
            )}
            <div className="field">
              <label htmlFor="at-reason">Reason (required)</label>
              <input id="at-reason" required value={form.reason} maxLength={500} onChange={(e) => setForm({ ...form, reason: e.target.value })} />
            </div>
            <div className="form-actions">
              <button type="button" className="btn btn-outline" onClick={onClose} disabled={busy}>Cancel</button>
              <button type="submit" className="btn btn-primary" disabled={busy || !form.reason.trim()}>{busy ? "Saving..." : "Save"}</button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
