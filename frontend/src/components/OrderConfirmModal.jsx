import { useEffect, useState } from "react";
import client from "../api/client";
import ProductVisual from "./ProductVisual";
import { peso } from "../utils/format";
import { priceLine } from "../utils/pricing";

export default function OrderConfirmModal({ product, initialQty = 1, mode = "cart", busy = false, onCancel, onConfirm }) {
  const [qty, setQty] = useState(initialQty); // always in pieces
  const [unit, setUnit] = useState("pcs");
  const [address, setAddress] = useState(null);
  const stock = Number(product.stock) || 0;
  const packSize = Number(product.packSize) || 0;
  const canUseBoxes = packSize > 1;
  const perUnit = unit === "boxes" && canUseBoxes ? packSize : 1;
  const shown = Math.max(1, Math.round(qty / perUnit));
  const maxShown = Math.max(1, Math.floor((stock || 1) / perUnit));
  const priced = priceLine(product.price, qty, product.salePercent);
  const isBuy = mode === "buy";
  const discounted = priced.rate > 0;
  const unitLabel = perUnit === 1 ? "pcs" : shown === 1 ? "box" : "boxes";

  useEffect(() => {
    if (!isBuy) return;
    client.get("/api/addresses")
      .then((res) => {
        const list = res.data.addresses || [];
        setAddress(list.find((a) => a.isDefault) || list[0] || null);
      })
      .catch(() => {});
  }, [isBuy]);

  function setShown(n) {
    const value = Math.min(Math.max(1, n), maxShown);
    setQty(value * perUnit);
  }

  return (
    <div className="overlay confirm-overlay" onClick={(e) => { e.stopPropagation(); onCancel(); }}>
      <div className="modal confirm-modal" role="dialog" aria-modal="true"
        aria-label={isBuy ? "Confirm your order" : "Confirm add to cart"} onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h3 style={{ margin: 0 }}>{isBuy ? "Confirm your order" : "Confirm add to cart"}</h3>
          <button type="button" className="modal-close" onClick={onCancel} aria-label="Close">&times;</button>
        </div>
        <div className="modal-body">
          <div className="confirm-item">
            <div className="confirm-thumb"><ProductVisual product={product} widthPercent={100} /></div>
            <div className="confirm-info">
              <strong>{product.name}</strong>
              <div className="confirm-unit">
                <span>Unit price</span>
                <span className="confirm-unit-price">{peso(priced.unitPrice)}</span>
              </div>
              {discounted && (
                <div className="confirm-discount">
                  {Math.round(priced.rate * 100)}% discount applied (regular {peso(product.price)} each)
                </div>
              )}
            </div>
          </div>

          <div className="confirm-qty">
            <span className="confirm-qty-label">Quantity{stock ? ` · ${stock} available` : ""}</span>
            <div className="qty-stepper">
              <button type="button" aria-label="Decrease" onClick={() => setShown(shown - 1)} disabled={shown <= 1}>−</button>
              <span className="qty-stepper-value" aria-live="polite">{shown} {unitLabel}</span>
              <button type="button" aria-label="Increase" onClick={() => setShown(shown + 1)} disabled={shown >= maxShown}>+</button>
            </div>
          </div>
          {canUseBoxes && (
            <div className="confirm-qty">
              <div className="unit-toggle" role="group" aria-label="Count in">
                <button type="button" className={unit === "pcs" ? "active" : ""} onClick={() => { setUnit("pcs"); setQty(shown); }}>Pieces</button>
                <button type="button" className={unit === "boxes" ? "active" : ""} onClick={() => { setUnit("boxes"); setQty(shown * packSize); }}>Boxes</button>
              </div>
              <span className="field-hint">1 box = {packSize} pcs · total {qty} pcs</span>
            </div>
          )}

          <div className="confirm-row confirm-subtotal">
            <span>Subtotal</span>
            <strong>{peso(priced.lineTotal)}</strong>
          </div>

          {isBuy && (
            <>
              <div className="confirm-row">
                <span>Deliver to</span>
                <span>{address ? address.formatted : "Choose your delivery address at checkout"}</span>
              </div>
              <div className="confirm-row">
                <span>Payment</span>
                <span>Cash on Delivery or GCash, chosen at checkout</span>
              </div>
            </>
          )}

          <div className="form-actions">
            <button type="button" className="btn btn-outline" onClick={onCancel} disabled={busy}>Cancel</button>
            <button type="button" className="btn btn-primary" disabled={busy || stock === 0 || qty < 1}
              onClick={() => onConfirm(qty)}>
              {busy ? "Please wait..." : isBuy ? "Confirm and continue" : "Confirm"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
