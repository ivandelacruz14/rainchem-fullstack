import { useState } from "react";
import client from "../api/client";
import { useAuth } from "../context/AuthContext";

/**
 * Shown over every page until a signed-in person has chosen Personal or Business and given a phone number.
 * Google sign-ups and older accounts see it. It cannot be closed; only signing out gets past it.
 */
export default function OnboardingGate() {
  const { user, setUser, logout } = useAuth();
  const [form, setForm] = useState({ accountType: "personal", businessName: "", tin: "", phone: user?.phone || "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (!user || user.accountTypeChosen !== false) return null;

  async function save(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const res = await client.put("/api/auth/me/account-type", form);
      setUser(res.data.user);
    } catch (err) {
      setError(err.response?.data?.error || "Could not save. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="overlay" role="dialog" aria-modal="true" aria-label="Tell us about your account" style={{ zIndex: 3000 }}>
      <div className="modal" style={{ maxWidth: 480 }}>
        <div className="modal-head">
          <h3 style={{ margin: 0 }}>Tell us about your account</h3>
        </div>
        <div className="modal-body">
          <p className="field-hint" style={{ marginTop: 0 }}>
            Choose once. Personal and business accounts have different order limits, and the choice cannot be changed by you later.
          </p>
          {error && <div className="alert alert-error" role="alert">{error}</div>}
          <form onSubmit={save}>
            <div className="field">
              <label htmlFor="ob-type">Account type</label>
              <select id="ob-type" value={form.accountType} onChange={(e) => setForm({ ...form, accountType: e.target.value })}>
                <option value="personal">Personal</option>
                <option value="business">Business (company or shop)</option>
              </select>
            </div>
            {form.accountType === "business" && (
              <>
                <div className="field">
                  <label htmlFor="ob-biz">Business name</label>
                  <input id="ob-biz" required value={form.businessName} onChange={(e) => setForm({ ...form, businessName: e.target.value })} />
                </div>
                <div className="field">
                  <label htmlFor="ob-tin">TIN (optional)</label>
                  <input id="ob-tin" value={form.tin} onChange={(e) => setForm({ ...form, tin: e.target.value })} />
                </div>
              </>
            )}
            <div className="field">
              <label htmlFor="ob-phone">Contact number</label>
              <input id="ob-phone" required placeholder="09xx xxx xxxx" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
            </div>
            <div className="form-actions">
              <button type="button" className="btn btn-outline" onClick={logout} disabled={busy}>Sign out</button>
              <button type="submit" className="btn btn-primary" disabled={busy}>{busy ? "Saving..." : "Continue"}</button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
