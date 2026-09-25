import { useEffect, useState } from "react";
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from "recharts";
import client from "../../api/client";
import { peso } from "../../utils/format";

const COLORS = ["#e1131f", "#f4a340", "#2e7d32", "#1565c0", "#8e24aa", "#00838f", "#6d4c41", "#c2185b"];

export default function Analytics() {
  const [data, setData] = useState(null);

  useEffect(() => {
    client.get("/api/admin/analytics/sales").then((res) => setData(res.data));
  }, []);

  if (!data) return <p>Loading...</p>;

  return (
    <div>
      <div className="admin-topbar">
        <div><h1>Sales Analytics</h1><p>Revenue and units sold per product.</p></div>
      </div>

     <div className="stat-grid" style={{ marginBottom: 24 }}>
  <div className="stat-box">
    <div className="label">Top Seller</div>
    <div className="value" style={{ fontSize: 18 }}>{data.topSeller?.name || "N/A"}</div>
    <div className="delta">{data.topSeller ? peso(data.topSeller.revenue) : ""}</div>
  </div>
  <div className="stat-box">
    <div className="label">Lowest Seller</div>
    <div className="value" style={{ fontSize: 18 }}>{data.lowestSeller?.name || "N/A"}</div>
    <div className="delta">{data.lowestSeller ? peso(data.lowestSeller.revenue) : ""}</div>
  </div>
</div>

      <div className="admin-panel">
        <h3>Revenue Share by Product</h3>
        <ResponsiveContainer width="100%" height={380}>
          <PieChart>
            <Pie data={data.products} dataKey="revenue" nameKey="name" outerRadius={140} label={(entry) => entry.name}>
              {data.products.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip formatter={(value) => peso(value)} />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </div>

      <div className="admin-panel" style={{ marginTop: 24 }}>
        <h3>Units Sold (High to Low)</h3>
        <table className="admin-table">
          <thead><tr><th>Product</th><th>Units Sold</th><th>Revenue</th></tr></thead>
          <tbody>
            {[...data.products].sort((a, b) => b.units - a.units).map((p) => (
              <tr key={p.name}><td>{p.name}</td><td>{p.units}</td><td>{peso(p.revenue)}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}