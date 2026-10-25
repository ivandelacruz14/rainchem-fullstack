import { useState, useEffect } from "react";
import client from "../../api/client";
import { formatDate, validatePassword } from "../../utils/format";
import { useToast } from "../../context/ToastContext";
import { useAdminAuth } from "../../context/AdminAuthContext";
import PasswordInput from "../../components/PasswordInput";

const PASSWORD_RULES = [
  { key: "len", label: "8-24 characters", test: (p) => p.length >= 8 && p.length <= 24 },
  { key: "up", label: "One uppercase", test: (p) => /[A-Z]/.test(p) },
  { key: "low", label: "One lowercase", test: (p) => /[a-z]/.test(p) },
  { key: "num", label: "One number", test: (p) => /[0-9]/.test(p) },
  { key: "sym", label: "One symbol", test: (p) => /[^A-Za-z0-9]/.test(p) },
];

const EMPTY = { name: "", email: "", role: "Distributor", password: "", permissions: [], confirmPassword: "" };

function PermissionChecks({ options, value, onChange }) {
  function toggle(key) {
    onChange(value.includes(key) ? value.filter((k) => k !== key) : [...value, key]);
  }
  return (
    <div className="perm-list">
      {options.map((opt) => (
        <label key={opt.key} className="perm-item">
          <input type="checkbox" checked={value.includes(opt.key)} onChange={() => toggle(opt.key)} />
          <span>{opt.label}</span>
        </label>
      ))}
    </div>
  );
}

export default function AdminAccounts() {
  const { admin: me } = useAdminAuth();
  const showToast = useToast();
  const [admins, setAdmins] = useState([]);
  const [permissionOptions, setPermissionOptions] = useState([]);
  const [roles, setRoles] = useState(["Head Admin", "Distributor"]);
  const [dialog, setDialog] = useState(null); // {type: create|edit|password|delete, account?}
  const [form, setForm] = useState(EMPTY);
  const [busy, setBusy] = useState(false);

  function load() {
    client.get("/api/admin/auth/accounts").then((res) => {
      setAdmins(res.data.admins);
      setPermissionOptions(res.data.permissions);
      setRoles(res.data.roles);
    });
  }
  useEffect(load, []);

  function open(type, account = null) {
    setForm(account
      ? { ...EMPTY, name: account.name, role: account.isHead ? "Head Admin" : "Distributor", permissions: account.permissions, isActive: account.isActive }
      : EMPTY);
    setDialog({ type, account });
  }

  function close() {
    setDialog(null);
    setForm(EMPTY);
  }

  async function submit(e) {
    e.preventDefault();
    const { type, account } = dialog;
    if ((type === "create" || type === "password") && validatePassword(form.password).length) {
      showToast("Password requirements not met: " + validatePassword(form.password).join(", "), "error");
      return;
    }
    setBusy(true);
    try {
      if (type === "create") {
        await client.post("/api/admin/auth/accounts", {
          name: form.name, email: form.email, role: form.role, password: form.password,
          permissions: form.permissions, confirmPassword: form.confirmPassword,
        });
        showToast("Account created", "success");
      } else if (type === "edit") {
        await client.put(`/api/admin/auth/accounts/${account.id}`, {
          name: form.name, role: form.role, permissions: form.permissions,
          isActive: form.isActive, confirmPassword: form.confirmPassword,
        });
        showToast("Account updated", "success");
      } else if (type === "password") {
        await client.post(`/api/admin/auth/accounts/${account.id}/password`, {
          newPassword: form.password, confirmPassword: form.confirmPassword,
        });
        showToast("Password reset", "success");
      } else if (type === "delete") {
        await client.delete(`/api/admin/auth/accounts/${account.id}`, { data: { confirmPassword: form.confirmPassword } });
        showToast("Account removed", "success");
      }
      close();
      load();
    } catch (err) {
      showToast(err.response?.data?.error || "That did not work. Please try again.", "error");
    } finally {
      setBusy(false);
    }
  }

  const type = dialog?.type;
  const isDistributor = form.role === "Distributor";
  const titles = { create: "Add account", edit: "Edit account", password: "Reset password", delete: "Remove account" };

  return (
    <div>
      <div className="admin-topbar">
        <div>
          <h1>Admin Accounts</h1>
          <p>Head Admins manage everything. Distributors only get the features you tick. There is no public sign-up.</p>
        </div>
        <button type="button" className="btn btn-primary" onClick={() => open("create")}>+ Add Account</button>
      </div>

      <div className="admin-panel">
        <div className="table-wrap">
          <table className="admin-table stack">
            <thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Access</th><th>Status</th><th>Created</th><th></th></tr></thead>
            <tbody>
              {admins.map((a) => (
                <tr key={a.id}>
                  <td data-label="Name" className="cell-name">{a.name}{a.id === me?.id && <span className="muted"> (you)</span>}</td>
                  <td data-label="Email" className="cell-wrap">{a.email}</td>
                  <td data-label="Role"><span className="badge">{a.role}</span></td>
                  <td data-label="Access">
                    {a.isHead ? "Full access" : a.permissions.length ? a.permissions.join(", ") : "Dashboard only"}
                  </td>
                  <td data-label="Status">{a.isActive ? "Active" : <span className="pill pill-low">Disabled</span>}</td>
                  <td data-label="Created">{formatDate(a.createdAt).split(",")[0]}</td>
                  <td data-label="" className="row-cell">
                    {a.id !== me?.id && (
                      <div className="row-actions">
                        <button type="button" className="icon-action wide" onClick={() => open("edit", a)}>Edit</button>
                        <button type="button" className="icon-action wide" onClick={() => open("password", a)}>Password</button>
                        <button type="button" className="icon-action wide" onClick={() => open("delete", a)}>Remove</button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {dialog && (
        <div className="overlay" onClick={close}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head">
              <h3 style={{ margin: 0 }}>{titles[type]}{dialog.account ? `: ${dialog.account.name}` : ""}</h3>
              <button type="button" className="modal-close" onClick={close}>&times;</button>
            </div>
            <form className="modal-body" onSubmit={submit}>
              {type === "delete" && (
                <p style={{ marginTop: 0 }}>This removes the account. Anything it owned goes back to the head office. Disabling the account instead keeps it for later.</p>
              )}

              {(type === "create" || type === "edit") && (
                <>
                  <div className="field"><label>Full name</label><input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
                  {type === "create" && (
                    <div className="field"><label>Email</label><input required type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></div>
                  )}
                  <div className="field">
                    <label>Role</label>
                    <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
                      {roles.map((r) => <option key={r}>{r}</option>)}
                    </select>
                  </div>
                  {isDistributor ? (
                    <div className="field">
                      <label>What this distributor can do</label>
                      <PermissionChecks options={permissionOptions} value={form.permissions} onChange={(permissions) => setForm({ ...form, permissions })} />
                    </div>
                  ) : (
                    <div className="alert alert-info">Head Admins can do everything, including managing accounts.</div>
                  )}
                  {type === "edit" && (
                    <label className="perm-item">
                      <input type="checkbox" checked={form.isActive} onChange={(e) => setForm({ ...form, isActive: e.target.checked })} />
                      <span>Account is active (untick to disable sign-in)</span>
                    </label>
                  )}
                </>
              )}

              {(type === "create" || type === "password") && (
                <div className="field">
                  <label>{type === "create" ? "Temporary password" : "New password"}</label>
                  <PasswordInput value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} autoComplete="new-password" />
                  <ul className="pw-rules">
                    {PASSWORD_RULES.map((rule) => <li key={rule.key} className={rule.test(form.password) ? "ok" : ""}>{rule.label}</li>)}
                  </ul>
                </div>
              )}

              <div className="field">
                <label>Your password (to confirm)</label>
                <PasswordInput value={form.confirmPassword} onChange={(e) => setForm({ ...form, confirmPassword: e.target.value })} autoComplete="current-password" />
              </div>
              <div className="form-actions">
                <button type="button" className="btn btn-outline" onClick={close}>Cancel</button>
                <button type="submit" className="btn btn-primary" disabled={busy}>{busy ? "Saving..." : titles[type]}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
