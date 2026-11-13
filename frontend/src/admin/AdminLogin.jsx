import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import client from "../api/client";
import PasswordInput from "../components/PasswordInput";
import Turnstile, { captchaEnabled } from "../components/Turnstile";
import { ADMIN_NOTICE_KEY, useAdminAuth } from "../context/AdminAuthContext";

/** Two steps: email and password, then the six-digit code emailed to the admin. */
export default function AdminLogin() {
  const { admin, loginWithToken } = useAdminAuth();
  const navigate = useNavigate();
  const [step, setStep] = useState("password");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [challenge, setChallenge] = useState("");
  const [maskedEmail, setMaskedEmail] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const captchaRef = useRef(null);
  const [captchaToken, setCaptchaToken] = useState("");
  function resetCaptcha() {
    captchaRef.current?.reset();
    setCaptchaToken("");
  }

  useEffect(() => {
    const saved = sessionStorage.getItem(ADMIN_NOTICE_KEY);
    if (saved) {
      setNotice(saved);
      sessionStorage.removeItem(ADMIN_NOTICE_KEY);
    }
  }, []);

  useEffect(() => {
    if (admin) navigate("/admin", { replace: true });
  }, [admin, navigate]);

  async function sendPassword(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setNotice("");
    if (captchaEnabled() && !captchaToken) {
      setError("Please complete the security check.");
      return;
    }
    try {
      const res = await client.post("/api/admin/auth/login", { email, password, captchaToken });
      if (res.data.otpRequired) {
        setChallenge(res.data.challenge);
        setMaskedEmail(res.data.maskedEmail);
        setPassword("");
        setStep("code");
      } else {
        loginWithToken(res.data.token, res.data.admin, res.data.idleMinutes);
      }
    } catch (err) {
      resetCaptcha();
      setError(err.response?.data?.error || "Could not sign in. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  async function verifyCode(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const res = await client.post("/api/admin/auth/login/verify", { challenge, code });
      loginWithToken(res.data.token, res.data.admin, res.data.idleMinutes);
    } catch (err) {
      setError(err.response?.data?.error || "The code could not be verified.");
      setCode("");
    } finally {
      setBusy(false);
    }
  }

  function startOver() {
    setStep("password");
    setChallenge("");
    setCode("");
    setError("");
  }

  return (
    <div className="admin-login-screen">
      <div className="admin-login-card">
        <h2 style={{ textAlign: "center", margin: "0 0 4px" }}>Admin Console</h2>
        <p className="sub-title">{step === "password" ? "Sign in with your account" : "Enter the code from your email"}</p>

        {notice && <div className="alert alert-info" role="status">{notice}</div>}
        {error && <div className="alert alert-error" role="alert">{error}</div>}

        {step === "password" ? (
          <form onSubmit={sendPassword}>
            <div className="field">
              <label htmlFor="admin-email">Email</label>
              <input id="admin-email" type="email" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
            <div className="field">
              <label htmlFor="admin-password">Password</label>
              <PasswordInput id="admin-password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
            </div>
            <Turnstile ref={captchaRef} onToken={setCaptchaToken} />
            <button type="submit" className="btn btn-primary btn-block" disabled={busy}>{busy ? "Checking..." : "Next"}</button>
          </form>
        ) : (
          <form onSubmit={verifyCode}>
            <p style={{ fontSize: 14, marginTop: 0 }}>
              We sent a 6-digit code to <strong>{maskedEmail}</strong>. It is valid for 10 minutes.
            </p>
            <div className="field">
              <label htmlFor="admin-code">Code</label>
              <input
                id="admin-code" className="otp-input" inputMode="numeric" autoComplete="one-time-code" maxLength={6} required
                value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))} placeholder="123456" autoFocus
              />
            </div>
            <button type="submit" className="btn btn-primary btn-block" disabled={busy || code.length !== 6}>{busy ? "Checking..." : "Sign in"}</button>
            <button type="button" className="btn btn-outline btn-block" style={{ marginTop: 8 }} onClick={startOver}>Back</button>
          </form>
        )}
        <p className="field-hint" style={{ textAlign: "center", marginTop: 16 }}>
          You will be signed out automatically after 10 minutes of inactivity.
        </p>
      </div>
    </div>
  );
}
