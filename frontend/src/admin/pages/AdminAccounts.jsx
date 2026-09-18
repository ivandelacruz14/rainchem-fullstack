import { useState, useEffect } from "react";
import client from "../../api/client";
import { formatDate, validatePassword } from "../../utils/format";
import { useToast } from "../../context/ToastContext";

const PASSWORD_RULES = [
  { key: "len", label: "8-24 characters", test: (p) => p.length >= 8 && p.length <= 24 },
  { key: "up", label: "One uppercase", test: (p) => /[A-Z]/.test(p) },
  { key: "low", label: "One lowercase", test: (p) => /[a-z]/.test(p) },
  { key: "num", label: "One number", test: (p) => /[0-9]/.test(p) },
  { key: "sym", label: "One symbol", test: (p) => /[^A-Za-z0-9]/.test(p) },
];

export default function AdminAccounts() {
  const [admins, setAdmins] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", role: "Admin", password: "" });
  const showToast = useToast();

  function load() {
    client.get("/api/admin/auth/accounts").then((res) => setAdmins(res.data.admins));
  }
  useEffect(load, []);

  async function handleSubmit(e) {
    e.preventDefault();
    const errors = validatePassword(form.password);
    if (errors.length) {
      showToast("Password requirements not met: " + errors.join(", "), "error");
      return;
    }
    try {
      await client.post("/api/admin/auth/accounts", form);
      showToast("Admin account created", "success");
      setShowForm(false);
      setForm({ name: "", email: "", role: "Admin", password: "" });
      load();
    } catch (err) {
      showToast(err.response?.data?.error || "Could not create admin account", "error");
    }
  }

  async function handleDelete(id) {
    if (!window.confirm("Remove this admin account?")) return;
    try {
      await client.delete(`/api/admin/auth/accounts/${id}`);
      showToast("Admin account removed", "error");
      load();
    } catch (err) {
      showToast(err.response?.data?.error || "Could not remove this admin", "error");
    }
  }

  return (
    <div>
      <div className="admin-topbar">
        <div><h1>Admin Accounts</h1><p>Manage who has access to this dashboard. No public sign-up exists, accounts are created here only.</p></div>
        <button className="btn btn-primary" onClick={() => setShowForm(true)}>+ Add Admin</button>
      </div>
      <div className="admin-panel">
        <div className="table-wrap">
          <table className="admin-table">
            <thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Created</th><th></th></tr></thead>
            <tbody>
              {admins.map((a) => (
                <tr key={a.id}>
                  <td style={{ fontWeight: 600 }}>{a.name}</td>
                  <td>{a.email}</td>
                  <td><span className="badge">{a.role}</span></td>
                  <td>{formatDate(a.createdAt).split(",")[0]}</td>
                  <td>{admins.length > 1 && <button className="icon-action" onClick={() => handleDelete(a.id)}>Remove</button>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {showForm && (
        <div className="overlay" onClick={() => setShowForm(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head"><h3 style={{ margin: 0 }}>Add Admin Account</h3><button className="modal-close" onClick={() => setShowForm(false)}>&times;</button></div>
            <div className="modal-body">
              <form onSubmit={handleSubmit}>
                <div className="field"><label>Full Name</label><input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
                <div className="field"><label>Email</label><input required type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></div>
                <div className="field">
                  <label>Role</label>
                  <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
                    <option>Admin</option><option>Support Staff</option><option>Content Manager</option>
                  </select>
                </div>
                <div className="field">
                  <label>Temporary Password</label>
                  <input required type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
                  <ul className="pw-rules">
                    {PASSWORD_RULES.map((rule) => (
                      <li key={rule.key} className={rule.test(form.password) ? "ok" : ""}>{rule.label}</li>
                    ))}
                  </ul>
                </div>
                <div className="form-actions">
                  <button type="button" className="btn btn-outline" onClick={() => setShowForm(false)}>Cancel</button>
                  <button type="submit" className="btn btn-primary">Create Admin Account</button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
