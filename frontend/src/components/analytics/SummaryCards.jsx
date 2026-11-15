import { peso } from "../../../utils/format";

function Change({ value }) {
  if (value === null || value === undefined) return <div className="delta muted">No earlier sales to compare</div>;
  const up = value >= 0;
  return <div className={`delta ${up ? "up" : "down"}`}>{up ? "+" : ""}{value}% vs previous period</div>;
}

export default function SummaryCards({ report }) {
  const { summary, change, bestSeller, lowestSeller } = report;
  return (
    <div className="stat-grid">
      <div className="stat-box"><div className="label">Revenue</div><div className="value">{peso(summary.revenue)}</div><Change value={change.revenue} /></div>
      <div className="stat-box"><div className="label">Products sold</div><div className="value">{summary.unitsSold}</div><Change value={change.unitsSold} /></div>
      <div className="stat-box"><div className="label">Orders</div><div className="value">{summary.orders}</div><Change value={change.orders} /></div>
      <div className="stat-box"><div className="label">Avg. order value</div><div className="value">{peso(summary.averageOrderValue)}</div></div>
      <div className="stat-box wide">
        <div className="label">Best seller</div>
        <div className="value small">{bestSeller ? bestSeller.name : "No sales in this period"}</div>
        {bestSeller && <div className="delta muted">{bestSeller.units} units &middot; {peso(bestSeller.revenue)}</div>}
      </div>
      <div className="stat-box wide">
        <div className="label">Lowest seller (with sales)</div>
        <div className="value small">{lowestSeller ? lowestSeller.name : "Not enough products sold"}</div>
        {lowestSeller && <div className="delta muted">{lowestSeller.units} units &middot; {peso(lowestSeller.revenue)}</div>}
      </div>
    </div>
  );
}
