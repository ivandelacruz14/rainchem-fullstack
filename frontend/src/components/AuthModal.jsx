import { useState } from "react";
import client from "../api/client";
import { useAuth } from "../context/AuthContext";
import { useUI } from "../context/UIContext";
import { useToast } from "../context/ToastContext";
import { validatePassword } from "../utils/format";
import GoogleSignInButton from "./GoogleSignInButton";
import PasswordInput from "./PasswordInput";

const PASSWORD_RULES = [
  { key: "len", label: "8-24 characters", test: (p) => p.length >= 8 && p.length <= 24 },
  { key: "up", label: "One uppercase letter", test: (p) => /[A-Z]/.test(p) },
  { key: "low", label: "One lowercase letter", test: (p) => /[a-z]/.test(p) },
  { key: "num", label: "One number", test: (p) => /[0-9]/.test(p) },
  { key: "sym", label: "One special symbol", test: (p) => /[^A-Za-z0-9]/.test(p) },
];

export default function AuthModal() {
  const [remember, setRemember] = useState(true);
  const { authModal, setAuthModal, closeAuth } = useUI();
  const { loginWithToken } = useAuth();
  const showToast = useToast();

  const [form, setForm] = useState({});
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [pendingEmail, setPendingEmail] = useState("");
  const [devCode, setDevCode] = useState("");

  if (!authModal.open) return null;
  const mode = authModal.mode;

  function update(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  function switchMode(nextMode) {
    setError("");
    setInfo("");
    setAuthModal({ open: true, mode: nextMode });
  }

  async function handleLogin(e) {
    e.preventDefault();
    setError("");
    try {
      const res = await client.post("/api/auth/login", { email: form.email, password: form.password });
      loginWithToken(res.data.token, res.data.user, remember);
      showToast(`Welcome back, ${res.data.user.name.split(" ")[0]}!`, "success");
      closeAuth();
    } catch (err) {
      const data = err.response?.data;
      if (data?.needsVerification) {
        setPendingEmail(data.email);
        switchMode("verify");
      } else {
        setError(data?.error || "Something went wrong. Please try again.");
      }
    }
  }

  async function handleRegister(e) {
    e.preventDefault();
    setError("");
    const passwordErrors = validatePassword(form.password || "");
    if (form.password !== form.password2) {
      setError("Passwords do not match.");
      return;
    }
    if (passwordErrors.length) {
      setError("Password requirements not met: " + passwordErrors.join(", "));
      return;
    }
    try {
      const res = await client.post("/api/auth/register", {
        name: form.name, email: form.email, phone: form.phone, password: form.password,
      });
      setPendingEmail(res.data.email);
      switchMode("verify");
    } catch (err) {
      const errors = err.response?.data?.errors;
      setError(errors ? errors.join(" ") : "Something went wrong. Please try again.");
    }
  }

  async function handleVerify(e) {
    e.preventDefault();
    setError("");
    try {
      const res = await client.post("/api/auth/verify-email", { email: pendingEmail, code: form.code });
      loginWithToken(res.data.token, res.data.user);
      showToast(`Account verified! Welcome, ${res.data.user.name.split(" ")[0]}.`, "success");
      closeAuth();
    } catch (err) {
      setError(err.response?.data?.error || "Incorrect or expired code.");
    }
  }

  async function handleResend() {
    try {
      await client.post("/api/auth/resend-code", { email: pendingEmail });
      showToast("A new verification code has been sent", "success");
    } catch {
      showToast("Could not resend the code", "error");
    }
  }

  async function handleForgot(e) {
    e.preventDefault();
    setError("");
    try {
      const res = await client.post("/api/auth/forgot-password", { email: form.email });
      setInfo(res.data.message);
    } catch {
      setError("Something went wrong. Please try again.");
    }
  }

  async function handleGoogleCredential(token) {
    setError("");
    try {
      const res = await client.post("/api/auth/google", { token });
      loginWithToken(res.data.token, res.data.user);
      showToast(`Welcome, ${res.data.user.name.split(" ")[0]}!`, "success");
      closeAuth();
    } catch (err) {
      setError(err.response?.data?.error || "Could not sign in with Google.");
    }
  }

  return (
    <div className="overlay" onClick={closeAuth}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h3 style={{ margin: 0, fontSize: 20 }}>
            {mode === "login" && "Log In"}
            {mode === "register" && "Create Account"}
            {mode === "verify" && "Verify Your Email"}
            {mode === "forgot" && "Reset Password"}
          </h3>
          <button className="modal-close" onClick={closeAuth}>&times;</button>
        </div>
        <div className="modal-body">
          {error && <div className="alert alert-error">{error}</div>}
          {info && <div className="alert alert-info">{info}</div>}

          {mode === "login" && (
            <form onSubmit={handleLogin}>
              <div className="field">
                <label>Email Address</label>
                <input required type="email" value={form.email || ""} onChange={(e) => update("email", e.target.value)} autoComplete={remember ? "username" : "off"} />
              </div>
              <div className="field">
                <label>Password</label>
                <PasswordInput value={form.password || ""} onChange={(e) => update("password", e.target.value)} autoComplete={remember ? "current-password" : "off"} />
              </div>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
                <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, cursor: "pointer" }}>
                  <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} style={{ width: "auto" }} />
                  Remember me
                </label>
                <button type="button" className="link-btn" style={{ fontSize: 12.5 }} onClick={() => switchMode("forgot")}>
                  Forgot password?
                </button>
              </div>
              <button type="submit" className="btn btn-primary btn-block">Log In</button>
              <div className="divider-text">or</div>
              <GoogleSignInButton onCredential={handleGoogleCredential} />
              <p className="auth-switch">
                Don't have an account?{" "}
                <button type="button" className="link-btn" onClick={() => switchMode("register")}>Sign up</button>
              </p>
            </form>
          )}

          {mode === "register" && (
            <form onSubmit={handleRegister}>
              <div className="field">
                <label>Full Name</label>
                <input required value={form.name || ""} onChange={(e) => update("name", e.target.value)} />
              </div>
              <div className="field">
                <label>Email Address</label>
                <input required type="email" value={form.email || ""} onChange={(e) => update("email", e.target.value)} />
              </div>
              <div className="field">
                <label>Contact Number</label>
                <input required placeholder="09xx xxx xxxx" value={form.phone || ""} onChange={(e) => update("phone", e.target.value)} />
              </div>
              <div className="field">
                <label>Password</label>
                <PasswordInput value={form.password || ""} onChange={(e) => update("password", e.target.value)} autoComplete="new-password" />
                <ul className="pw-rules">
                  {PASSWORD_RULES.map((rule) => (
                    <li key={rule.key} className={rule.test(form.password || "") ? "ok" : ""}>{rule.label}</li>
                  ))}
                </ul>
              </div>
              <div className="field">
                <label>Confirm Password</label>
                <PasswordInput value={form.password2 || ""} onChange={(e) => update("password2", e.target.value)} autoComplete="new-password" />
              </div>
              <button type="submit" className="btn btn-primary btn-block">Create Account</button>
              <div className="divider-text">or</div>
              <GoogleSignInButton onCredential={handleGoogleCredential} />
              <p className="auth-switch">
                Already have an account?{" "}
                <button type="button" className="link-btn" onClick={() => switchMode("login")}>Log in</button>
              </p>
            </form>
          )}

          {mode === "verify" && (
            <>
              <div className="alert alert-info">
                We sent a 6-digit verification code to <strong>{pendingEmail}</strong>. Enter it below to activate your account.
              </div>
              {devCode && (
                <div className="admin-demo-hint" style={{ marginBottom: 16 }}>
                  Development mode: check the backend console output for your code.
                </div>
              )}
              <form onSubmit={handleVerify}>
                <div className="field">
                  <label>Verification Code</label>
                  <input required maxLength={6} placeholder="123456" value={form.code || ""} onChange={(e) => update("code", e.target.value)} />
                </div>
                <button type="submit" className="btn btn-primary btn-block">Verify &amp; Continue</button>
              </form>
              <p className="auth-switch">
                Didn't get a code?{" "}
                <button type="button" className="link-btn" onClick={handleResend}>Resend code</button>
              </p>
            </>
          )}

          {mode === "forgot" && (
            <form onSubmit={handleForgot}>
              <div className="field">
                <label>Email Address</label>
                <input required type="email" value={form.email || ""} onChange={(e) => update("email", e.target.value)} />
              </div>
              <button type="submit" className="btn btn-primary btn-block">Send Reset Link</button>
              <p className="auth-switch">
                <button type="button" className="link-btn" onClick={() => switchMode("login")}>Back to log in</button>
              </p>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}