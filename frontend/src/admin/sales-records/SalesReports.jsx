import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import client from "../../api/client";
import { isoDay, presetRange } from "../analytics/useSalesReport";
import { peso } from "../../utils/format";

export default function SalesReports() {
  const [filters, setFilters] = useState({ ...presetRange("30d"), granularity: "daily" });
  const [state, setState] = useState({ loading: true, error: "", data: null });

  useEffect(() => {
    let cancelled = false;
    setState((p) => ({ ...p, loading: true, error: "" }));
    client.get("/api/admin/sales-records/summary", { params: { from: filters.start, to: filters.end, granularity: filters.granularity } })
      .then((res) => { if (!cancelled) setState({ loading: false, error: "", data: res.data }); })
      .catch((err) => { if (!cancelled) setState({ loading: false, error: err.response?.data?.error || "The report could not be loaded.", data: null }); });
    return () => { cancelled = true; };
  }, [filters.start, filters.end, filters.granularity]);

  const { data } = state;
  const s = data?.summary;
  const set = (patch) => setFilters((p) => ({ ...p, ...patch }));

  return (
    <div>
      <div className="admin-panel filter-panel">
        <div className="chip-row">
          {[["7d", "Last 7 days"], ["30d", "Last 30 days"], ["month", "This month"], ["90d", "Last 90 days"]].map(([key, label]) => (
            <button key={key} type="button" className="chip" onClick={() => set(presetRange(key))}>{label}</button>
          ))}
        </div>
        <div className="filter-fields">
          <div className="field"><label htmlFor="rep-from">From</label><input id="rep-from" type="date" value={filters.start} max={filters.end} onChange={(e) => set({ start: e.target.value })} /></div>
          <div className="field"><label htmlFor="rep-to">To</label><input id="rep-to" type="date" value={filters.end} min={filters.start} max={isoDay(new Date())} onChange={(e) => set({ end: e.target.value })} /></div>
          <div className="field"><label htmlFor="rep-group">Report</label>
            <select id="rep-group" value={filters.granularity} onChange={(e) => set({ granularity: e.target.value })}>
              <option value="daily">Daily</option><option value="weekly">Weekly</option><option value="monthly">Monthly</option>
            </select></div>
        </div>
      </div>

      {state.error && <div className="alert alert-error">{state.error}</div>}
      {state.loading && !data && <p className="field-hint">Loading report...</p>}

      {data && (
        <div className={state.loading ? "is-loading" : ""}>
          <div className="stat-grid">
            <div className="stat-box"><div className="label">Total recorded</div><div className="value">{s.recordedRows}</div><div className="delta muted">{peso(s.recordedValue)} across all states</div></div>
            <div className="stat-box"><div className="label">Completed sales</div><div className="value">{s.completedRows}</div><div className="delta muted">{peso(s.completedValue)} &middot; {s.units} units</div></div>
            <div className="stat-box"><div className="label">Gross sales</div><div className="value">{peso(s.grossSales)}</div><div className="delta muted">Before discounts</div></div>
            <div className="stat-box"><div className="label">Discounts</div><div className="value">{peso(s.discounts)}</div></div>
            <div className="stat-box"><div className="label">Refunds and returns</div><div className="value">{peso(s.refunds)}</div><div className="delta muted">{s.refundedRows} line(s)</div></div>
            <div className="stat-box"><div className="label">Net sales</div><div className="value">{peso(s.netSales)}</div><div className="delta muted">Not profit</div></div>
            <div className="stat-box"><div className="label">Pending (unpaid)</div><div className="value">{s.pendingRows}</div><div className="delta muted">{peso(s.pendingValue)} not counted yet</div></div>
            <div className="stat-box"><div className="label">Cancelled</div><div className="value">{s.cancelledRows}</div><div className="delta muted">{peso(s.cancelledValue)}</div></div>
          </div>
          <div className="admin-panel">
            <h3>Net sales trend</h3>
            {data.series.some((p) => p.netSales > 0) ? (
              <div className="chart-box">
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={data.series} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--line-strong)" />
                    <XAxis dataKey="label" interval={Math.max(0, Math.ceil(data.series.length / 8) - 1)} tick={{ fontSize: 11, fill: "var(--soft)" }} />
                    <YAxis width={52} tick={{ fontSize: 11, fill: "var(--soft)" }} tickFormatter={(v) => (v >= 1000 ? `${v / 1000}k` : v)} />
                    <Tooltip formatter={(v) => peso(v)} contentStyle={{ background: "var(--surface)", border: "1px solid var(--line-strong)", borderRadius: 8, color: "var(--ink)" }} />
                    <Bar dataKey="netSales" name="Net sales" fill="#b5121b" radius={[3, 3, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : <p className="empty-state">No completed sales in this period.</p>}
          </div>
          <div className="two-col">
            <div className="admin-panel"><h3>Best-selling products</h3>
              {data.bestSelling.length === 0 ? <p className="field-hint">No completed sales yet.</p> : (
                <ol className="rank-list">{data.bestSelling.map((p) => <li key={p.name}><span className="rank-name">{p.name}</span><span className="rank-value">{p.units} sold &middot; {peso(p.net)}</span></li>)}</ol>
              )}
            </div>
            <div className="admin-panel"><h3>Products with declining sales</h3>
              <p className="field-hint" style={{ marginTop: 0 }}>Compared with {data.range.previousStart} to {data.range.previousEnd}.</p>
              {data.declining.length === 0 ? <p className="field-hint">No product sold less than before.</p> : (
                <ol className="rank-list">{data.declining.map((p) => <li key={p.name}><span className="rank-name">{p.name}</span><span className="rank-value">{p.previousUnits} &rarr; {p.units} units ({p.changePercent}%)</span></li>)}</ol>
              )}
            </div>
          </div>
          <p className="field-hint">
            <strong>Completed:</strong> {data.definitions.completed} <strong>Gross sales:</strong> {data.definitions.grossSales} <strong>Net sales:</strong> {data.definitions.netSales}
          </p>
        </div>
      )}
    </div>
  );
}
