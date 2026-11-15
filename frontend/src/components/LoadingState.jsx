/** A spinner with a short message. Use it where a screen waits for data, instead of a blank page. */
export default function LoadingState({ message = "Loading..." }) {
  return (
    <div className="loading-state" role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      <span>{message}</span>
    </div>
  );
}

/** Placeholder cards that keep the layout still while products load. */
export function SkeletonGrid({ count = 8 }) {
  return (
    <div className="product-grid" aria-busy="true" aria-label="Loading products">
      {Array.from({ length: count }, (_, i) => (
        <div className="product-card skeleton-card" key={i} aria-hidden="true">
          <div className="product-thumb skeleton-block" />
          <div className="product-info">
            <span className="skeleton-line short" />
            <span className="skeleton-line" />
            <span className="skeleton-line short" />
          </div>
        </div>
      ))}
    </div>
  );
}
