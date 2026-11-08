import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import client from "../api/client";
import PasswordInput from "../components/PasswordInput";
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
    try {
      const res = await client.post("/api/admin/auth/login", { email, password });
      if (res.data.otpRequired) {
        setChallenge(res.data.challenge);
        setMaskedEmail(res.data.maskedEmail);
        setPassword("");
        setStep("code");
      } else {
        loginWithToken(res.data.token, res.data.admin, res.data.idleMinutes);
      }
    } catch (err) {
      setError(err.response?.data?.error || "Hindi ma-login. Subukan ulit.");
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
      setError(err.response?.data?.error || "Hindi ma-verify ang code.");
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
        <p className="sub-title">{step === "password" ? "Mag-sign in gamit ang iyong account" : "Ilagay ang code mula sa iyong email"}</p>

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
            <button type="submit" className="btn btn-primary btn-block" disabled={busy}>{busy ? "Sinusuri..." : "Next"}</button>
          </form>
        ) : (
          <form onSubmit={verifyCode}>
            <p style={{ fontSize: 14, marginTop: 0 }}>
              Nagpadala kami ng 6-digit na code sa <strong>{maskedEmail}</strong>. Valid ito nang 10 minuto.
            </p>
            <div className="field">
              <label htmlFor="admin-code">Code</label>
              <input
                id="admin-code" className="otp-input" inputMode="numeric" autoComplete="one-time-code" maxLength={6} required
                value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))} placeholder="123456" autoFocus
              />
            </div>
            <button type="submit" className="btn btn-primary btn-block" disabled={busy || code.length !== 6}>{busy ? "Sinusuri..." : "Sign in"}</button>
            <button type="button" className="btn btn-outline btn-block" style={{ marginTop: 8 }} onClick={startOver}>Bumalik</button>
          </form>
        )}
        <p className="field-hint" style={{ textAlign: "center", marginTop: 16 }}>
          Awtomatikong mag-lo-logout pagkatapos ng 10 minutong walang aktibidad.
        </p>
      </div>
    </div>
  );
}
