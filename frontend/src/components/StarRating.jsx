export function StarDisplay({ value, size = 16 }) {
  const rounded = Math.round(value || 0);
  return (
    <span className="stars" style={{ fontSize: size }} role="img" aria-label={`${value || 0} out of 5 stars`}>
      {[1, 2, 3, 4, 5].map((n) => (
        <span key={n} className={n <= rounded ? "star on" : "star"} aria-hidden="true">{"\u2605"}</span>
      ))}
    </span>
  );
}

export function StarInput({ value, onChange }) {
  return (
    <div className="star-input" role="radiogroup" aria-label="Star rating">
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n} type="button" role="radio" aria-checked={value === n} aria-label={`${n} star${n > 1 ? "s" : ""}`}
          className={n <= value ? "star-btn on" : "star-btn"} onClick={() => onChange(n)}
        >
          {"\u2605"}
        </button>
      ))}
    </div>
  );
}
