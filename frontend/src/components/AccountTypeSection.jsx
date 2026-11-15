import { useState } from "react";
import client from "../api/client";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";

/** Personal or Business. A business can order in bulk. The TIN is optional and never required. */
export default function AccountTypeSection() {
  const { user, setUser } = useAuth();
  const showToast = useToast();
  const [form, setForm] = useState({
    accountType: user?.accountType || "personal",
    businessName: user?.businessName || "",
    tin: user?.tin || "",
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function save(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const res = await client.put("/api/auth/me/account-type", form);
      setUser(res.data.user);
      showToast("Account type saved", "success");
    } catch (err) {
      setError(err.response?.data?.error || "Could not save. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  if (user?.accountTypeChosen) {
    return (
      <div className="panel" style={{ maxWidth: 520, marginBottom: 20 }}>
        <h3 style={{ marginTop: 0 }}>Account type</h3>
        <p><strong>{user.accountType === "business" ? `Business: ${user.businessName || ""}` : "Personal"}</strong></p>
        <p className="field-hint">This was set when the account was created. To change it, contact the store.</p>
      </div>
    );
  }

  return (
    <div className="panel" style={{ maxWidth: 520, marginBottom: 20 }}>
      <h3 style={{ marginTop: 0 }}>Account type</h3>
      <p className="field-hint">Business accounts can place bulk orders. A TIN is optional.</p>
      {error && <div className="alert alert-error" role="alert">{error}</div>}
      <form onSubmit={save}>
        <div className="field">
          <label htmlFor="acct-type">Account type</label>
          <select id="acct-type" value={form.accountType} onChange={(e) => setForm({ ...form, accountType: e.target.value })}>
            <option value="personal">Personal</option>
            <option value="business">Business (company or shop)</option>
          </select>
        </div>
        {form.accountType === "business" && (
          <>
            <div className="field">
              <label htmlFor="acct-biz">Business name</label>
              <input id="acct-biz" required value={form.businessName} onChange={(e) => setForm({ ...form, businessName: e.target.value })} />
            </div>
            <div className="field">
              <label htmlFor="acct-tin">TIN (optional)</label>
              <input id="acct-tin" value={form.tin} onChange={(e) => setForm({ ...form, tin: e.target.value })} />
            </div>
          </>
        )}
        <button type="submit" className="btn btn-primary" disabled={busy}>{busy ? "Saving..." : "Save account type"}</button>
      </form>
    </div>
  );
}
