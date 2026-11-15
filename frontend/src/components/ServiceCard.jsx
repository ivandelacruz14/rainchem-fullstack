import { peso } from "../utils/format";

export default function ServiceCard({ service, area, onBook }) {
  const selected = service.selected;
  const hasArea = Boolean(area);

  return (
    <article className="service-card service-card-item">
      <div className="service-card-head">
        <h3>{service.name}</h3>
        {service.category && <span className="badge">{service.category}</span>}
      </div>
      <p className="service-desc">{service.description}</p>
      {service.requirements && (
        <p className="field-hint"><strong>Requirements:</strong> {service.requirements}</p>
      )}

      {hasArea ? (
        selected?.available ? (
          <div className="service-status ok">
            <span className="service-price">{peso(selected.price)}</span>
            <span>Available in {selected.area}</span>
          </div>
        ) : (
          <div className="service-status bad">
            <strong>Not available</strong>
            <span>{selected?.reason || "Not offered in this area"}</span>
          </div>
        )
      ) : (
        <div className="service-status">
          <span>Choose your area above to see the price.</span>
        </div>
      )}

      <button
        type="button" className="btn btn-primary btn-block" style={{ marginTop: 12 }}
        disabled={!hasArea || !selected?.available} onClick={() => onBook(service)}
      >
        {!hasArea ? "Select an area first" : selected?.available ? "Request this service" : "Unavailable in this area"}
      </button>
    </article>
  );
}
