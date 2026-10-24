import { useEffect, useMemo, useState } from "react";
import client from "../../api/client";
import SummaryCards from "../components/analytics/SummaryCards";
import TrendCharts from "../components/analytics/TrendCharts";
import ProductTable from "../components/analytics/ProductTable";
import Recommendations from "../components/analytics/Recommendations";
import ForecastPanel from "../components/analytics/ForecastPanel";
import ProductHistory from "../components/analytics/ProductHistory";

const PERIODS = [
  { value: "daily", label: "Daily" },
  { value: "weekly", label: "Weekly" },
  { value: "monthly", label: "Monthly" },
];

export default function Analytics() {
  const [granularity, setGranularity] = useState("daily");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [report, setReport] = useState(null);
  const [error, setError] = useState("");
  const [historyId, setHistoryId] = useState(null);

  const params = useMemo(() => {
    const p = { granularity };
    if (start) p.start = start;
    if (end) p.end = end;
    return p;
  }, [granularity, start, end]);

  useEffect(() => {
    let cancelled = false;
    setError("");
    client.get("/api/admin/analytics/report", { params })
      .then((res) => { if (!cancelled) setReport(res.data); })
      .catch((err) => { if (!cancelled) setError(err.response?.data?.error || "Could not load the sales report."); });
    return () => { cancelled = true; };
  }, [params]);

  function changeGranularity(value) {
    setGranularity(value);
    setStart("");
    setEnd("");
  }

  return (
    <div>
      <div className="admin-topbar">
        <div>
          <h1>Sales Analytics</h1>
          <p>Recorded sales come from confirmed orders. Forecasts and recommendations are estimates based on them.</p>
        </div>
      </div>

      <div className="admin-panel filter-bar">
        <div className="tab-bar compact">
          {PERIODS.map((p) => (
            <button key={p.value} type="button" className={`tab-btn ${granularity === p.value ? "active" : ""}`} onClick={() => changeGranularity(p.value)}>
              {p.label}
            </button>
          ))}
        </div>
        <div className="date-filters">
          <label>From<input type="date" value={start || report?.range.start || ""} max={end || undefined} onChange={(e) => setStart(e.target.value)} /></label>
          <label>To<input type="date" value={end || report?.range.end || ""} min={start || undefined} onChange={(e) => setEnd(e.target.value)} /></label>
          {(start || end) && <button type="button" className="btn btn-outline btn-sm" onClick={() => { setStart(""); setEnd(""); }}>Reset</button>}
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {!report && !error && <p className="field-hint">Loading report...</p>}

      {report && (
        <>
          <p className="field-hint">
            Showing {report.range.start} to {report.range.end} ({report.range.days} days), compared with {report.previousRange.start} to {report.previousRange.end}. {report.basis}
          </p>
          <SummaryCards report={report} />

          <div className="admin-panel">
            <h3>Sales trend</h3>
            <TrendCharts series={report.series} />
          </div>

          <div className="admin-panel">
            <h3>Product performance (recorded)</h3>
            <ProductTable products={report.products} selectedId={historyId} onSelect={setHistoryId} />
          </div>

          {historyId && <ProductHistory productId={historyId} params={params} onClose={() => setHistoryId(null)} />}

          <div className="admin-panel">
            <h3>Recommendations <span className="badge">Based on recorded sales</span></h3>
            <Recommendations items={report.recommendations} />
          </div>

          <div className="admin-panel">
            <h3>Estimated future demand <span className="badge">Estimate</span></h3>
            <ForecastPanel forecast={report.forecast} />
          </div>
        </>
      )}
    </div>
  );
}
