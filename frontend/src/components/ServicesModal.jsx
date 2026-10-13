import { peso } from "../utils/format";

export default function ServicesModal({ services, cartIds, onToggle, onContinue, onClose }) {
  const addedCount = services.filter((s) => cartIds.has(s.id)).length;

  return (
    <div className="overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h3 style={{ margin: 0, fontSize: 19 }}>Add a service?</h3>
          <button type="button" className="modal-close" onClick={onClose}>&times;</button>
        </div>
        <div className="modal-body">
          <p style={{ marginTop: 0, fontSize: 14, color: "#57524c" }}>
            Our partner service bays can install your parts. Add one to this order, or skip it.
          </p>

          {services.map((s) => {
            const added = cartIds.has(s.id);
            return (
              <div key={s.id} className={`svc-option ${added ? "added" : ""}`}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 700, fontSize: 14 }}>{s.name}</div>
                  <div style={{ fontSize: 12.5, color: "#6b665f", margin: "2px 0 4px" }}>{s.shortDesc}</div>
                  <div style={{ fontWeight: 700, color: "var(--red-700)" }}>{peso(s.price)}</div>
                </div>
                <button
                  type="button"
                  className={`btn btn-sm ${added ? "btn-outline" : "btn-primary"}`}
                  onClick={() => onToggle(s, added)}
                >
                  {added ? "Remove" : "Add"}
                </button>
              </div>
            );
          })}

          <button type="button" className="btn btn-primary btn-block" style={{ marginTop: 16 }} onClick={onContinue}>
            {addedCount > 0 ? `Continue to payment (${addedCount} service${addedCount > 1 ? "s" : ""} added)` : "No thanks, continue to payment"}
          </button>
        </div>
      </div>
    </div>
  );
}
