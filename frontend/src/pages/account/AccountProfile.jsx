import { useState } from "react";
import client from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import { useToast } from "../../context/ToastContext";
import { resizeImage } from "../../utils/imageResize";

export default function AccountProfile() {
  async function handleAvatarChange(e) {
  const file = e.target.files[0];
  if (!file) return;
  const dataUrl = await resizeImage(file, 300);
  try {
    const res = await client.put("/api/auth/me/avatar", { avatarPhoto: dataUrl });
    setUser(res.data.user);
    showToast("Profile photo updated", "success");
  } catch {
    showToast("Could not update photo", "error");
  }
}
  const { user, setUser } = useAuth();
  const showToast = useToast();

  const [form, setForm] = useState({
    name: user?.name || "",
    phone: user?.phone || "",
    age: user?.age || "",
    gender: user?.gender || "",
    
  });
  const [saving, setSaving] = useState(false);

  const [newEmail, setNewEmail] = useState("");
  const [emailStep, setEmailStep] = useState("idle"); // idle | code
  const [emailCode, setEmailCode] = useState("");

  async function handleSaveProfile(e) {
    e.preventDefault();
    setSaving(true);
    try {
      const res = await client.put("/api/auth/me/profile", form);
      setUser(res.data.user);
      showToast("Profile updated", "success");
    } catch (err) {
      showToast(err.response?.data?.error || "Could not update profile", "error");
    } finally {
      setSaving(false);
    }
  }

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

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 20 }}>
  <div style={{ width: 72, height: 72, borderRadius: "50%", overflow: "hidden", background: "var(--fog)", border: "1px solid rgba(24,20,15,.12)" }}>
    {user?.avatarPhoto && <img src={user.avatarPhoto} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} />}
  </div>
  <div>
    <input type="file" accept="image/*" onChange={handleAvatarChange} />
    <div className="field-hint">JPG or PNG, resized automatically.</div>
  </div>
</div>
      <h2>Profile</h2>

      <div className="panel" style={{ maxWidth: 520, marginBottom: 20 }}>
        <form onSubmit={handleSaveProfile}>
          <div className="field">
            <label>Full Name</label>
            <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </div>
          <div className="field">
            <label>Phone</label>
            <input required value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
          </div>
          <div className="field-row">
            <div className="field">
              <label>Age</label>
              <input type="number" min="1" max="120" value={form.age} onChange={(e) => setForm({ ...form, age: e.target.value })} />
            </div>
            <div className="field">
              <label>Gender</label>
              <select value={form.gender} onChange={(e) => setForm({ ...form, gender: e.target.value })}>
                <option value="">Prefer not to say</option>
                <option value="Male">Male</option>
                <option value="Female">Female</option>
                <option value="Other">Other</option>
              </select>
            </div>
          </div>
          {user?.verified && <span className="badge" style={{ marginBottom: 14, display: "inline-block" }}>Verified Account</span>}
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? "Saving..." : "Save Changes"}
          </button>
        </form>
      </div>

      <div className="panel" style={{ maxWidth: 520 }}>
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
    </div>
  );
}