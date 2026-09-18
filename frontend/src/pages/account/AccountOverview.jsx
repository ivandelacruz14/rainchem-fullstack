import { useState, useEffect } from "react";
import client from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import { formatDate } from "../../utils/format";

export default function AccountOverview() {
  const { user } = useAuth();
  const [orders, setOrders] = useState([]);

  useEffect(() => {
    client.get("/api/orders").then((res) => setOrders(res.data.orders));
  }, []);

  const inTransit = orders.filter((o) => ["confirmed", "processing", "shipped"].includes(o.status)).length;
  const delivered = orders.filter((o) => o.status === "delivered").length;

  return (
    <div>
      <h2>Welcome back, {user?.name.split(" ")[0]}</h2>
      <p style={{ color: "#57524c" }}>Here's a quick snapshot of your account.</p>
      <div className="stat-grid" style={{ marginTop: 20 }}>
        <div className="stat-box"><div className="label">Total Orders</div><div className="value">{orders.length}</div></div>
        <div className="stat-box"><div className="label">In Transit</div><div className="value">{inTransit}</div></div>
        <div className="stat-box"><div className="label">Delivered</div><div className="value">{delivered}</div></div>
        <div className="stat-box"><div className="label">Member Since</div><div className="value" style={{ fontSize: 16 }}>{user ? formatDate(user.createdAt).split(",")[0] : ""}</div></div>
      </div>
    </div>
  );
}
