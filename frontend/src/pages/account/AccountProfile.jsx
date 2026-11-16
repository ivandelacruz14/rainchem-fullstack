import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import client from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import { useToast } from "../../context/ToastContext";
import { resizeImage } from "../../utils/imageResize";
import AccountTypeSection from "../../components/AccountTypeSection";
import PasswordInput from "../../components/PasswordInput";

/** Split the stored full name when the separate name fields are not filled in yet (accounts made before them). */
function nameParts(user) {
  const parts = (user?.name || "").trim().split(/\s+/).filter(Boolean);
  return {
    firstName: user?.firstName || parts[0] || "",
    middleName: user?.middleName || (parts.length > 2 ? parts.slice(1, -1).join(" ") : ""),
    lastName: user?.lastName || (parts.length > 1 ? parts[parts.length - 1] : ""),
  };
}

export default function AccountProfile() {
  const { user, setUser } = useAuth();
  const showToast = useToast();
  const [form, setForm] = useState(() => ({
    ...nameParts(user),
    phone: user?.phone || "",
    age: user?.age || "",
    gender: user?.gender || "",
  }));
  const [saving, setSaving] = useState(false);
  const [address, setAddress] = useState(null);
  const [newEmail, setNewEmail] = useState("");
  const [emailStep, setEmailStep] = useState("idle");
  const [emailCode, setEmailCode] = useState("");

  useEffect(() => {
    let active = true;
    Promise.resolve()
      .then(() => client.get("/api/addresses"))
      .then((res) => {
        if (!active) return;
        const list = res.data.addresses || [];
        setAddress(list.find((a) => a.isDefault) || list[0] || null);
      })
      .catch(() => {});
    return () => { active = false; };
  }, []);

  async function handleAvatarChange(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const dataUrl = await resizeImage(file, 300);
      const res = await client.put("/api/auth/me/avatar", { avatarPhoto: dataUrl });
      setUser(res.data.user);
      showToast("Profile photo updated", "success");
    } catch {
      showToast("Could not update photo", "error");
    }
  }

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

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  const [pw, setPw] = useState({ currentPassword: "", newPassword: "", confirm: "" });
  const [pwSaving, setPwSaving] = useState(false);

  async function handleChangePassword(e) {
    e.preventDefault();
    if (pw.newPassword !== pw.confirm) {
      showToast("New passwords do not match", "error");
      return;
    }
    setPwSaving(true);
    try {
      await client.put("/api/auth/me/password", { currentPassword: pw.currentPassword, newPassword: pw.newPassword });
      showToast("Password updated", "success");
      setPw({ currentPassword: "", newPassword: "", confirm: "" });
    } catch (err) {
      showToast(err.response?.data?.error || "Could not update password", "error");
    } finally {
      setPwSaving(false);
    }
  }

  return (
    <div className="acct-profile">
      <h2 className="acct-title">My Profile</h2>
      <p className="acct-subtitle">Manage your account information and settings</p>

      <div className="acct-grid">
        <section className="acct-card acct-info">
          <div className="acct-card-head">
            <span className="acct-card-icon" aria-hidden="true">&#128100;</span>
            <div>
              <h3>Account Information</h3>
              <p>Keep your details up to date</p>
            </div>
          </div>

          <div className="acct-photo-row">
            <div className="acct-photo">
              {user?.avatarPhoto ? <img src={user.avatarPhoto} alt="Your profile" /> : <span>{(user?.name || "?").charAt(0).toUpperCase()}</span>}
              <label className="acct-photo-btn" htmlFor="acct-photo-input" title="Change photo" aria-label="Change photo">&#128247;</label>
              <input id="acct-photo-input" type="file" accept="image/png,image/jpeg,image/webp" onChange={handleAvatarChange} hidden />
            </div>
            <div className="acct-photo-hint">
              <label htmlFor="acct-photo-input" className="acct-outline-btn">Change Photo</label>
              <span>JPG or PNG, resized automatically</span>
            </div>
          </div>

          <form onSubmit={handleSaveProfile} className="acct-form">
            <div className="acct-field-row three">
              <div className="field">
                <label htmlFor="pf-first">First Name</label>
                <input id="pf-first" required maxLength={60} value={form.firstName} onChange={set("firstName")} />
              </div>
              <div className="field">
                <label htmlFor="pf-middle">Middle Name</label>
                <input id="pf-middle" maxLength={60} value={form.middleName} onChange={set("middleName")} />
              </div>
              <div className="field">
                <label htmlFor="pf-last">Last Name</label>
                <input id="pf-last" required maxLength={60} value={form.lastName} onChange={set("lastName")} />
              </div>
            </div>
            <div className="acct-field-row">
              <div className="field">
                <label htmlFor="pf-email">Email Address</label>
                <input id="pf-email" value={user?.email || ""} readOnly />
                <p className="field-hint">To change your email, use the section below.</p>
              </div>
              <div className="field">
                <label htmlFor="pf-phone">Mobile Number</label>
                <input id="pf-phone" required inputMode="numeric" value={form.phone} onChange={set("phone")} />
              </div>
            </div>
            <div className="acct-field-row">
              <div className="field">
                <label htmlFor="pf-age">Age</label>
                <input id="pf-age" type="number" min="1" max="120" value={form.age} onChange={set("age")} />
              </div>
              <div className="field">
                <label htmlFor="pf-gender">Gender</label>
                <select id="pf-gender" value={form.gender} onChange={set("gender")}>
                  <option value="">Prefer not to say</option>
                  <option value="Male">Male</option>
                  <option value="Female">Female</option>
                  <option value="Other">Other</option>
                </select>
              </div>
            </div>
            <div className="acct-actions">
              <button type="submit" className="btn btn-primary" disabled={saving}>{saving ? "Saving..." : "Save Changes"}</button>
            </div>
          </form>
        </section>

        <aside className="acct-side-cards">
          <section className="acct-card acct-status">
            <div className="acct-status-head">
              <span className="acct-status-icon" aria-hidden="true">&#10004;</span>
              <div>
                <h3>Account Status</h3>
                <span className={`acct-status-badge ${user?.verified ? "ok" : ""}`}>
                  {user?.verified ? "Verified Account" : "Not verified yet"}
                </span>
              </div>
            </div>
            <p className="acct-status-note">
              {user?.verified ? "Your account is verified and active." : "Verify your email to place orders and chat with us."}
            </p>
            <ul className="acct-checks">
              <li><span>Email Verified</span><span className={user?.verified ? "tick" : "cross"}>{user?.verified ? "\u2713" : "\u2717"}</span></li>
              <li><span>Mobile Number on file</span><span className={user?.phone ? "tick" : "cross"}>{user?.phone ? "\u2713" : "\u2717"}</span></li>
            </ul>
          </section>

          <AccountTypeSection />
        </aside>

        <section className="acct-card acct-address">
          <div className="acct-card-head">
            <span className="acct-card-icon" aria-hidden="true">&#128205;</span>
            <div>
              <h3>Delivery Address</h3>
              <p>Your default delivery address</p>
            </div>
          </div>
          {address ? (
            <div className="acct-address-box">
              <span className="acct-address-tag">{address.label}</span>
              <p>{address.formatted}</p>
            </div>
          ) : (
            <p className="acct-empty">You have no saved address yet.</p>
          )}
          <Link to="/account/address" className="acct-outline-btn">{address ? "Edit" : "Add an address"}</Link>
        </section>

        <section className="acct-card acct-email">
          <h3>Email Address</h3>
          <p className="acct-subtitle-small">Current: <strong>{user?.email}</strong></p>
          {emailStep === "idle" ? (
            <form onSubmit={handleRequestEmailChange}>
              <div className="field">
                <label htmlFor="em-new">New Email Address</label>
                <input id="em-new" required type="email" value={newEmail} onChange={(e) => setNewEmail(e.target.value)} />
              </div>
              <button type="submit" className="btn btn-outline">Send Confirmation Code</button>
            </form>
          ) : (
            <form onSubmit={handleConfirmEmailChange}>
              <div className="alert alert-info">Enter the code sent to <strong>{newEmail}</strong>.</div>
              <div className="field">
                <label htmlFor="em-code">Confirmation Code</label>
                <input id="em-code" required maxLength={6} value={emailCode} onChange={(e) => setEmailCode(e.target.value)} />
              </div>
              <button type="submit" className="btn btn-primary">Confirm New Email</button>
              <button type="button" className="link-btn" style={{ marginLeft: 12 }} onClick={() => setEmailStep("idle")}>Cancel</button>
            </form>
          )}
        </section>

        <section className="acct-card acct-password">
          <h3>Change Password</h3>
          <p className="acct-subtitle-small">At least 8 characters, with upper and lower case letters, a number, and a symbol.</p>
          <form onSubmit={handleChangePassword}>
            <div className="field">
              <label>Current Password</label>
              <PasswordInput value={pw.currentPassword} onChange={(e) => setPw({ ...pw, currentPassword: e.target.value })} autoComplete="current-password" />
            </div>
            <div className="field">
              <label>New Password</label>
              <PasswordInput value={pw.newPassword} onChange={(e) => setPw({ ...pw, newPassword: e.target.value })} autoComplete="new-password" />
            </div>
            <div className="field">
              <label>Confirm New Password</label>
              <PasswordInput value={pw.confirm} onChange={(e) => setPw({ ...pw, confirm: e.target.value })} autoComplete="new-password" />
            </div>
            <button type="submit" className="btn btn-primary" disabled={pwSaving || !pw.currentPassword || !pw.newPassword}>
              {pwSaving ? "Updating..." : "Update Password"}
            </button>
          </form>
        </section>
      </div>
    </div>
  );
}
