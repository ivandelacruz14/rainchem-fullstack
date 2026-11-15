import { Link } from "react-router-dom";
import { peso } from "../../utils/format";

/** What the assistant found in verified documentation. Everything here comes from the server's answer:
 *  the reasons, specifications and sources are copied from the documents, not written by the assistant. */
export default function RecommendationCards({ recommendation, onNavigate }) {
  if (!recommendation) return null;
  const { recommendations = [], missing = [], notConfirmed = [] } = recommendation;

  return (
    <div className="rec-list">
      {recommendations.map((card) => (
        <article key={card.productId} className="rec-card">
          <header className="rec-head">
            <strong>{card.name}</strong>
            <span className="rec-price">{peso(card.price)}</span>
          </header>
          <div className="rec-sub">
            {card.category} &middot; {card.inStock ? "In stock" : "Out of stock"}
          </div>

          <h5>Why it matches</h5>
          <ul className="rec-why">
            {card.matched.map((m) => (
              <li key={m.requirement}><span className="rec-ok" aria-hidden="true">&#10003;</span> <strong>{m.requirement}</strong><span className="rec-evidence">{m.evidence}</span></li>
            ))}
          </ul>

          {card.specs.length > 0 && (
            <>
              <h5>Specifications (from the documents)</h5>
              <dl className="rec-specs">
                {card.specs.map((s) => (
                  <div key={s.label}><dt>{s.label}</dt><dd>{s.values.join(", ")}</dd></div>
                ))}
              </dl>
            </>
          )}

          {card.limitations.length > 0 && (
            <div className="rec-limits">
              <h5>Check before you buy</h5>
              <ul>{card.limitations.map((l) => <li key={l}>{l}</li>)}</ul>
            </div>
          )}

          <h5>Sources</h5>
          <ul className="rec-sources">
            {card.sources.map((s) => (
              <li key={s.documentId}>{s.title}{s.version ? `, version ${s.version}` : ""}{s.source ? ` (${s.source})` : ""}</li>
            ))}
          </ul>

          <Link to={card.link} className="btn btn-primary btn-sm" onClick={onNavigate}>View product</Link>
        </article>
      ))}

      {recommendations.length > 0 && missing.length > 0 && (
        <div className="rec-missing">
          <strong>Information that would make this more certain</strong>
          <ul>{missing.map((m) => <li key={m}>{m}</li>)}</ul>
        </div>
      )}

      {recommendations.length === 0 && notConfirmed.length > 0 && (
        <div className="rec-missing">
          <strong>Partly matching, not confirmed</strong>
          <ul>{notConfirmed.map((n) => <li key={n.name}>{n.name}: not confirmed for {n.unmet.join(", ")}</li>)}</ul>
        </div>
      )}
    </div>
  );
}

const QUICK = [
  { test: /equipment or vehicle/i, replies: ["Motorcycle", "Car", "Truck", "Generator"] },
  { test: /type of engine/i, replies: ["4-stroke", "2-stroke", "Gasoline", "Diesel"] },
  { test: /used for/i, replies: ["Engine oil", "Gear oil", "Coolant", "Brake fluid"] },
  { test: /viscosity grade or specification/i, replies: ["Not sure"] },
];

export function quickReplies(question) {
  return QUICK.find((q) => q.test.test(question || ""))?.replies || [];
}
