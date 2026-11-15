const PRESETS = [
  { key: "7d", label: "Last 7 days" },
  { key: "30d", label: "Last 30 days" },
  { key: "month", label: "This month" },
  { key: "90d", label: "Last 90 days" },
];

export default function SalesFilters({ filters, onChange, onPreset }) {
  return (
    <div className="admin-panel filter-panel">
      <div className="chip-row">
        {PRESETS.map((p) => (
          <button key={p.key} type="button" className="chip" onClick={() => onPreset(p.key)}>{p.label}</button>
        ))}
      </div>
      <div className="filter-fields">
        <div className="field">
          <label htmlFor="sales-from">From</label>
          <input id="sales-from" type="date" value={filters.start} max={filters.end} onChange={(e) => onChange({ start: e.target.value })} />
        </div>
        <div className="field">
          <label htmlFor="sales-to">To</label>
          <input id="sales-to" type="date" value={filters.end} min={filters.start} onChange={(e) => onChange({ end: e.target.value })} />
        </div>
        <div className="field">
          <label htmlFor="sales-group">Report</label>
          <select id="sales-group" value={filters.granularity} onChange={(e) => onChange({ granularity: e.target.value })}>
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
            <option value="monthly">Monthly</option>
          </select>
        </div>
      </div>
    </div>
  );
}
