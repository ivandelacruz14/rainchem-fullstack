const ON_THE_WAY = ["ready_for_delivery", "shipped", "rescheduled", "delivery_failed"];

function day(iso) {
  const d = new Date(`${String(iso).slice(0, 10)}T00:00:00`);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString("en-PH", { month: "long", day: "numeric", year: "numeric" });
}

/** For the customer: who is delivering the order, how to reach them, and the estimated delivery date. */
export default function RiderInfo({ order }) {
  const waiting = ON_THE_WAY.includes(order.status);
  const rider = waiting ? order.rider : null;
  const eta = waiting ? order.estimatedDelivery : null;
  const needsConfirm = order.canReceive;
  if (!rider && !eta && !needsConfirm && !order.autoConfirmed) return null;

  return (
    <div className="rider-info" role="group" aria-label="Delivery details">
      {rider && (
        <div className="rider-info-row">
          <span className="rider-info-label">Your rider</span>
          <strong>{rider.name}</strong>
          {rider.phone && <a href={`tel:${rider.phone}`} className="rider-info-phone">{rider.phone}</a>}
        </div>
      )}
      {eta && (
        <div className="rider-info-row">
          <span className="rider-info-label">Estimated delivery</span>
          <strong>{day(eta)}</strong>
        </div>
      )}
      {order.autoConfirmed && <p className="rider-info-confirm">Confirmed for you automatically after delivery.</p>}
      {needsConfirm && (
        <p className="rider-info-confirm">
          The rider has delivered your order. Please confirm that you received it.
          {order.autoConfirmAt && <> If you do not, we confirm it for you on {day(order.autoConfirmAt)}.</>}
        </p>
      )}
    </div>
  );
}
