import { peso } from "../../utils/format";

function Change({ value, previous, formatter }) {
  if (value === null || value === undefined) {
    return <div className="delta muted">No sales in the previous period to compare</div>;
  }
  const up = value >= 0;
  return (
    <div className={`delta ${up ? "up" : "down"}`}>
      {up ? "\u25B2" : "\u25BC"} {Math.abs(value)}% vs previous period ({formatter(previous)})
    </div>
  );
}

export default function SummaryCards({ report }) {
  const { summary, previous, change } = report;
  return (
    <div className="stat-grid">
      <div className="stat-box">
        <div className="label">Sales revenue</div>
        <div className="value">{peso(summary.revenue)}</div>
        <Change value={change.revenue} previous={previous.revenue} formatter={peso} />
      </div>
      <div className="stat-box">
        <div className="label">Products sold</div>
        <div className="value">{summary.units}</div>
        <Change value={change.units} previous={previous.units} formatter={(n) => `${n} units`} />
      </div>
      <div className="stat-box">
        <div className="label">Orders</div>
        <div className="value">{summary.orders}</div>
        <Change value={change.orders} previous={previous.orders} formatter={(n) => `${n} orders`} />
      </div>
      <div className="stat-box">
        <div className="label">Average order</div>
        <div className="value">{peso(summary.averageOrderValue)}</div>
        <div className="delta muted">Revenue per order</div>
      </div>
    </div>
  );
}
