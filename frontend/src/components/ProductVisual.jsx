const ICONS = {
  bottle: (
    <svg viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M9 2h6v3.5l2 2V20a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2V7.5l2-2V2Z" />
      <path d="M7 12h10" />
    </svg>
  ),
  drop: (
    <svg viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M12 2s7 8.2 7 13a7 7 0 0 1-14 0c0-4.8 7-13 7-13Z" />
    </svg>
  ),
  filter: (
    <svg viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M4 4h16l-6 8v6l-4 2v-8L4 4Z" />
    </svg>
  ),
  disc: (
    <svg viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" strokeWidth="1.8">
      <circle cx="12" cy="12" r="9" />
      <circle cx="12" cy="12" r="3" />
      <path d="M12 3v3M12 18v3M3 12h3M18 12h3" />
    </svg>
  ),
  wrench: (
    <svg viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18l3 3 6.3-6.3a4 4 0 0 0 5.4-5.4l-2.8 2.8-2-2 2.8-2.8Z" />
    </svg>
  ),
  gauge: (
    <svg viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z" />
      <path d="M12 12 16 8" />
    </svg>
  ),
};

const GLYPH_MAP = {
  "oil-synthetic": "bottle", "oil-semi": "bottle", "coolant-red": "drop", "coolant-ready": "drop",
  "chain-lube": "wrench", "oil-filter": "filter", "air-filter": "filter", "brake-pads": "disc",
  "brake-fluid": "bottle", "service-oil": "gauge", "service-coolant": "gauge", "spark-plug": "wrench",
};

export function CategoryIcon({ category }) {
  const map = {
    "Oils & Fluids": "bottle", Coolant: "drop", Filters: "filter",
    Brakes: "disc", Accessories: "wrench", Services: "gauge",
  };
  return <div style={{ width: 22, height: 22 }}>{ICONS[map[category] || "bottle"]}</div>;
}

export default function ProductVisual({ product, widthPercent = 56 }) {
  if (product.imagePhoto) {
    return <img src={product.imagePhoto} alt={product.name} />;
  }
  const key = GLYPH_MAP[product.imageGlyph] || "bottle";
  return (
    <div style={{ width: `${widthPercent}%`, color: "var(--red-700)" }}>
      {ICONS[key]}
    </div>
  );
}
