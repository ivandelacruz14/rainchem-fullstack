import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { peso } from "../../../utils/format";

const AXIS = { fontSize: 11, fill: "var(--soft)" };

export default function TrendCharts({ series }) {
  if (!series.some((point) => point.orders > 0)) {
    return <p className="field-hint">No recorded sales in this period, so there is no trend to draw.</p>;
  }
  return (
    <div className="chart-grid">
      <div>
        <h4 className="chart-title">Revenue</h4>
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={series} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" />
            <XAxis dataKey="label" tick={AXIS} interval="preserveStartEnd" minTickGap={16} />
            <YAxis tick={AXIS} width={52} tickFormatter={(v) => (v >= 1000 ? `${Math.round(v / 1000)}k` : v)} />
            <Tooltip formatter={(value) => peso(value)} />
            <Bar dataKey="revenue" name="Revenue" fill="#e1131f" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div>
        <h4 className="chart-title">Products sold</h4>
        <ResponsiveContainer width="100%" height={240}>
          <LineChart data={series} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" />
            <XAxis dataKey="label" tick={AXIS} interval="preserveStartEnd" minTickGap={16} />
            <YAxis tick={AXIS} width={36} allowDecimals={false} />
            <Tooltip />
            <Line type="monotone" dataKey="units" name="Units" stroke="#1565c0" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
