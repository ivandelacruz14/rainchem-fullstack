import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import client from "../api/client";
import ReceiptView from "../components/ReceiptView";

export default function Receipt() {
  const { orderId } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    client
      .get(`/api/orders/${orderId}/receipt`)
      .then((res) => setData(res.data))
      .catch((err) => setError(err.response?.data?.error || "Receipt not available"));
  }, [orderId]);

  if (error) {
    return (
      <div className="container" style={{ padding: "60px 24px", textAlign: "center" }}>
        <div className="alert alert-error" style={{ maxWidth: 420, margin: "0 auto" }}>{error}</div>
        <button className="btn btn-outline" style={{ marginTop: 16 }} onClick={() => navigate("/account/orders")}>Back to My Orders</button>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="container">
      <div style={{ maxWidth: 780, margin: "0 auto" }}>
        <div className="no-print" style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 24 }}>
          <button className="btn btn-outline btn-sm" onClick={() => navigate("/account/orders")}>Back</button>
          <button className="btn btn-primary btn-sm" onClick={() => window.print()}>Print Receipt</button>
        </div>
      </div>
      <ReceiptView order={data.order} receipt={data.receipt} />
    </div>
  );
}
