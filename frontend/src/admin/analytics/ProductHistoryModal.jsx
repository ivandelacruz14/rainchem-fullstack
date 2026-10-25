import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import client from "../../api/client";
import { peso } from "../../utils/format";

export default function ProductHistoryModal({ product, filters, onClose }) {
  const [granularity, setGranularity] = useState(filters.granularity === "daily" ? "weekly" : filters.granularity);
  const [state, setState] = useState({ loading: true, error: "", data: null });

  useEffect(() => {
    let cancelled = false;
    setState({ loading: true, error: "", data: null });
    client.get(`/api/admin/analytics/products/${product.productId}/history`, {
      params: { start: filters.start, end: filters.end, granularity },
    })
      .then((res) => { if (!cancelled) setState({ loading: false, error: "", data: res.data }); })
      .catch((err) => { if (!cancelled) setState({ loading: false, error: err.response?.data?.error || "Could not load the history.", data: null }); });
    return () => { cancelled = true; };
  }, [product.productId, filters.start, filters.end, granularity]);

  const { data } = state;

  return (
    <div className="overlay" onClick={onClose}>
      <div className="modal wide" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h3 style={{ margin: 0 }}>{product.name}</h3>
          <button type="button" className="modal-close" onClick={onClose}>&times;</button>
        </div>
        <div className="modal-body">
          <p className="field-hint">Recorded sales from {filters.start} to {filters.end}.</p>
          <div className="field" style={{ maxWidth: 200 }}>
            <label htmlFor="history-group">Group by</label>
            <select id="history-group" value={granularity} onChange={(e) => setGranularity(e.target.value)}>
              <option value="daily">Day</option>
              <option value="weekly">Week</option>
              <option value="monthly">Month</option>
            </select>
          </div>
          {state.loading && <p className="field-hint">Loading...</p>}
          {state.error && <div className="alert alert-error">{state.error}</div>}
          {data && (
            <>
              <p><strong>{data.summary.units}</strong> units &middot; <strong>{peso(data.summary.revenue)}</strong> &middot; {data.summary.orders} orders</p>
              {data.summary.units === 0 ? <p className="empty-state">No recorded sales of this product in the period.</p> : (
                <div className="chart-box">
                  <ResponsiveContainer width="100%" height={240}>
                    <BarChart data={data.series} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--line-strong)" />
                      <XAxis dataKey="label" interval={Math.max(0, Math.ceil(data.series.length / 6) - 1)} tick={{ fontSize: 11, fill: "var(--soft)" }} />
                      <YAxis allowDecimals={false} width={30} tick={{ fontSize: 11, fill: "var(--soft)" }} />
                      <Tooltip contentStyle={{ background: "var(--surface)", border: "1px solid var(--line-strong)", borderRadius: 8, color: "var(--ink)" }} />
                      <Bar dataKey="units" name="Units" fill="#b5121b" radius={[3, 3, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
              <div className="table-wrap">
                <table className="admin-table">
                  <thead><tr><th>Period</th><th>Units</th><th>Orders</th><th>Revenue</th></tr></thead>
                  <tbody>
                    {data.series.map((row) => (
                      <tr key={row.start}><td>{row.label}</td><td>{row.units}</td><td>{row.orders}</td><td>{peso(row.revenue)}</td></tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
