import { useState, useEffect, useCallback } from "react";
import client from "../../api/client";
import { formatDate, validatePassword } from "../../utils/format";
import { useToast } from "../../context/ToastContext";
import { useAdminAuth } from "../../context/AdminAuthContext";

const PERMISSION_LABELS = {
  manage_products: "Add and edit own products",
  manage_services: "Add and edit own services and areas",
  view_orders: "View orders containing own products",
  view_sales: "View sales analytics for own products",
};

const EMPTY_FORM = { name: "", email: "", role: "Distributor", password: "", permissions: [], currentPassword: "" };

function PermissionPicker({ value, onChange }) {
  function toggle(key) {
    onChange(value.includes(key) ? value.filter((k) => k !== key) : [...value, key]);
  }
  return (
    <fieldset className="permission-picker">
      <legend>Permissions</legend>
      {Object.entries(PERMISSION_LABELS).map(([key, label]) => (
        <label key={key}>
          <input type="checkbox" checked={value.includes(key)} onChange={() => toggle(key)} />
          <span>{label}</span>
        </label>
      ))}
    </fieldset>
  );
}

export default function AdminAccounts() {
  const { admin: me } = useAdminAuth();
  const showToast = useToast();
  const [admins, setAdmins] = useState([]);
  const [modal, setModal] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);

  const load = useCallback(() => {
    client.get("/api/admin/auth/accounts").then((res) => setAdmins(res.data.admins));
  }, []);
  useEffect(load, [load]);

  function openCreate() {
    setForm(EMPTY_FORM);
    setModal({ type: "create" });
  }

  function openEdit(account) {
    setForm({
      name: account.name, email: account.email, role: account.role, password: "",
      permissions: account.permissions, currentPassword: "", isActive: account.isActive,
    });
    setModal({ type: "edit", account });
  }

  function openDelete(account) {
    setForm({ ...EMPTY_FORM });
    setModal({ type: "delete", account });
  }

  async function handleSubmit(e) {
    e.preventDefault();
    const isCreate = modal.type === "create";
    if (form.password) {
      const unmet = validatePassword(form.password);
      if (unmet.length) {
        showToast("Password requirements not met: " + unmet.join(", "), "error");
        return;
      }
    }
    try {
      if (isCreate) {
        await client.post("/api/admin/auth/accounts", form);
        showToast("Account created", "success");
      } else {
        const body = {
          name: form.name, currentPassword: form.currentPassword,
          newPassword: form.password || undefined,
        };
        if (modal.account.id !== me.id) {
          Object.assign(body, { role: form.role, isActive: form.isActive, permissions: form.permissions });
        }
        await client.put(`/api/admin/auth/accounts/${modal.account.id}`, body);
        showToast("Account updated", "success");
      }
      setModal(null);
      load();
    } catch (err) {
      showToast(err.response?.data?.error || "Could not save this account", "error");
    }
  }

  async function handleDelete(e) {
    e.preventDefault();
    try {
      await client.delete(`/api/admin/auth/accounts/${modal.account.id}`, { data: { currentPassword: form.currentPassword } });
      showToast("Account removed", "success");
      setModal(null);
      load();
    } catch (err) {
      showToast(err.response?.data?.error || "Could not remove this account", "error");
    }
  }

  const editing = modal?.type === "edit";
  const isSelf = editing && modal.account.id === me.id;
  const showPermissions = form.role === "Distributor" && !isSelf;

  return (
    <div>
      <div className="admin-topbar">
        <div>
          <h1>Accounts &amp; Roles</h1>
          <p>Head Admins manage everything. Distributors only get the permissions you tick. There is no public admin sign-up.</p>
        </div>
        <button type="button" className="btn btn-primary" onClick={openCreate}>+ Add Account</button>
      </div>

      <div className="admin-panel">
        <div className="table-wrap">
          <table className="admin-table">
            <thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Permissions</th><th>Status</th><th>Created</th><th></th></tr></thead>
            <tbody>
              {admins.map((a) => (
                <tr key={a.id}>
                  <td className="strong">{a.name}</td>
                  <td className="wrap-cell">{a.email}</td>
                  <td><span className="badge">{a.role}</span></td>
                  <td className="wrap-cell">{a.isHead ? "Full access" : a.permissions.map((k) => PERMISSION_LABELS[k]).join(", ") || "None"}</td>
                  <td>{a.isActive ? "Active" : "Disabled"}</td>
                  <td>{formatDate(a.createdAt).split(",")[0]}</td>
                  <td>
                    <div className="row-actions">
                      <button type="button" className="icon-action" onClick={() => openEdit(a)}>Edit</button>
                      {a.id !== me.id && <button type="button" className="icon-action" onClick={() => openDelete(a)}>Remove</button>}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {(modal?.type === "create" || editing) && (
        <div className="overlay" onClick={() => setModal(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head">
              <h3>{editing ? "Edit Account" : "Add Account"}</h3>
              <button type="button" className="modal-close" onClick={() => setModal(null)}>&times;</button>
            </div>
            <div className="modal-body">
              <form onSubmit={handleSubmit}>
                <div className="field"><label>Full Name</label><input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
                <div className="field"><label>Email</label><input required type="email" disabled={editing} value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></div>
                {!isSelf && (
                  <div className="field">
                    <label>Role</label>
                    <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
                      <option>Distributor</option>
                      <option>Head Admin</option>
                    </select>
                  </div>
                )}
                {showPermissions && <PermissionPicker value={form.permissions} onChange={(permissions) => setForm({ ...form, permissions })} />}
                {editing && !isSelf && (
                  <label className="check-row">
                    <input type="checkbox" checked={form.isActive} onChange={(e) => setForm({ ...form, isActive: e.target.checked })} />
                    <span>Account is active</span>
                  </label>
                )}
                <div className="field">
                  <label>{editing ? "New password (leave blank to keep)" : "Temporary password"}</label>
                  <input type="password" required={!editing} autoComplete="new-password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
                </div>
                <div className="field">
                  <label>Your password (to confirm)</label>
                  <input type="password" required autoComplete="current-password" value={form.currentPassword} onChange={(e) => setForm({ ...form, currentPassword: e.target.value })} />
                </div>
                <div className="form-actions">
                  <button type="button" className="btn btn-outline" onClick={() => setModal(null)}>Cancel</button>
                  <button type="submit" className="btn btn-primary">{editing ? "Save Changes" : "Create Account"}</button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {modal?.type === "delete" && (
        <div className="overlay" onClick={() => setModal(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head"><h3>Remove {modal.account.name}?</h3></div>
            <div className="modal-body">
              <form onSubmit={handleDelete}>
                <p className="field-hint">Their products and services stay in the catalogue but become unassigned.</p>
                <div className="field">
                  <label>Your password (to confirm)</label>
                  <input type="password" required autoComplete="current-password" value={form.currentPassword} onChange={(e) => setForm({ ...form, currentPassword: e.target.value })} />
                </div>
                <div className="form-actions">
                  <button type="button" className="btn btn-outline" onClick={() => setModal(null)}>Cancel</button>
                  <button type="submit" className="btn btn-primary">Remove Account</button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
