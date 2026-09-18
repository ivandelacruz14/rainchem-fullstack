import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import client from "../api/client";
import { useAdminAuth } from "../context/AdminAuthContext";

export default function AdminLogin() {
  const { loginWithToken } = useAdminAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    try {
      const res = await client.post("/api/admin/auth/login", { email, password });
      loginWithToken(res.data.token, res.data.admin);
      navigate("/admin");
    } catch (err) {
      setError(err.response?.data?.error || "Incorrect email or password.");
    }
  }

  return (
    <div className="admin-login-screen">
      <div className="admin-login-card">
        <div className="brand" style={{ justifyContent: "center", marginBottom: 6 }}>
          <span className="dot"></span>Rain<span className="sub">chem</span>
        </div>
        <p className="sub-title">Admin Console - internal access only</p>
        {error && <div className="alert alert-error">{error}</div>}
        <form onSubmit={handleSubmit}>
          <div className="field"><label>Admin Email</label><input required type="email" value={email} onChange={(e) => setEmail(e.target.value)} /></div>
          <div className="field"><label>Password</label><input required type="password" value={password} onChange={(e) => setPassword(e.target.value)} /></div>
          <button type="submit" className="btn btn-primary btn-block">Log In to Dashboard</button>
        </form>
        <div className="admin-demo-hint">
          Demo admin: admin@raincheminternational.com / Admin123!<br />
          There is no public sign-up. New admin accounts are created from inside this dashboard.
        </div>
        <p className="auth-switch"><Link to="/">Back to storefront</Link></p>
      </div>
    </div>
  );
}
