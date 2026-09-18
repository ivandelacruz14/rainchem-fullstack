import { useState, useEffect } from "react";
import client from "../../api/client";
import { formatDate } from "../../utils/format";

export default function Users() {
  const [summary, setSummary] = useState(null);
  const [revealed, setRevealed] = useState(false);
  const [users, setUsers] = useState([]);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState(null);

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
                <thead><tr><th>Name</th><th>Email</th><th>Phone</th><th>Status</th><th>Orders</th><th>Joined</th><th></th></tr></thead>
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
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
