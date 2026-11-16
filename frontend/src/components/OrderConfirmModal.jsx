import { useEffect, useState } from "react";
import client from "../api/client";
import QtyInput from "./QtyInput";
import ProductVisual from "./ProductVisual";
import { peso } from "../utils/format";
import { priceLine } from "../utils/pricing";

/**
 * Confirms a purchase before anything is added or ordered. Shows the product, the actual unit price, the quantity
 * (limited to stock), the subtotal, and, for Buy Now, the delivery address and payment step.
 */
export default function OrderConfirmModal({ product, initialQty = 1, mode = "cart", busy = false, onCancel, onConfirm }) {
  const [qty, setQty] = useState(initialQty);
  const [address, setAddress] = useState(null);
  const stock = Number(product.stock) || 0;
  const priced = priceLine(product.price, qty, product.salePercent);
  const isBuy = mode === "buy";
  const discounted = priced.rate > 0;

  useEffect(() => {
    if (!isBuy) return;
    client.get("/api/addresses")
      .then((res) => {
        const list = res.data.addresses || [];
        setAddress(list.find((a) => a.isDefault) || list[0] || null);
      })
      .catch(() => {});
  }, [isBuy]);

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

          <div className="field">
            <label>Quantity{stock ? ` (${stock} available)` : ""}</label>
            <QtyInput value={qty} onCommit={setQty} max={stock || null} packSize={product.packSize} />
          </div>

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
