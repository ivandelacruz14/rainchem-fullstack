import { useEffect, useState } from "react";

/**
 * Quantity you can type. The value is always pieces; when the product has a pack size, the person can switch
 * the unit to boxes, and the number is converted (boxes x pieces per box). Typed numbers are checked on leave or Enter.
 */
export default function QtyInput({ value, onCommit, max = null, packSize = null }) {
  const canUseBoxes = Number(packSize) > 1;
  const [unit, setUnit] = useState("pcs");
  const perUnit = unit === "boxes" && canUseBoxes ? Number(packSize) : 1;
  const shown = Math.max(1, Math.round(value / perUnit));
  const [text, setText] = useState(String(shown));

  useEffect(() => {
    setText(String(shown));
  }, [shown]);

  function commit(raw) {
    const n = parseInt(String(raw).replace(/[^0-9]/g, ""), 10);
    if (!Number.isFinite(n) || n < 1) {
      setText(String(shown));
      return;
    }
    let pieces = n * perUnit;
    if (max && pieces > max) pieces = max;
    const displayed = Math.max(1, Math.floor(pieces / perUnit));
    setText(String(displayed));
    if (pieces !== value) onCommit(pieces);
  }

  return (
    <span className="qty-input-wrap">
      <button type="button" aria-label="Decrease" onClick={() => commit(shown - 1)} disabled={shown <= 1}>-</button>
      <input
        className="qty-input" aria-label="Quantity" inputMode="numeric" value={text}
        onChange={(e) => setText(e.target.value.replace(/[^0-9]/g, ""))}
        onBlur={(e) => commit(e.target.value)}
        onKeyDown={(e) => { if (e.key === "Enter") commit(e.currentTarget.value); }}
      />
      <button type="button" aria-label="Increase" onClick={() => commit(shown + 1)}>+</button>
      {canUseBoxes && (
        <select aria-label="Unit" className="qty-unit" value={unit} onChange={(e) => setUnit(e.target.value)}>
          <option value="pcs">pcs</option>
          <option value="boxes">boxes</option>
        </select>
      )}
    </span>
  );
}
