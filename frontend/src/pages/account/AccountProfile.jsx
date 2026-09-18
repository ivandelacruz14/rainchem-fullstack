import { useAuth } from "../../context/AuthContext";

export default function AccountProfile() {
  const { user } = useAuth();

  return (
    <div>
      <h2>Profile</h2>
      <div className="panel" style={{ maxWidth: 520 }}>
        <div className="field"><label>Full Name</label><input value={user?.name || ""} disabled /></div>
        <div className="field"><label>Email</label><input value={user?.email || ""} disabled /></div>
        <div className="field"><label>Phone</label><input value={user?.phone || ""} disabled /></div>
        {user?.hasGoogleLogin && <span className="badge" style={{ marginRight: 8 }}>Linked to Google</span>}
        {user?.verified && <span className="badge">Verified Account</span>}
      </div>
    </div>
  );
}
