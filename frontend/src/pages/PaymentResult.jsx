import { useEffect, useState, useRef } from "react";
import { useSearchParams, Link, useNavigate } from "react-router-dom";
import client from "../api/client";
import { peso } from "../utils/format";

const MAX_CHECKS = 5;

export default function PaymentResult() {
  const [params] = useSearchParams();
  const orderId = params.get("order");
  const cancelled = params.get("cancelled") === "1";
  const navigate = useNavigate();

  const [state, setState] = useState("checking");
  const [order, setOrder] = useState(null);
  const [message, setMessage] = useState("");
  const [retrying, setRetrying] = useState(false);
  const checks = useRef(0);

  useEffect(() => {
    if (!orderId) {
      navigate("/account/orders", { replace: true });
      return undefined;
    }
    let timer;
    let stopped = false;

    async function check() {
      try {
        const res = await client.post(`/api/payments/orders/${orderId}/verify`);
        if (stopped) return;
        setOrder(res.data.order);
        if (res.data.paid) {
          setState("paid");
        } else if (!cancelled && checks.current < MAX_CHECKS) {
          checks.current += 1;
          timer = setTimeout(check, 2500);
        } else {
          setState("unpaid");
        }
      } catch (err) {
        if (stopped) return;
        setMessage(err.response?.data?.error || "We couldn't confirm your payment yet.");
        setOrder(err.response?.data?.order || null);
        setState("error");
      }
    }
    check();
    return () => {
      stopped = true;
      clearTimeout(timer);
    };
  }, [orderId, cancelled, navigate]);

  function handlePayAgain() {
    // Back to our payment page, where the customer can retry the card or pick GCash / COD.
    setRetrying(true);
    navigate(`/payment/${orderId}`);
  }

  return (
    <div className="container" style={{ padding: "60px 24px 80px", maxWidth: 560, textAlign: "center" }}>
      {state === "checking" && (
        <>
          <h3>Confirming your payment...</h3>
          <p style={{ color: "var(--muted)" }}>Please don't close this page.</p>
        </>
      )}

      {state === "paid" && (
        <>
          <div className="result-icon ok">
            <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#1d6e3b" strokeWidth="2.4"><path d="M20 6 9 17l-5-5" /></svg>
          </div>
          <h3>Payment received!</h3>
          <p style={{ color: "var(--muted)" }}>
            Thank you. We've received your {order?.paymentMethod} payment of {order && peso(order.total)} for order{" "}
            <strong className="mono">{order?.orderNumber}</strong>. Our team will confirm it shortly.
          </p>
          <Link to="/account/orders?tab=to_ship" className="btn btn-primary btn-block" style={{ marginTop: 18 }}>View My Orders</Link>
          <Link to="/" className="btn btn-outline btn-block" style={{ marginTop: 10 }}>Continue Shopping</Link>
        </>
      )}

      {(state === "unpaid" || state === "error") && (
        <>
          <div className="result-icon warn">!</div>
          <h3>{cancelled ? "Payment cancelled" : "Payment not completed yet"}</h3>
          <p style={{ color: "var(--muted)" }}>
            {message || "Your order is saved under To Pay. You can finish the payment now or later from My Orders."}
          </p>
          <button className="btn btn-primary btn-block" style={{ marginTop: 18 }} disabled={retrying} onClick={handlePayAgain}>
            {retrying ? "Please wait..." : "Try again or choose another way to pay"}
          </button>
          <Link to="/account/orders?tab=to_pay" className="btn btn-outline btn-block" style={{ marginTop: 10 }}>Go to My Orders</Link>
        </>
      )}
    </div>
  );
}
