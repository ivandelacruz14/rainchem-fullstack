import { peso } from "../../../utils/format";

function change(value) {
  if (value === null || value === undefined) return "n/a";
  return `${value > 0 ? "+" : ""}${value}%`;
}

export default function ProductTable({ products, selectedId, onSelect }) {
  return (
    <div className="table-wrap">
      <table className="admin-table">
        <thead>
          <tr><th>Product</th><th>Units</th><th>Revenue</th><th>Share</th><th>Prev. units</th><th>Change</th><th>Stock</th><th></th></tr>
        </thead>
        <tbody>
          {products.length === 0 && <tr><td colSpan={8}>No products.</td></tr>}
          {products.map((p) => (
            <tr key={p.productId ?? p.name} className={p.productId === selectedId ? "row-selected" : ""}>
              <td className="strong wrap-cell">{p.name}</td>
              <td>{p.units}</td>
              <td>{peso(p.revenue)}</td>
              <td>{p.share}%</td>
              <td>{p.previousUnits}</td>
              <td>{change(p.unitsChange)}</td>
              <td>{p.stock ?? "n/a"}</td>
              <td>
                {p.productId && <button type="button" className="icon-action" onClick={() => onSelect(p.productId)}>History</button>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
