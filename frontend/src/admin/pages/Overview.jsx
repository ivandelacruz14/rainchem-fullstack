import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import client from "../../api/client";
import { peso } from "../../utils/format";

export default function Overview() {
  const [data, setData] = useState(null);

  useEffect(() => {
    client.get("/api/admin/overview").then((res) => setData(res.data));
  }, []);

  if (!data) return null;
  const { stats, recentOrders, topFaqs } = data;
  const maxHits = Math.max(1, ...topFaqs.map((f) => f.hits));

  return (
    <div>
      <div className="admin-topbar">
        <div><h1>Dashboard Overview</h1><p>Live snapshot of your store, customers, and AI assistant.</p></div>
      </div>
      <div className="stat-grid">
        <div className="stat-box"><div className="label">Total Revenue</div><div className="value">{peso(stats.totalRevenue)}</div><div className="delta">{stats.orderCount} orders total</div></div>
        <div className="stat-box"><div className="label">Registered Users</div><div className="value">{stats.userCount}</div><div className="delta">{stats.verifiedUserCount} verified</div></div>
        <div className="stat-box"><div className="label">Products Listed</div><div className="value">{stats.productCount}</div><div className="delta">{stats.lowStockCount} low stock</div></div>
        <div className="stat-box"><div className="label">Pending KB Approvals</div><div className="value">{stats.pendingKnowledgeCount}</div><div className="delta">{stats.chatCount} chat interactions</div></div>
      </div>
      <div className="two-col">
        <div className="admin-panel">
          <div className="panel-head">
            <div><h3 style={{ margin: 0 }}>Recent Orders</h3><p style={{ margin: "2px 0 0", fontSize: 12.5, color: "#8a8580" }}>Latest 5 orders across all customers</p></div>
            <Link to="/admin/orders" className="btn btn-sm btn-outline">View All</Link>
          </div>
          <div className="table-wrap">
            <table className="admin-table">
              <thead><tr><th>Order</th><th>Customer</th><th>Total</th><th>Status</th></tr></thead>
              <tbody>
                {recentOrders.length === 0 ? (
                  <tr><td colSpan={4}>No orders yet.</td></tr>
                ) : (
                  recentOrders.map((o) => (
                    <tr key={o.id}>
                      <td className="mono">{o.orderNumber}</td>
                      <td>{o.customer.name}</td>
                      <td>{peso(o.total)}</td>
                      <td><span className={`status-pill status-${o.status}`}>{o.statusLabel}</span></td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
        <div className="admin-panel">
          <div className="panel-head"><div><h3 style={{ margin: 0 }}>Top Asked Questions</h3><p style={{ margin: "2px 0 0", fontSize: 12.5, color: "#8a8580" }}>Most frequently asked, all time</p></div></div>
          {topFaqs.length === 0 ? <p style={{ color: "#8a8580" }}>No questions asked yet.</p> : topFaqs.map((f) => (
            <div key={f.id} style={{ marginBottom: 14 }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, fontWeight: 600 }}>
                <span>{f.question}</span><span className="mono" style={{ color: "#8a8580" }}>{f.hits}</span>
              </div>
              <div className="hit-bar-track"><div className="hit-bar-fill" style={{ width: `${(f.hits / maxHits) * 100}%` }} /></div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
