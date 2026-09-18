import { useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import client from "../api/client";
import { validatePassword } from "../utils/format";

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") || "";
  const navigate = useNavigate();

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");

    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    const passwordErrors = validatePassword(password);
    if (passwordErrors.length) {
      setError("Password requirements not met: " + passwordErrors.join(", "));
      return;
    }

    try {
      await client.post("/api/auth/reset-password", { token, password });
      setDone(true);
    } catch (err) {
      setError(err.response?.data?.error || "This reset link is invalid or has expired.");
    }
  }

  return (
    <div className="container" style={{ maxWidth: 440, padding: "80px 24px" }}>
      <div className="panel">
        <h2>Reset Your Password</h2>
        {done ? (
          <>
            <div className="alert alert-success">Your password has been updated. You can now log in.</div>
            <button className="btn btn-primary btn-block" onClick={() => navigate("/")}>Back to Home</button>
          </>
        ) : (
          <form onSubmit={handleSubmit}>
            {error && <div className="alert alert-error">{error}</div>}
            {!token && <div className="alert alert-error">This link is missing a reset token.</div>}
            <div className="field">
              <label>New Password</label>
              <input required type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
            </div>
            <div className="field">
              <label>Confirm New Password</label>
              <input required type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} />
            </div>
            <button type="submit" className="btn btn-primary btn-block" disabled={!token}>Update Password</button>
          </form>
        )}
      </div>
    </div>
  );
}
