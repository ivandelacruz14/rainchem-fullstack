import { Bar, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { peso } from "../../utils/format";

export default function SalesTrendChart({ series, granularity }) {
  const hasSales = series.some((point) => point.revenue > 0);
  if (!hasSales) return <p className="empty-state">No recorded sales in this period.</p>;

  const tickEvery = Math.max(0, Math.ceil(series.length / 8) - 1);
  return (
    <div className="chart-box">
      <ResponsiveContainer width="100%" height={300}>
        <ComposedChart data={series} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--line-strong)" />
          <XAxis dataKey="label" interval={tickEvery} tick={{ fontSize: 11, fill: "var(--soft)" }} />
          <YAxis yAxisId="money" width={52} tick={{ fontSize: 11, fill: "var(--soft)" }} tickFormatter={(v) => (v >= 1000 ? `${v / 1000}k` : v)} />
          <YAxis yAxisId="units" orientation="right" width={34} allowDecimals={false} tick={{ fontSize: 11, fill: "var(--soft)" }} />
          <Tooltip
            formatter={(value, name) => (name === "Revenue" ? peso(value) : value)}
            contentStyle={{ background: "var(--surface)", border: "1px solid var(--line-strong)", borderRadius: 8, color: "var(--ink)" }}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Bar yAxisId="money" dataKey="revenue" name="Revenue" fill="#b5121b" radius={[3, 3, 0, 0]} />
          <Line yAxisId="units" type="monotone" dataKey="units" name="Units sold" stroke="#f2b705" strokeWidth={2} dot={series.length <= 31} />
        </ComposedChart>
      </ResponsiveContainer>
      <p className="field-hint">Grouped {granularity}. Weeks start on Monday.</p>
    </div>
  );
}
