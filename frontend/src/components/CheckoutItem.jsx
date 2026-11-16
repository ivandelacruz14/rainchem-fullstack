import ProductVisual from "./ProductVisual";
import QtyInput from "./QtyInput";
import { useCart } from "../context/CartContext";
import { peso } from "../utils/format";

/** One item on the checkout page: photo, name (opens the product details), key facts, quantity, and line total. */
export default function CheckoutItem({ line, onOpen }) {
  const { setQty, removeItem } = useCart();
  const p = line.product;
  const each = line.qty ? line.lineTotal / line.qty : 0;
  const packSize = Number(p.packSize) || 0;
  const discounted = line.discountRate > 0;

  return (
    <div className="checkout-item">
      <button type="button" className="checkout-item-thumb" onClick={() => onOpen(p)} aria-label={`View details of ${p.name}`}>
        <ProductVisual product={p} widthPercent={100} />
      </button>
      <div className="checkout-item-info">
        <button type="button" className="checkout-item-name" onClick={() => onOpen(p)}>{p.name}</button>
        <div className="checkout-item-tags">
          {p.category && <span className="checkout-tag">{p.category}</span>}
          {packSize > 1 && <span className="checkout-tag">1 box = {packSize} pcs</span>}
          {p.stock !== undefined && <span className="checkout-tag">{p.stock} in stock</span>}
          {discounted && <span className="checkout-tag checkout-tag-ok">{Math.round(line.discountRate * 100)}% off</span>}
        </div>
        <div className="checkout-item-price">
          {peso(each)} each
          {discounted && <s className="checkout-item-was">{peso(p.price)}</s>}
        </div>
        <div className="checkout-item-controls">
          <QtyInput value={line.qty} onCommit={(pcs) => setQty(p.id, pcs)} max={Number(p.stock) || null} packSize={p.packSize} />
          <button type="button" className="checkout-item-remove" onClick={() => removeItem(p.id)}>Remove</button>
        </div>
      </div>
      <div className="checkout-item-total">{peso(line.lineTotal)}</div>
    </div>
  );
}
