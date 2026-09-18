import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import client from "../../api/client";
import OrderCard from "../../components/OrderCard";
import { useToast } from "../../context/ToastContext";

export default function AccountOrders() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const showToast = useToast();

  function loadOrders() {
    client.get("/api/orders").then((res) => {
      setOrders(res.data.orders);
      setLoading(false);
    });
  }

  useEffect(loadOrders, []);

  async function handleCancel(orderId) {
    if (!window.confirm("Cancel this order? This cannot be undone.")) return;
    try {
      await client.post(`/api/orders/${orderId}/cancel`);
      showToast("Order cancelled", "success");
      loadOrders();
    } catch (err) {
      showToast(err.response?.data?.error || "Could not cancel this order", "error");
    }
  }

  return (
    <div>
      <h2>My Orders</h2>
      {loading ? null : orders.length === 0 ? (
        <div className="empty-state">
          No orders yet. <Link to="/" style={{ color: "var(--red-700)", fontWeight: 600 }}>Start shopping</Link>
        </div>
      ) : (
        orders.map((order) => <OrderCard key={order.id} order={order} onCancel={handleCancel} />)
      )}
    </div>
  );
}
