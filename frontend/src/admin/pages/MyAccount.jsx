import { useState } from "react";
import client from "../../api/client";
import PasswordInput from "../../components/PasswordInput";
import { useAdminAuth } from "../../context/AdminAuthContext";
import { useToast } from "../../context/ToastContext";
import { validatePassword } from "../../utils/format";

function errorText(err) {
  return err.response?.data?.error || "That did not work. Please try again.";
}

function EmailSection({ admin, onChanged }) {
  const showToast = useToast();
  const [step, setStep] = useState("form");
  const [newEmail, setNewEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function send(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await client.post("/api/admin/auth/me/email/start", { password, newEmail });
      setPassword("");
      setCode("");
      setStep("code");
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  async function confirm(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const res = await client.post("/api/admin/auth/me/email/confirm", { code });
      onChanged(res.data.admin);
      showToast("Email updated", "success");
      setStep("form");
      setNewEmail("");
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="admin-panel">
      <h3>Email</h3>
      <p className="field-hint" style={{ marginTop: 0 }}>
        This is your login and where approval codes are sent. Current email: <strong>{admin.email}</strong>
      </p>
      {error && <div className="alert alert-error">{error}</div>}

      {step === "form" ? (
        <form onSubmit={send}>
          <div className="field"><label htmlFor="new-email">New email</label><input id="new-email" type="email" required value={newEmail} onChange={(e) => setNewEmail(e.target.value)} /></div>
          <div className="field"><label>Your password</label><PasswordInput value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" /></div>
          <button type="submit" className="btn btn-primary" disabled={busy || !newEmail || !password}>{busy ? "Sending..." : "Send code to new email"}</button>
        </form>
      ) : (
        <form onSubmit={confirm}>
          <p>We sent a 6-digit code to <strong>{newEmail}</strong>. It lasts 10 minutes. Your email changes only after you enter it.</p>
          <div className="field">
            <label htmlFor="email-code">Code</label>
            <input id="email-code" className="otp-input" inputMode="numeric" autoComplete="one-time-code" maxLength={6} value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))} placeholder="123456" />
          </div>
          <div className="form-actions" style={{ justifyContent: "flex-start" }}>
            <button type="button" className="btn btn-outline" onClick={() => { setStep("form"); setError(""); }}>Use a different email</button>
            <button type="submit" className="btn btn-primary" disabled={busy || code.length !== 6}>{busy ? "Checking..." : "Confirm email"}</button>
          </div>
        </form>
      )}
    </div>
  );
}

function PasswordSection() {
  const showToast = useToast();
  const [form, setForm] = useState({ currentPassword: "", newPassword: "", confirm: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setError("");
    if (form.newPassword !== form.confirm) {
      setError("The two new passwords do not match.");
      return;
    }
    const problems = validatePassword(form.newPassword);
    if (problems.length) {
      setError("Password requirements not met: " + problems.join(", "));
      return;
    }
    setBusy(true);
    try {
      await client.put("/api/admin/auth/me/password", { currentPassword: form.currentPassword, newPassword: form.newPassword });
      showToast("Password updated", "success");
      setForm({ currentPassword: "", newPassword: "", confirm: "" });
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="admin-panel">
      <h3>Password</h3>
      {error && <div className="alert alert-error">{error}</div>}
      <form onSubmit={submit}>
        <div className="field"><label>Current password</label><PasswordInput value={form.currentPassword} onChange={(e) => setForm({ ...form, currentPassword: e.target.value })} autoComplete="current-password" /></div>
        <div className="field"><label>New password</label><PasswordInput value={form.newPassword} onChange={(e) => setForm({ ...form, newPassword: e.target.value })} autoComplete="new-password" /><p className="field-hint">8-24 characters with an uppercase letter, a lowercase letter, a number and a symbol.</p></div>
        <div className="field"><label>Confirm new password</label><PasswordInput value={form.confirm} onChange={(e) => setForm({ ...form, confirm: e.target.value })} autoComplete="new-password" /></div>
        <button type="submit" className="btn btn-primary" disabled={busy || !form.currentPassword || !form.newPassword}>{busy ? "Saving..." : "Update password"}</button>
      </form>
    </div>
  );
}

export default function MyAccount() {
  const { admin, setAdmin } = useAdminAuth();
  if (!admin) return null;
  return (
    <div>
      <div className="admin-topbar">
        <div>
          <h1>My Account</h1>
          <p>{admin.name} &middot; {admin.role}</p>
        </div>
      </div>
      <EmailSection admin={admin} onChanged={setAdmin} />
      <PasswordSection />
    </div>
  );
}
