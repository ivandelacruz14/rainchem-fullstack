import { Link } from "react-router-dom";
import useProductReviews from "../../hooks/useProductReviews";
import { useAuth } from "../../context/AuthContext";
import { formatDate } from "../../utils/format";
import StarRating from "./StarRating";

function Distribution({ distribution, count }) {
  return (
    <div className="review-bars">
      {[5, 4, 3, 2, 1].map((n) => {
        const total = distribution[String(n)] || 0;
        return (
          <div className="review-bar-row" key={n}>
            <span>{n}</span>
            <div className="hit-bar-track"><div className="hit-bar-fill" style={{ width: `${count ? (total / count) * 100 : 0}%` }} /></div>
            <span className="review-bar-count">{total}</span>
          </div>
        );
      })}
    </div>
  );
}

export default function ReviewSection({ productId, onNavigate }) {
  const { user } = useAuth();
  const { loading, error, data } = useProductReviews(productId);

  return (
    <section className="pd-reviews" aria-label="Customer reviews">
      <h4 className="pd-extra-head">Customer Reviews</h4>

      {loading && <p className="field-hint">Loading reviews...</p>}
      {error && <p className="field-hint">Reviews could not be loaded right now.</p>}

      {data && data.summary.count === 0 && (
        <p className="review-empty">
          No reviews yet. Customers can review this product after their order has been delivered.
        </p>
      )}

      {data && data.summary.count > 0 && (
        <>
          <div className="review-summary">
            <div className="review-score">
              <strong>{data.summary.average.toFixed(1)}</strong>
              <StarRating value={data.summary.average} size={18} />
              <span>{data.summary.count} review{data.summary.count === 1 ? "" : "s"}</span>
            </div>
            <Distribution distribution={data.summary.distribution} count={data.summary.count} />
          </div>
          <ul className="review-list">
            {data.reviews.map((review) => (
              <li key={review.id} className="review-item">
                <div className="review-item-top">
                  <StarRating value={review.rating} size={14} />
                  <span className="review-author">{review.author}</span>
                  <span className="review-date">{formatDate(review.createdAt).split(",").slice(0, 2).join(",")}</span>
                </div>
                {review.comment && <p>{review.comment}</p>}
              </li>
            ))}
          </ul>
        </>
      )}

      {user && (
        <p className="field-hint">
          Received this product? Rate it from{" "}
          <Link to="/account/orders?tab=to_review" onClick={onNavigate}>My Orders</Link>.
        </p>
      )}
    </section>
  );
}
