import { formatDate } from "../../utils/format";

const ICONS = {
  received: <path d="M9 4h6l1 2h3v14H5V6h3l1-2zM9 12h6M9 16h4" />,
  verification: <path d="M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zm9 15-4-4M8.5 11l2 2 3.5-4" />,
  approved: <path d="M12 3 5 6v6c0 4 3 7 7 9 4-2 7-5 7-9V6l-7-3zM9 12l2 2 4-4" />,
  preparing: <path d="M3 8l9-5 9 5v9l-9 5-9-5V8zm9 5v9M3 8l9 5 9-5" />,
  in_transit: <path d="M2 6h11v9H2zM13 9h4l3 3v3h-7zM6 18a2 2 0 1 0 0-.01M17 18a2 2 0 1 0 0-.01" />,
  delivered: <path d="M5 21V4M5 4h12l-2 4 2 4H5" />,
};

function Node({ stop, index }) {
  return (
    <span className="stop-node" aria-hidden="true">
      <span className="stop-hex">
        {stop.state === "done" ? (
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12.5l4.5 4.5L19 7" /></svg>
        ) : stop.state === "stopped" ? (
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.8" strokeLinecap="round"><path d="M6 6l12 12M18 6L6 18" /></svg>
        ) : (
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">{ICONS[stop.key]}</svg>
        )}
      </span>
      <span className="stop-index">{index + 1}</span>
    </span>
  );
}

function timeText(stop) {
  if (stop.at) return formatDate(stop.at);
  if (stop.state === "done") return "Completed";
  if (stop.state === "current") return "In progress";
  if (stop.state === "stopped") return "Stopped here";
  return "Not yet";
}

/** The Rainchem Order Journey: a dipstick-style gauge and a route of hex-nut stops. Every
 *  state and time shown here comes from the order's real status history. */
export default function OrderJourney({ order }) {
  const { journey } = order;
  const stops = journey.milestones;
  const progress = Math.round((journey.stageNumber / journey.stageCount) * 100);

  return (
    <section className={`journey journey-${journey.state}`} aria-label={`Order journey for ${order.orderNumber}`}>
      <header className="journey-head">
        <div className="journey-id">
          <span className="journey-eyebrow">Order journey</span>
          <h2 className="journey-number">{order.orderNumber}</h2>
          <span className="journey-tracking">Tracking no. <span className="mono">{order.trackingNumber}</span></span>
        </div>
        <div className="journey-status">
          <span className="journey-chip">{journey.headline}</span>
          {journey.updatedAt && <span className="journey-updated">Latest update: {formatDate(journey.updatedAt)}</span>}
        </div>
      </header>

      <div className="dipstick" role="progressbar" aria-valuemin={0} aria-valuemax={journey.stageCount} aria-valuenow={journey.stageNumber}
        aria-label={`Stage ${journey.stageNumber} of ${journey.stageCount}`}>
        <div className="dipstick-fill" style={{ width: `${progress}%` }} />
        <div className="dipstick-ticks" />
        <div className="dipstick-labels"><span>Ordered</span><span>Stage {journey.stageNumber} of {journey.stageCount}</span><span>Delivered</span></div>
      </div>

      {journey.alerts.map((alert) => (
        <div key={alert.kind + alert.title} className={`journey-alert ${alert.kind}`} role="status">
          <strong>{alert.title}</strong>
          <span>{alert.message}</span>
          {alert.at && <time>{formatDate(alert.at)}</time>}
        </div>
      ))}

      <ol className="journey-route">
        {stops.map((stop, i) => {
          const next = stops[i + 1];
          const linked = next && stop.state === "done" && ["done", "current", "stopped"].includes(next.state);
          return (
            <li key={stop.key} className={`stop ${stop.state} ${linked ? "linked" : ""}`} aria-current={stop.state === "current" ? "step" : undefined}>
              <Node stop={stop} index={i} />
              <div className="stop-body">
                <h3>{stop.title}</h3>
                <time className="stop-time">{timeText(stop)}</time>
                <p>{stop.description}</p>
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
