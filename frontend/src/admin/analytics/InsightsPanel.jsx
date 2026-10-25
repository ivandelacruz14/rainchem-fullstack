import { useEffect, useState } from "react";
import client from "../../api/client";

const TYPE_LABELS = { restock: "Restock soon", prioritize: "Prioritize", promote: "Needs promotion" };
const TREND_LABELS = { up: "Rising", down: "Slowing", flat: "Steady" };

export default function InsightsPanel() {
  const [state, setState] = useState({ loading: true, error: false, data: null });

  useEffect(() => {
    client.get("/api/admin/analytics/insights")
      .then((res) => setState({ loading: false, error: false, data: res.data }))
      .catch(() => setState({ loading: false, error: true, data: null }));
  }, []);

  const { data } = state;
  const estimates = data ? data.products.filter((p) => p.status === "estimate") : [];

  return (
    <div className="admin-panel">
      <div className="panel-head">
        <div>
          <h3 style={{ margin: 0 }}>Recommendations and demand estimate</h3>
          <p className="field-hint" style={{ margin: "2px 0 0" }}>Estimated from past sales. These are not recorded sales and not guarantees.</p>
        </div>
      </div>

      {state.loading && <p className="field-hint">Working out estimates...</p>}
      {state.error && <div className="alert alert-error">Estimates could not be loaded.</div>}

      {data && (
        <>
          {!data.enoughHistory && (
            <div className="alert alert-info">
              Not enough sales history yet for estimates. {data.historyDays} day(s) of recorded sales so far; about a month is needed.
            </div>
          )}

          {data.suggestions.length > 0 && (
            <ul className="suggestion-list">
              {data.suggestions.map((s) => (
                <li key={`${s.type}-${s.productId}`} className={`suggestion ${s.type}`}>
                  <span className="suggestion-tag">{TYPE_LABELS[s.type]}</span>
                  <span>{s.message}</span>
                </li>
              ))}
            </ul>
          )}
          {data.enoughHistory && data.suggestions.length === 0 && <p className="field-hint">Nothing needs attention right now.</p>}

          {estimates.length > 0 && (
            <div className="table-wrap">
              <table className="admin-table stack">
                <thead><tr><th>Product</th><th>Trend</th><th>Est. per week</th><th>Est. next 30 days</th><th>Likely range</th><th>In stock</th><th>Stock lasts</th></tr></thead>
                <tbody>
                  {estimates.map((p) => (
                    <tr key={p.productId}>
                      <td data-label="Product" className="cell-name">{p.name}</td>
                      <td data-label="Trend">{TREND_LABELS[p.trend]}</td>
                      <td data-label="Est. per week">{p.estimatedWeeklyUnits}</td>
                      <td data-label="Est. next 30 days">{p.estimatedUnitsNext30Days} units</td>
                      <td data-label="Likely range">{p.estimateLow} to {p.estimateHigh}</td>
                      <td data-label="In stock">{p.stock}</td>
                      <td data-label="Stock lasts">{p.daysOfStock ? `~${Math.round(p.daysOfStock)} days` : "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <p className="field-hint">{data.method} {data.disclaimer}</p>
        </>
      )}
    </div>
  );
}
