import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import client from "../api/client";

export default function PaymentDemo() {
  const { orderId } = useParams();
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function finish(success) {
    setBusy(true);
    setError("");
    try {
      await client.post(`/api/payments/orders/${orderId}/demo-complete`, { success });
      navigate(`/payment/result?order=${orderId}${success ? "" : "&cancelled=1"}`, { replace: true });
    } catch (err) {
      setError(err.response?.data?.error || "Demo payment is not available.");
      setBusy(false);
    }
  }

  return (
    <div className="container" style={{ padding: "60px 24px 80px", maxWidth: 440, textAlign: "center" }}>
      <div className="panel">
        <div className="badge" style={{ marginBottom: 12 }}>TEST MODE</div>
        <h3 style={{ marginTop: 0 }}>Demo payment page</h3>
        <p style={{ color: "#57524c", fontSize: 14 }}>
          This stands in for the GCash / card page. No real money is used.
        </p>
        {error && <div className="alert alert-error">{error}</div>}
        <button className="btn btn-primary btn-block" disabled={busy} onClick={() => finish(true)}>Approve payment</button>
        <button className="btn btn-outline btn-block" style={{ marginTop: 10 }} disabled={busy} onClick={() => finish(false)}>Cancel payment</button>
      </div>
    </div>
  );
}
