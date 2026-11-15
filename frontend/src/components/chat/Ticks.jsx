const LABELS = { sent: "Sent", delivered: "Delivered", read: "Read" };

// One grey check: stored on the server. Two grey: delivered. Two blue: read.
export default function Ticks({ status }) {
  if (!LABELS[status]) return null;
  const double = status !== "sent";
  return (
    <span className={`ticks ${status}`} role="img" aria-label={LABELS[status]} title={LABELS[status]}>
      <svg width={double ? 18 : 12} height="11" viewBox={double ? "0 0 18 11" : "0 0 12 11"} fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
        <path d="M1 6l3 3 6-7" />
        {double && <path d="M7 8.2 8 9l6-7" />}
      </svg>
    </span>
  );
}
