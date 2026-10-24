import { useCallback, useEffect, useState } from "react";
import client from "../api/client";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { formatDate } from "../utils/format";
import { StarDisplay, StarInput } from "./StarRating";

const MAX_COMMENT = 500;

function ReviewForm({ productId, onSubmitted }) {
  const showToast = useToast();
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    if (rating < 1) {
      setError("Please choose a star rating.");
      return;
    }
    setError("");
    setSaving(true);
    try {
      await client.post(`/api/products/${productId}/reviews`, { rating, comment });
      showToast("Thanks for your review", "success");
      onSubmitted();
    } catch (err) {
      setError(err.response?.data?.error || "Could not save your review. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="review-form" onSubmit={handleSubmit}>
      <h5>Write a review</h5>
      {error && <div className="alert alert-error">{error}</div>}
      <StarInput value={rating} onChange={setRating} />
      <textarea
        rows="3" maxLength={MAX_COMMENT} placeholder="Share how this product worked for you (optional)"
        value={comment} onChange={(e) => setComment(e.target.value)}
      />
      <div className="review-form-foot">
        <span className="field-hint">{comment.length}/{MAX_COMMENT}</span>
        <button type="submit" className="btn btn-primary btn-sm" disabled={saving}>
          {saving ? "Saving..." : "Submit review"}
        </button>
      </div>
    </form>
  );
}

export default function ProductReviews({ productId }) {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [failed, setFailed] = useState(false);
  const [eligibility, setEligibility] = useState(null);

  const load = useCallback(() => {
    client.get(`/api/products/${productId}/reviews`)
      .then((res) => { setData(res.data); setFailed(false); })
      .catch(() => setFailed(true));
    if (user) {
      client.get(`/api/products/${productId}/reviews/eligibility`)
        .then((res) => setEligibility(res.data))
        .catch(() => setEligibility(null));
    } else {
      setEligibility(null);
    }
  }, [productId, user]);

  useEffect(() => {
    setData(null);
    load();
  }, [load]);

  const summary = data?.summary;
  const maxCount = summary ? Math.max(1, ...Object.values(summary.distribution)) : 1;

  return (
    <section className="pd-reviews" aria-labelledby="reviews-heading">
      <h4 className="pd-extra-head" id="reviews-heading">Customer Reviews</h4>

      {failed && <p className="field-hint">Reviews could not be loaded right now.</p>}
      {!data && !failed && <p className="field-hint">Loading reviews...</p>}

      {data && (
        <>
          {summary.count === 0 ? (
            <p className="review-empty">No reviews yet. Reviews appear here once customers have received this product.</p>
          ) : (
            <div className="review-summary">
              <div className="review-average">
                <strong>{summary.average.toFixed(1)}</strong>
                <StarDisplay value={summary.average} size={18} />
                <span>{summary.count} review{summary.count === 1 ? "" : "s"}</span>
              </div>
              <div className="review-bars">
                {[5, 4, 3, 2, 1].map((star) => (
                  <div className="review-bar-row" key={star}>
                    <span>{star}{"\u2605"}</span>
                    <div className="hit-bar-track"><div className="hit-bar-fill" style={{ width: `${(summary.distribution[star] / maxCount) * 100}%` }} /></div>
                    <span>{summary.distribution[star]}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {user && eligibility?.canReview && <ReviewForm productId={productId} onSubmitted={load} />}
          {user && eligibility && !eligibility.canReview && eligibility.reason && (
            <p className="field-hint">{eligibility.reason}</p>
          )}
          {!user && <p className="field-hint">Log in to review products you have received.</p>}

          <ul className="review-list">
            {data.reviews.map((review) => (
              <li key={review.id} className="review-item">
                <div className="review-item-head">
                  <StarDisplay value={review.rating} />
                  <strong>{review.reviewer}</strong>
                  <span className="review-date">{formatDate(review.createdAt).split(",").slice(0, 2).join(",")}</span>
                </div>
                {review.comment && <p>{review.comment}</p>}
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
