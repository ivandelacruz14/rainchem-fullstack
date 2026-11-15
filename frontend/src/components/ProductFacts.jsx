import { useState } from "react";

/** Quick facts under the product photo, with a "See more" toggle for the full specification list. */
export default function ProductFacts({ product }) {
  const [open, setOpen] = useState(false);
  const rows = [
    ["Category", product.category || "-"],
    ["SKU", product.sku || "-"],
    ["Pieces per box", product.packSize ? String(product.packSize) : "Sold per piece"],
    ["Stock", product.stock > 0 ? `${product.stock} units available` : "Out of stock"],
  ];
  const specs = product.specs || [];
  return (
    <div className="pd-facts">
      <dl>
        {rows.map(([label, value]) => (
          <div className="pd-fact-row" key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
      {specs.length > 0 && (
        <>
          <button type="button" className="pd-more-btn" aria-expanded={open} onClick={() => setOpen((o) => !o)}>
            {open ? "See less \u25B4" : "See more \u25BE"}
          </button>
          {open && <ul className="pd-specs">{specs.map((s, i) => <li key={i}>{s}</li>)}</ul>}
        </>
      )}
    </div>
  );
}
