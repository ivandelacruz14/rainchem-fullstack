import { peso } from "../../../utils/format";

export default function ForecastPanel({ forecast }) {
  const estimated = forecast.products.filter((p) => p.sufficientData);
  const waiting = forecast.products.filter((p) => !p.sufficientData);

  return (
    <div>
      <div className="alert alert-info">
        <strong>Estimate, not recorded sales.</strong> {forecast.method} It is not a guarantee.
      </div>
      {estimated.length === 0 ? (
        <p className="field-hint">There is not enough sales history yet to estimate demand for any product.</p>
      ) : (
        <>
          <p className="field-hint">Estimated revenue for the next {forecast.horizonWeeks} weeks across these products: <strong>{peso(forecast.expectedRevenue)}</strong></p>
          <div className="table-wrap">
            <table className="admin-table">
              <thead><tr><th>Product</th><th>Est. units ({forecast.horizonWeeks} wks)</th><th>Likely range</th><th>In stock</th><th>Confidence</th><th>Note</th></tr></thead>
              <tbody>
                {estimated.map((p) => (
                  <tr key={p.productId}>
                    <td className="strong wrap-cell">{p.name}</td>
                    <td>{p.expectedUnits}</td>
                    <td>{p.lowUnits} to {p.highUnits}</td>
                    <td>{p.stock}</td>
                    <td>{p.confidence}</td>
                    <td>{p.needsRestock ? <span className="pill pill-low">May need restocking</span> : "Stock covers estimate"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
      {waiting.length > 0 && (
        <p className="field-hint">Not enough history to estimate: {waiting.map((p) => p.name).join(", ")}.</p>
      )}
    </div>
  );
}
