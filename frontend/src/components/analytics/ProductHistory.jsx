import { useEffect, useState } from "react";
import client from "../../../api/client";
import { peso } from "../../../utils/format";
import TrendCharts from "./TrendCharts";

export default function ProductHistory({ productId, params, onClose }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setData(null);
    setError("");
    client.get(`/api/admin/analytics/products/${productId}/history`, { params })
      .then((res) => setData(res.data))
      .catch((err) => setError(err.response?.data?.error || "Could not load this product's history."));
  }, [productId, params]);

  return (
    <div className="admin-panel">
      <div className="panel-head">
        <h3 style={{ margin: 0 }}>{data ? `${data.product.name}: sales history` : "Product sales history"}</h3>
        <button type="button" className="btn btn-outline btn-sm" onClick={onClose}>Close</button>
      </div>
      {error && <div className="alert alert-error">{error}</div>}
      {!data && !error && <p className="field-hint">Loading...</p>}
      {data && (
        <>
          <p className="field-hint">
            {data.summary.unitsSold} units &middot; {peso(data.summary.revenue)} &middot; {data.summary.orders} orders in the selected range.
          </p>
          <TrendCharts series={data.series} />
        </>
      )}
    </div>
  );
}
