export default function StarRating({ value = 0, size = 16, label }) {
  const filled = Math.round(value);
  return (
    <span className="stars" style={{ fontSize: size }} role="img" aria-label={label || `${value} out of 5 stars`}>
      {[1, 2, 3, 4, 5].map((n) => (
        <span key={n} className={n <= filled ? "on" : ""}>{"\u2605"}</span>
      ))}
    </span>
  );
}
