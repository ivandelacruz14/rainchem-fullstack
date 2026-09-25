import { useState } from "react";
import client from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import { useTheme } from "../../context/ThemeContext";
import { useToast } from "../../context/ToastContext";

export default function AccountSettings() {
  const { user, setUser } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const showToast = useToast();

  const [newEmail, setNewEmail] = useState("");
  const [emailStep, setEmailStep] = useState("idle");
  const [emailCode, setEmailCode] = useState("");

  const [pwForm, setPwForm] = useState({ currentPassword: "", newPassword: "", confirm: "" });

  async function handleRequestEmailChange(e) {
    e.preventDefault();
    try {
      await client.post("/api/auth/me/email/request-change", { newEmail });
      showToast("Confirmation code sent to your new email", "success");
      setEmailStep("code");
    } catch (err) {
      showToast(err.response?.data?.error || "Could not send code", "error");
    }
  }

  async function handleConfirmEmailChange(e) {
    e.preventDefault();
    try {
      const res = await client.post("/api/auth/me/email/confirm-change", { code: emailCode });
      setUser(res.data.user);
      showToast("Email address updated", "success");
      setEmailStep("idle");
      setNewEmail("");
      setEmailCode("");
    } catch (err) {
      showToast(err.response?.data?.error || "Incorrect or expired code", "error");
    }
  }

  async function handleChangePassword(e) {
    e.preventDefault();
    if (pwForm.newPassword !== pwForm.confirm) {
      showToast("New passwords do not match", "error");
      return;
    }
    try {
      await client.put("/api/auth/me/password", {
        currentPassword: pwForm.currentPassword,
        newPassword: pwForm.newPassword,
      });
      showToast("Password updated", "success");
      setPwForm({ currentPassword: "", newPassword: "", confirm: "" });
    } catch (err) {
      showToast(err.response?.data?.error || "Could not update password", "error");
    }
  }

  return (
    <div>
      <h2>Settings &amp; Privacy</h2>

      <div className="panel" style={{ maxWidth: 520, marginBottom: 20 }}>
        <h3 style={{ marginTop: 0 }}>Appearance</h3>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span>Dark Mode</span>
          <button type="button" className="btn btn-outline" onClick={toggleTheme}>
            {theme === "dark" ? "Switch to Light" : "Switch to Dark"}
          </button>
        </div>
      </div>

      <div className="panel" style={{ maxWidth: 520, marginBottom: 20 }}>
        <h3 style={{ marginTop: 0 }}>Email Address</h3>
        <p style={{ fontSize: 13.5, color: "#6b665f" }}>Current: <strong>{user?.email}</strong></p>
        {emailStep === "idle" ? (
          <form onSubmit={handleRequestEmailChange}>
            <div className="field">
              <label>New Email Address</label>
              <input required type="email" value={newEmail} onChange={(e) => setNewEmail(e.target.value)} />
            </div>
            <button type="submit" className="btn btn-outline">Send Confirmation Code</button>
          </form>
        ) : (
          <form onSubmit={handleConfirmEmailChange}>
            <div className="alert alert-info">Enter the code sent to <strong>{newEmail}</strong>.</div>
            <div className="field">
              <label>Confirmation Code</label>
              <input required maxLength={6} value={emailCode} onChange={(e) => setEmailCode(e.target.value)} />
            </div>
            <button type="submit" className="btn btn-primary">Confirm New Email</button>
            <button type="button" className="link-btn" style={{ marginLeft: 12 }} onClick={() => setEmailStep("idle")}>Cancel</button>
          </form>
        )}
      </div>

      <div className="panel" style={{ maxWidth: 520 }}>
        <h3 style={{ marginTop: 0 }}>Change Password</h3>
        <form onSubmit={handleChangePassword}>
          <div className="field">
            <label>Current Password</label>
            <input required type="password" value={pwForm.currentPassword} onChange={(e) => setPwForm({ ...pwForm, currentPassword: e.target.value })} />
          </div>
          <div className="field">
            <label>New Password</label>
            <input required type="password" value={pwForm.newPassword} onChange={(e) => setPwForm({ ...pwForm, newPassword: e.target.value })} />
          </div>
          <div className="field">
            <label>Confirm New Password</label>
            <input required type="password" value={pwForm.confirm} onChange={(e) => setPwForm({ ...pwForm, confirm: e.target.value })} />
          </div>
          <button type="submit" className="btn btn-primary">Update Password</button>
        </form>
      </div>
    </div>
  );
}