import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import Avatar from "../../components/chat/Avatar";
import client from "../../api/client";
import { formatDate, peso } from "../../utils/format";
import { photoPath } from "./ConversationList";

export default function CustomerPanel({ conversationId, onClose }) {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setData(null);
    setFailed(false);
    client.get(`/api/admin/live-chat/conversations/${conversationId}/customer`)
      .then((res) => { if (!cancelled) setData(res.data); })
      .catch(() => { if (!cancelled) setFailed(true); });
    return () => { cancelled = true; };
  }, [conversationId]);

  return (
    <aside className="lc-info" aria-label="Customer and orders">
      <div className="lc-info-head">
        <h3>Customer</h3>
        {onClose && <button type="button" className="btn btn-outline btn-sm lc-info-close" onClick={onClose}>Back to chat</button>}
      </div>
      {failed && <p className="field-hint">Customer details could not be loaded.</p>}
      {!data && !failed && <p className="field-hint">Loading...</p>}
      {data?.customer && (
        <>
          <div className="lc-customer">
            <Avatar user={data.customer} photoPath={photoPath(data.customer)} size={56} />
            <div>
              <strong>{data.customer.name}</strong>
              <div className="muted">{data.customer.email}</div>
              {data.customer.phone && <div className="muted">{data.customer.phone}</div>}
              {data.customer.verified !== undefined && <div className="muted">{data.customer.verified ? "Email verified" : "Email not verified"}</div>}
            </div>
          </div>

          <h4 className="lc-info-sub">Orders</h4>
          {!data.canSeeOrders ? (
            <p className="field-hint">Your account cannot view orders.</p>
          ) : data.orders.length === 0 ? (
            <p className="field-hint">No orders yet.</p>
          ) : (
            <ul className="lc-orders">
              {data.orders.map((o) => (
                <li key={o.id} className={o.linked ? "linked" : ""}>
                  <div className="lc-order-top">
                    <span className="mono">{o.orderNumber}</span>
                    {o.linked && <span className="status-pill req-pending">This chat</span>}
                  </div>
                  <div className="lc-order-line"><span className={`status-pill status-${o.status}`}>{o.statusLabel}</span> <span className="muted">{formatDate(o.createdAt)}</span></div>
                  <div className="lc-order-line">Payment: {o.paymentMethod} &middot; <span className={`pay-pill pay-${o.paymentStatus}`}>{o.paymentStatusLabel}</span></div>
                  <div className="lc-order-line">{o.confirmed ? "Order confirmed" : o.status === "cancelled" ? "Order cancelled" : "Awaiting confirmation"}</div>
                  <ul className="lc-order-items">{o.items.map((i, n) => <li key={n}>{i.name} <span className="muted">x {i.quantity}</span></li>)}</ul>
                  <div className="lc-order-line"><strong>{peso(o.total)}</strong></div>
                  {data.canOpenOrders && (
                    <button type="button" className="btn btn-outline btn-sm" onClick={() => navigate(`/admin/orders?order=${o.id}`)}>Open order</button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </aside>
  );
}
