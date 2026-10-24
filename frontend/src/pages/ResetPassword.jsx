import { useEffect, useState } from "react";
import { Link, useSearchParams, useNavigate } from "react-router-dom";
import client from "../api/client";
import { useUI } from "../context/UIContext";
import { validatePassword } from "../utils/format";
import PasswordInput from "../components/PasswordInput";

const RULES = [
  { key: "len", label: "8-24 characters", test: (p) => p.length >= 8 && p.length <= 24 },
  { key: "up", label: "One uppercase letter", test: (p) => /[A-Z]/.test(p) },
  { key: "low", label: "One lowercase letter", test: (p) => /[a-z]/.test(p) },
  { key: "num", label: "One number", test: (p) => /[0-9]/.test(p) },
  { key: "sym", label: "One special symbol", test: (p) => /[^A-Za-z0-9]/.test(p) },
];

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") || "";
  const navigate = useNavigate();
  const { requireLogin } = useUI();

  const [status, setStatus] = useState(token ? "checking" : "invalid");
  const [problem, setProblem] = useState(token ? "" : "This link is missing its reset token. Please request a new one.");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!token) return;
    client.get("/api/auth/reset-password/validate", { params: { token } })
      .then(() => setStatus("ready"))
      .catch((err) => {
        setStatus("invalid");
        setProblem(err.response?.data?.error || "This reset link could not be checked. Please try again.");
      });
  }, [token]);

  function goToLogin() {
    navigate("/", { replace: true });
    requireLogin("login");
  }

  useEffect(() => {
    if (status !== "done") return undefined;
    const timer = setTimeout(goToLogin, 2500);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status]);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    const unmet = validatePassword(password);
    if (unmet.length) {
      setError("Password requirements not met: " + unmet.join(", "));
      return;
    }
    setSaving(true);
    try {
      await client.post("/api/auth/reset-password", { token, password });
      setStatus("done");
    } catch (err) {
      const data = err.response?.data;
      if (data?.reason) {
        setStatus("invalid");
        setProblem(data.error);
      } else {
        setError(data?.error || "Could not reset your password. Please try again.");
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="container narrow-page">
      <div className="panel">
        <h2>Reset Your Password</h2>

        {status === "checking" && <p className="field-hint">Checking your reset link...</p>}

        {status === "invalid" && (
          <>
            <div className="alert alert-error">{problem}</div>
            <button type="button" className="btn btn-primary btn-block" onClick={() => { navigate("/", { replace: true }); requireLogin("forgot"); }}>
              Request a new link
            </button>
            <p className="auth-switch"><Link to="/">Back to home</Link></p>
          </>
        )}

        {status === "ready" && (
          <form onSubmit={handleSubmit}>
            {error && <div className="alert alert-error">{error}</div>}
            <div className="field">
              <label>New Password</label>
              <PasswordInput value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" />
              <ul className="pw-rules">
                {RULES.map((rule) => <li key={rule.key} className={rule.test(password) ? "ok" : ""}>{rule.label}</li>)}
              </ul>
            </div>
            <div className="field">
              <label>Confirm New Password</label>
              <PasswordInput value={confirm} onChange={(e) => setConfirm(e.target.value)} autoComplete="new-password" />
            </div>
            <button type="submit" className="btn btn-primary btn-block" disabled={saving}>
              {saving ? "Saving..." : "Update Password"}
            </button>
          </form>
        )}

        {status === "done" && (
          <>
            <div className="alert alert-success">Your password has been updated. Taking you to the login...</div>
            <button type="button" className="btn btn-primary btn-block" onClick={goToLogin}>Log in now</button>
          </>
        )}
      </div>
    </div>
  );
}
