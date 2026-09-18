import { useLocation, useNavigate, Link } from "react-router-dom";
import { peso } from "../utils/format";
import ProductVisual from "../components/ProductVisual";
import { useCart } from "../context/CartContext";
import { useToast } from "../context/ToastContext";

export default function OrderSuccess() {
  const { state } = useLocation();
  const navigate = useNavigate();
  const { addItem } = useCart();
  const showToast = useToast();

  if (!state?.order) {
    navigate("/", { replace: true });
    return null;
  }

  const { order, recommendations = [] } = state;

  function handleAddRec(product) {
    addItem(product, 1);
    showToast("Added to cart", "success");
  }

  return (
    <div className="container" style={{ padding: "50px 24px 80px", maxWidth: 700 }}>
      <div className="text-center">
        <div style={{ width: 64, height: 64, borderRadius: "50%", background: "#e9f7ef", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 16px" }}>
          <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#1d6e3b" strokeWidth="2.4"><path d="M20 6 9 17l-5-5" /></svg>
        </div>
        <h3>Thank you, {order.customer.name.split(" ")[0]}!</h3>
        <p style={{ color: "#57524c" }}>
          Your order has been placed and is pending confirmation from our team. You'll get an
          email once it's confirmed, and you can cancel it from My Orders until then.
        </p>
        <div className="panel" style={{ textAlign: "left", background: "var(--fog)", border: "none", marginTop: 16 }}>
          <div className="cart-summary-row"><span>Order Number</span><span className="mono">{order.orderNumber}</span></div>
          <div className="cart-summary-row"><span>Tracking Number</span><span className="mono">{order.trackingNumber}</span></div>
          <div className="cart-summary-row total"><span>Total Paid</span><span>{peso(order.total)}</span></div>
        </div>
        <Link to="/account/orders" className="btn btn-primary btn-block" style={{ marginTop: 18 }}>View My Orders</Link>
        <Link to="/" className="btn btn-outline btn-block" style={{ marginTop: 10 }}>Continue Shopping</Link>
      </div>

      {recommendations.length > 0 && (
        <div style={{ textAlign: "left", marginTop: 28, paddingTop: 22, borderTop: "1px solid rgba(24,20,15,.08)" }}>
          <h4 style={{ marginBottom: 4 }}>You May Also Like</h4>
          <p className="field-hint" style={{ marginBottom: 14 }}>Frequently paired with what you just ordered</p>
          <div className="reco-grid">
            {recommendations.map((p) => (
              <div className="reco-card" key={p.id}>
                <div className="reco-thumb" onClick={() => navigate("/")}> <ProductVisual product={p} widthPercent={50} /></div>
                <div className="reco-name">{p.name}</div>
                <div className="reco-bottom">
                  <span className="reco-price">{peso(p.price)}</span>
                  <button className="icon-add" title="Add to cart" onClick={() => handleAddRec(p)}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <circle cx="9" cy="21" r="1" /><circle cx="19" cy="21" r="1" />
                      <path d="M1 1h4l2.6 13.4a2 2 0 0 0 2 1.6h9.8a2 2 0 0 0 2-1.6L23 6H6" />
                    </svg>
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
