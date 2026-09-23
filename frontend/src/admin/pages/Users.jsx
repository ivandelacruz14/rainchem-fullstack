import { useState, useEffect } from "react";
import client from "../../api/client";
import { formatDate } from "../../utils/format";

export default function Users() {
  const [summary, setSummary] = useState(null);
  const [revealed, setRevealed] = useState(false);
  const [users, setUsers] = useState([]);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    setRevealed(false);
    client.get("/api/admin/users/summary").then((res) => setSummary(res.data));
  }, []);

  useEffect(() => {
    if (revealed) {
      client.get("/api/admin/users", { params: { search } }).then((res) => setUsers(res.data.users));
    }
  }, [revealed, search]);

  async function openDetail(userId) {
    const res = await client.get(`/api/admin/users/${userId}`);
    setSelected(res.data.user);
  }

  async function deleteUser(userId) {
    setDeleting(true);
    try {
      await client.delete(`/api/admin/users/${userId}`);
      setUsers((prev) => prev.filter((u) => u.id !== userId));
      setConfirmDelete(null);
      setSelected(null);
      setSummary((prev) => prev && { ...prev, total: prev.total - 1 });
    } catch (err) {
      alert(err?.response?.data?.error || "Could not delete this account. Please try again.");
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div>
      <div className="admin-topbar"><div><h1>Users</h1><p>Registered storefront customers. Customer details stay hidden until you choose to view them.</p></div></div>

      <div className="admin-panel">
        {!revealed ? (
          <div style={{ textAlign: "center", padding: "36px 20px" }}>
            <h3 style={{ marginBottom: 6 }}>Customer data is hidden by default</h3>
            <p style={{ color: "#8a8580", fontSize: 13.5, maxWidth: 420, margin: "0 auto 18px" }}>
              There are <strong>{summary?.total ?? "..."}</strong> registered accounts ({summary?.verified ?? "..."} verified).
              Names, emails, and phone numbers are only shown after you choose to view them here.
            </p>
            <button className="btn btn-primary" onClick={() => setRevealed(true)}>Show Customer List</button>
          </div>
        ) : (
          <>
            <div className="panel-head">
              <div className="search-input">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="8" /><path d="m21 21-4.3-4.3" /></svg>
                <input placeholder="Search users..." value={search} onChange={(e) => setSearch(e.target.value)} />
              </div>
              <button className="btn btn-sm btn-outline" onClick={() => setRevealed(false)}>Hide Customer List</button>
            </div>
            <div className="table-wrap">
              <table className="admin-table">
                <thead><tr><th>Name</th><th>Email</th><th>Phone</th><th>Status</th><th>Orders</th><th>Joined</th><th></th><th></th></tr></thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id}>
                      <td style={{ fontWeight: 600 }}>{u.name}</td>
                      <td>{u.email}</td>
                      <td>{u.phone || "-"}</td>
                      <td><span className={`pill ${u.verified ? "pill-approved" : "pill-pending"}`}>{u.verified ? "Verified" : "Unverified"}</span></td>
                      <td>{u.orderCount}</td>
                      <td>{formatDate(u.createdAt).split(",")[0]}</td>
                      <td><button className="icon-action" onClick={() => openDetail(u.id)}>View</button></td>
                      <td><button className="icon-action" style={{ color: "#c0392b" }} onClick={() => setConfirmDelete(u)}>Delete</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>

      {selected && (
        <div className="overlay" onClick={() => setSelected(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head"><h3 style={{ margin: 0 }}>User Detail</h3><button className="modal-close" onClick={() => setSelected(null)}>&times;</button></div>
            <div className="modal-body">
              <h3 style={{ margin: "0 0 4px" }}>{selected.name}</h3>
              <p style={{ color: "#8a8580", fontSize: 13.5 }}>{selected.email} &middot; {selected.phone || "No phone on file"}</p>
              <span className={`pill ${selected.verified ? "pill-approved" : "pill-pending"}`}>{selected.verified ? "Verified" : "Unverified"}</span>
              <h4 style={{ margin: "18px 0 8px" }}>Order History ({selected.orders.length})</h4>
              {selected.orders.length === 0 ? (
                <p style={{ color: "#8a8580", fontSize: 13.5 }}>No orders placed yet, this customer has not purchased anything through the storefront.</p>
              ) : (
                selected.orders.map((o) => (
                  <div className="cart-summary-row" key={o.id}><span className="mono">{o.orderNumber}</span><span>{o.statusLabel}</span></div>
                ))
              )}
              <div style={{ marginTop: 18, paddingTop: 14, borderTop: "1px solid #eee" }}>
                <button className="btn btn-sm" style={{ background: "#c0392b", color: "#fff" }} onClick={() => setConfirmDelete(selected)}>
                  Delete Account
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {confirmDelete && (
        <div className="overlay" onClick={() => !deleting && setConfirmDelete(null)}>
          <div className="modal" style={{ maxWidth: 380 }} onClick={(e) => e.stopPropagation()}>
            <div className="modal-head"><h3 style={{ margin: 0 }}>Delete this account?</h3></div>
            <div className="modal-body">
              <p style={{ fontSize: 13.5, color: "#4a4540" }}>
                This will permanently delete <strong>{confirmDelete.name}</strong> ({confirmDelete.email}).
                This cannot be undone, and they will need to register again with a fresh account.
              </p>
              <div style={{ display: "flex", gap: 10, marginTop: 18, justifyContent: "flex-end" }}>
                <button className="btn btn-sm btn-outline" disabled={deleting} onClick={() => setConfirmDelete(null)}>Cancel</button>
                <button
                  className="btn btn-sm"
                  style={{ background: "#c0392b", color: "#fff" }}
                  disabled={deleting}
                  onClick={() => deleteUser(confirmDelete.id)}
                >
                  {deleting ? "Deleting..." : "Yes, Delete"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
