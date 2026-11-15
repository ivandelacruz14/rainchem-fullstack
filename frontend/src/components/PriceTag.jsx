import { peso } from "../utils/format";

// Regular price with a line through it, the sale price, and the percent off.
export default function PriceTag({ product, size = 18 }) {
  if (!product.onSale) {
    return <span className="product-price" style={{ fontSize: size }}>{peso(product.price)}</span>;
  }
  return (
    <span className="price-stack">
      <span className="product-price price-now" style={{ fontSize: size }}>{peso(product.salePrice)}</span>
      <s className="price-was" style={{ fontSize: Math.max(12, size * 0.66) }}>{peso(product.price)}</s>
      <span className="sale-badge">-{product.salePercent}%</span>
    </span>
  );
}
