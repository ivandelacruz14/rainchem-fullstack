import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import client from "../api/client";
import PasswordInput from "../components/PasswordInput";
import { useUI } from "../context/UIContext";
import { validatePassword } from "../utils/format";

const RULES = [
  { key: "len", label: "8-24 characters", test: (p) => p.length >= 8 && p.length <= 24 },
  { key: "up", label: "One uppercase letter", test: (p) => /[A-Z]/.test(p) },
  { key: "low", label: "One lowercase letter", test: (p) => /[a-z]/.test(p) },
  { key: "num", label: "One number", test: (p) => /[0-9]/.test(p) },
  { key: "sym", label: "One special symbol", test: (p) => /[^A-Za-z0-9]/.test(p) },
];

const REDIRECT_SECONDS = 4;

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") || "";
  const navigate = useNavigate();
  const { requireLogin } = useUI();

  const [linkState, setLinkState] = useState({ status: "checking", message: "" });
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (!token) {
      setLinkState({ status: "bad", message: "This link is missing its reset code. Please request a new reset email." });
      return;
    }
    client.get("/api/auth/reset-password/check", { params: { token } })
      .then((res) => setLinkState(res.data.valid ? { status: "ok" } : { status: "bad", message: res.data.error }))
      .catch(() => setLinkState({ status: "error", message: "We could not check this link. Please try again in a moment." }));
  }, [token]);

  useEffect(() => {
    if (!done) return undefined;
    const timer = setTimeout(goToLogin, REDIRECT_SECONDS * 1000);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [done]);

  function goToLogin() {
    navigate("/", { replace: true });
    requireLogin("login");
  }

  function requestNewLink() {
    navigate("/", { replace: true });
    requireLogin("forgot");
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    if (password !== confirm) {
      setError("The two passwords do not match.");
      return;
    }
    const problems = validatePassword(password);
    if (problems.length) {
      setError("Password requirements not met: " + problems.join(", "));
      return;
    }
    setBusy(true);
    try {
      await client.post("/api/auth/reset-password", { token, password });
      setDone(true);
    } catch (err) {
      const data = err.response?.data;
      setError(data?.error || "Could not reset your password. Please try again.");
      if (data?.reason) setLinkState({ status: "bad", message: data.error });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="container auth-page">
      <div className="panel">
        <h2>Reset your password</h2>

        {linkState.status === "checking" && <p className="field-hint">Checking your link...</p>}

        {(linkState.status === "bad" || linkState.status === "error") && !done && (
          <>
            <div className="alert alert-error">{linkState.message}</div>
            <button type="button" className="btn btn-primary btn-block" onClick={requestNewLink}>Request a new link</button>
            <p className="auth-switch"><Link to="/">Back to home</Link></p>
          </>
        )}

        {done && (
          <>
            <div className="alert alert-success">
              Your password has been updated. Taking you to the log in screen in a few seconds.
            </div>
            <button type="button" className="btn btn-primary btn-block" onClick={goToLogin}>Log in now</button>
          </>
        )}

        {linkState.status === "ok" && !done && (
          <form onSubmit={handleSubmit}>
            {error && <div className="alert alert-error">{error}</div>}
            <div className="field">
              <label>New password</label>
              <PasswordInput value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" />
              <ul className="pw-rules">
                {RULES.map((rule) => <li key={rule.key} className={rule.test(password) ? "ok" : ""}>{rule.label}</li>)}
              </ul>
            </div>
            <div className="field">
              <label>Confirm new password</label>
              <PasswordInput value={confirm} onChange={(e) => setConfirm(e.target.value)} autoComplete="new-password" />
            </div>
            <button type="submit" className="btn btn-primary btn-block" disabled={busy}>
              {busy ? "Saving..." : "Update password"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
