export default function Brand({ variant = "full", height = 48, onDark = false, style }) {
  const src = variant === "wordmark" ? "/images/raimol-wordmark.png" : "/images/raimol-logo.png";
  return (
    <img
      src={src}
      alt="Raimol"
      className={`brand-logo${onDark ? " on-dark" : ""}`}
      style={{ height, ...style }}
    />
  );
}