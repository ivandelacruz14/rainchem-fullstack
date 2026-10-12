import { useState, useEffect } from "react";
import { Link, useSearchParams } from "react-router-dom";
import client from "../../api/client";
import OrderCard from "../../components/OrderCard";
import { ReviewModal, ReturnModal } from "../../components/OrderActionModals";
import { useToast } from "../../context/ToastContext";

const TABS = [
  { key: "all", label: "All" },
  { key: "to_pay", label: "To Pay" },
  { key: "to_ship", label: "To Ship" },
  { key: "to_receive", label: "To Receive" },
  { key: "to_review", label: "To Review" },
  { key: "return", label: "Return" },
];

const EMPTY_TEXT = {
  all: "No orders yet.",
  to_pay: "Nothing waiting for payment.",
  to_ship: "No orders waiting to be shipped.",
  to_receive: "No orders on the way.",
  to_review: "No delivered orders to review.",
  return: "No returned or cancelled orders.",
};

export default function AccountOrders() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [reviewing, setReviewing] = useState(null);
  const [returning, setReturning] = useState(null);
  const [params, setParams] = useSearchParams();
  const showToast = useToast();

  const tab = TABS.some((t) => t.key === params.get("tab")) ? params.get("tab") : "all";

  function loadOrders() {
    client.get("/api/orders")
      .then((res) => setOrders(res.data.orders))
      .finally(() => setLoading(false));
  }
  useEffect(loadOrders, []);

  const counts = {};
  TABS.forEach((t) => {
    counts[t.key] = t.key === "all" ? orders.length : orders.filter((o) => o.tab === t.key).length;
  });
  const visible = tab === "all" ? orders : orders.filter((o) => o.tab === tab);

  function changeTab(key) {
    setParams(key === "all" ? {} : { tab: key });
  }

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

  async function handlePay(orderId) {
    try {
      const res = await client.post(`/api/payments/orders/${orderId}/checkout`);
      window.location.href = res.data.checkoutUrl;
    } catch (err) {
      showToast(err.response?.data?.error || "Could not start the payment", "error");
    }
  }

  async function handleReceive(orderId) {
    if (!window.confirm("Confirm that you received this order?")) return;
    try {
      await client.post(`/api/orders/${orderId}/received`);
      showToast("Thanks! You can now rate your order.", "success");
      loadOrders();
      changeTab("to_review");
    } catch (err) {
      showToast(err.response?.data?.error || "Could not update this order", "error");
    }
  }

  function handleDone(message) {
    setReviewing(null);
    setReturning(null);
    showToast(message, "success");
    loadOrders();
  }

  return (
    <div>
      <h2>My Orders</h2>

      <div className="order-tabs" role="tablist">
        {TABS.map((t) => (
          <button
            key={t.key} role="tab" aria-selected={tab === t.key}
            className={`order-tab ${tab === t.key ? "active" : ""}`}
            onClick={() => changeTab(t.key)}
          >
            {t.label}
            {t.key !== "all" && counts[t.key] > 0 && <span className="order-tab-count">{counts[t.key]}</span>}
          </button>
        ))}
      </div>

      {loading ? null : visible.length === 0 ? (
        <div className="empty-state">
          {EMPTY_TEXT[tab]} <Link to="/" style={{ color: "var(--red-700)", fontWeight: 600 }}>Start shopping</Link>
        </div>
      ) : (
        visible.map((order) => (
          <OrderCard
            key={order.id} order={order}
            onCancel={handleCancel} onPay={handlePay} onReceive={handleReceive}
            onReview={setReviewing} onReturn={setReturning}
          />
        ))
      )}

      {reviewing && <ReviewModal order={reviewing} onClose={() => setReviewing(null)} onDone={handleDone} />}
      {returning && <ReturnModal order={returning} onClose={() => setReturning(null)} onDone={handleDone} />}
    </div>
  );
}
