import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import client from "../api/client";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";

/** Privacy policy link and account deletion. Deleting removes personal details; order records are kept. */
export default function PrivacySection() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const showToast = useToast();
  const [open, setOpen] = useState(false);
  const [password, setPassword] = useState("");
  const [confirmText, setConfirmText] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function remove(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await client.delete("/api/auth/me/account", { data: { password, confirmText } });
      showToast("Your account has been deleted", "success");
      logout();
      navigate("/", { replace: true });
    } catch (err) {
      setError(err.response?.data?.error || "Your account could not be deleted. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="panel" style={{ maxWidth: 520, marginBottom: 20 }}>
      <h3 style={{ marginTop: 0 }}>Privacy</h3>
      <p>
        Read how we collect, use, and protect your personal data in our <Link to="/privacy">Privacy Policy</Link>.
      </p>

      <h3>Delete account</h3>
      <p className="field-hint">
        This erases your login, contact details, address, photo, and cart. Your order and receipt records are kept for
        accounting, as the Privacy Policy explains. This cannot be undone.
      </p>
      {!open ? (
        <button type="button" className="btn btn-outline" style={{ color: "var(--red-700)", borderColor: "var(--red-700)" }} onClick={() => setOpen(true)}>
          Delete my account
        </button>
      ) : (
        <form onSubmit={remove}>
          {error && <div className="alert alert-error" role="alert">{error}</div>}
          <div className="field">
            <label htmlFor="del-pass">Password (if you sign in with a password)</label>
            <input id="del-pass" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="del-confirm">Type DELETE (if you sign in with Google only)</label>
            <input id="del-confirm" value={confirmText} onChange={(e) => setConfirmText(e.target.value)} />
          </div>
          <div className="form-actions">
            <button type="button" className="btn btn-outline" onClick={() => setOpen(false)} disabled={busy}>Cancel</button>
            <button type="submit" className="btn btn-primary" style={{ background: "var(--red-700)" }} disabled={busy}>
              {busy ? "Deleting..." : "Permanently delete"}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
