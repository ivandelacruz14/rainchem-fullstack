import { useState } from "react";
import InsightsPanel from "../analytics/InsightsPanel";
import ProductHistoryModal from "../analytics/ProductHistoryModal";
import ProductSales from "../analytics/ProductSales";
import SalesFilters from "../analytics/SalesFilters";
import SalesTrendChart from "../analytics/SalesTrendChart";
import SummaryCards from "../analytics/SummaryCards";
import useSalesReport, { presetRange } from "../analytics/useSalesReport";

export default function Analytics() {
  const [filters, setFilters] = useState({ ...presetRange("30d"), granularity: "daily" });
  const [historyFor, setHistoryFor] = useState(null);
  const { loading, error, data } = useSalesReport(filters);

  function change(patch) {
    setFilters((prev) => ({ ...prev, ...patch }));
  }

  return (
    <div>
      <div className="admin-topbar">
        <div>
          <h1>Sales Analytics</h1>
          <p>Daily, weekly and monthly sales from recorded orders.</p>
        </div>
      </div>

      <SalesFilters filters={filters} onChange={change} onPreset={(key) => change(presetRange(key))} />

      {error && <div className="alert alert-error">{error}</div>}
      {loading && !data && <p className="field-hint">Loading report...</p>}

      {data && (
        <div className={loading ? "is-loading" : ""}>
          <p className="field-hint basis-note">{data.basis}</p>
          <SummaryCards report={data} />
          <div className="admin-panel">
            <h3>Sales trend</h3>
            <SalesTrendChart series={data.series} granularity={data.range.granularity} />
          </div>
          <ProductSales report={data} onOpenHistory={setHistoryFor} />
        </div>
      )}

      <InsightsPanel />

      {historyFor && <ProductHistoryModal product={historyFor} filters={filters} onClose={() => setHistoryFor(null)} />}
    </div>
  );
}
