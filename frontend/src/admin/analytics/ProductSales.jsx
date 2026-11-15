import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { peso } from "../../utils/format";

function Change({ value }) {
  if (value === null || value === undefined) return <span className="muted">n/a</span>;
  return <span className={value >= 0 ? "delta up" : "delta down"}>{value >= 0 ? "+" : ""}{value}%</span>;
}

function RankList({ title, rows, empty }) {
  return (
    <div className="admin-panel">
      <h3>{title}</h3>
      {rows.length === 0 ? <p className="field-hint">{empty}</p> : (
        <ol className="rank-list">
          {rows.map((row) => (
            <li key={`${row.productId}-${row.name}`}>
              <span className="rank-name">{row.name}</span>
              <span className="rank-value">{row.units} sold &middot; {peso(row.revenue)}</span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

export default function ProductSales({ report, onOpenHistory }) {
  const top = report.products.filter((p) => p.units > 0).slice(0, 8).map((p) => ({ name: p.name.length > 24 ? `${p.name.slice(0, 23)}...` : p.name, units: p.units }));

  return (
    <>
      <div className="two-col">
        <RankList title="Best selling" rows={report.bestSelling} empty="No sales in this period yet." />
        <RankList title="Lowest selling" rows={report.lowestSelling} empty="No products to compare." />
      </div>

      {top.length > 0 && (
        <div className="admin-panel">
          <h3>Units sold by product</h3>
          <div className="chart-box">
            <ResponsiveContainer width="100%" height={Math.max(200, top.length * 38)}>
              <BarChart data={top} layout="vertical" margin={{ top: 0, right: 12, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--line-strong)" horizontal={false} />
                <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11, fill: "var(--soft)" }} />
                <YAxis type="category" dataKey="name" width={110} tick={{ fontSize: 11, fill: "var(--ink)" }} />
                <Tooltip contentStyle={{ background: "var(--surface)", border: "1px solid var(--line-strong)", borderRadius: 8, color: "var(--ink)" }} />
                <Bar dataKey="units" name="Units" fill="#b5121b" radius={[0, 3, 3, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      <div className="admin-panel">
        <h3>All products</h3>
        <p className="field-hint">Compared with the previous period of the same length ({report.range.previousStart} to {report.range.previousEnd}).</p>
        <div className="table-wrap">
          <table className="admin-table stack">
            <thead>
              <tr><th>Product</th><th>Units</th><th>Revenue</th><th>Share</th><th>Units vs previous</th><th>Stock</th><th></th></tr>
            </thead>
            <tbody>
              {report.products.map((p) => (
                <tr key={`${p.productId}-${p.name}`}>
                  <td data-label="Product" className="cell-name">{p.name}{p.discontinued && <span className="muted"> (removed)</span>}</td>
                  <td data-label="Units">{p.units}</td>
                  <td data-label="Revenue">{peso(p.revenue)}</td>
                  <td data-label="Share">{p.revenueShare}%</td>
                  <td data-label="Units vs previous"><Change value={p.unitsChange} /> <span className="muted">({p.previousUnits})</span></td>
                  <td data-label="Stock">{p.stock ?? "-"}</td>
                  <td data-label="" className="row-cell">
                    {p.productId && <button type="button" className="icon-action wide" onClick={() => onOpenHistory(p)}>History</button>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
