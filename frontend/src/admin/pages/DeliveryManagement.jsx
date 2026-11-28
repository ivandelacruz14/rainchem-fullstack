import { useEffect, useState } from "react";
import client from "../../api/client";
import { useToast } from "../../context/ToastContext";
import { useAdminAuth } from "../../context/AdminAuthContext";
import PrintStickerButton from "../../components/PrintStickerButton";
import { peso, formatDate } from "../../utils/format";

/** The order path, in order: confirmed -> print the sticker -> send to a rider -> delivered (or failed and rescheduled). */
const TABS = [
  { key: "send", label: "1. To send to rider", help: "Confirmed orders. Print the sticker, choose the rider, then send it." },
  { key: "riders", label: "2. With riders", help: "Orders already with a rider and out for delivery." },
  { key: "awaiting", label: "Failed, to confirm", help: "Riders reported these as failed. Confirm each one and set the new delivery date." },
  { key: "rescheduled", label: "Rescheduled", help: "Failed deliveries with their new delivery date." },
  { key: "delivered", label: "Delivered", help: "Completed deliveries, with the rider, time, note, and photo." },
];

export default function DeliveryManagement() {
  const { can } = useAdminAuth();
  const canManage = can("manage_orders");
  const [tab, setTab] = useState("send");
  const [items, setItems] = useState(null);
  const [riders, setRiders] = useState([]);
  const [error, setError] = useState("");
  const [refresh, setRefresh] = useState(0);
  const activeTab = TABS.find((t) => t.key === tab);

  useEffect(() => {
    client.get("/api/admin/orders/riders").then((r) => setRiders(r.data.riders)).catch(() => setRiders([]));
  }, []);

  useEffect(() => {
    let active = true;
    setError("");
    setItems(null);
    let request;
    if (tab === "send" || tab === "riders") {
      request = client.get("/api/admin/dispatch").then((r) => r.data.orders.filter((o) => (tab === "send" ? !o.riderId : !!o.riderId)));
    } else if (tab === "delivered") {
      request = client.get("/api/admin/delivered-orders").then((r) => r.data.orders);
    } else {
      request = client.get("/api/admin/failed-deliveries", { params: { tab } }).then((r) => r.data.items);
    }
    Promise.resolve(request)
      .then((list) => { if (active) setItems(list); })
      .catch((err) => { if (active) { setItems([]); setError(err.response?.data?.error || "The list could not be loaded. Check your connection and refresh."); } });
    return () => { active = false; };
  }, [tab, refresh]);

  const reload = () => setRefresh((n) => n + 1);

  return (
    <div className="dm-page">
      <header className="dm-header">
        <p className="dm-kicker">Sales and orders</p>
        <h2 className="dm-title">Delivery Management</h2>
        <p className="dm-sub">{activeTab.help}</p>
      </header>

      <nav className="dm-tabs" role="tablist" aria-label="Delivery management tabs">
        {TABS.map((t) => (
          <button key={t.key} type="button" role="tab" aria-selected={tab === t.key}
            className={`dm-tab ${tab === t.key ? "active" : ""}`} onClick={() => setTab(t.key)}>
            {t.label}
          </button>
        ))}
      </nav>

      <div className="dm-toolbar">
        <button type="button" className="btn btn-outline btn-sm" onClick={reload}>Refresh</button>
      </div>

      {error && <div className="alert alert-error" role="alert">{error}</div>}
      {items === null && <div className="loading-state" role="status"><span className="spinner" /> Loading...</div>}
      {items && items.length === 0 && !error && (
        <div className="empty-state"><strong>Nothing here</strong><span>{emptyText(tab)}</span></div>
      )}

      {items && items.length > 0 && tab === "send" && (
        <Table headers={["Order", "Customer", "Status", "Payment", "Cash to collect", "Sticker", "Rider"]}>
          {items.map((o) => (
            <tr key={o.id}>
              <td className="dm-strong">{o.orderNumber}</td>
              <td>{o.customerName}<div className="dm-muted">{o.customerPhone}</div></td>
              <td>{o.statusLabel}</td>
              <td>{o.paymentMethod}</td>
              <td className="num">{o.codAmount > 0 ? peso(o.codAmount) : "Paid"}</td>
              <td><PrintStickerButton orderId={o.id} /></td>
              <td className="dm-act">{canManage ? <SendToRider order={o} riders={riders} onDone={reload} /> : <span className="dm-muted">View only</span>}</td>
            </tr>
          ))}
        </Table>
      )}

      {items && items.length > 0 && tab === "riders" && (
        <Table headers={["Order", "Customer", "Rider", "Estimated date", "Status", "Cash to collect", "Sticker"]}>
          {items.map((o) => (
            <tr key={o.id}>
              <td className="dm-strong">{o.orderNumber}</td>
              <td>{o.customerName}</td>
              <td>{o.riderName || "-"}{o.riderPhone && <div className="dm-muted">{o.riderPhone}</div>}</td>
              <td>{o.estimatedDate ? formatDate(o.estimatedDate).split(",").slice(0, 2).join(",") : "-"}</td>
              <td>{o.statusLabel}</td>
              <td className="num">{o.codAmount > 0 ? peso(o.codAmount) : "Paid"}</td>
              <td><PrintStickerButton orderId={o.id} /></td>
            </tr>
          ))}
        </Table>
      )}

      {items && items.length > 0 && tab === "awaiting" && (
        <Table headers={["Order", "Customer", "Rider", "Reason", "Failed on", "Action"]}>
          {items.map((i) => (
            <tr key={i.orderId}>
              <td className="dm-strong">{i.orderNumber}</td>
              <td>{i.customerName}<div className="dm-muted">{i.customerPhone}</div></td>
              <td>{i.rider || "-"}</td>
              <td className="dm-reason">{i.failedReason}</td>
              <td>{i.failedAt ? formatDate(i.failedAt) : "-"}</td>
              <td className="dm-act">{canManage ? <ConfirmFailed item={i} onDone={reload} /> : <span className="dm-muted">View only</span>}</td>
            </tr>
          ))}
        </Table>
      )}

      {items && items.length > 0 && tab === "rescheduled" && (
        <Table headers={["Order", "Customer", "Rider", "New delivery date", "Reason"]}>
          {items.map((i) => (
            <tr key={i.orderId}>
              <td className="dm-strong">{i.orderNumber}</td>
              <td>{i.customerName}</td>
              <td>{i.rider || "-"}</td>
              <td className="dm-strong">{i.rescheduledFor || "-"}</td>
              <td className="dm-reason">{i.failedReason}</td>
            </tr>
          ))}
        </Table>
      )}

      {items && items.length > 0 && tab === "delivered" && (
        <Table headers={["Order", "Customer", "Rider", "Total", "Payment", "Delivered", "Note", "Photo"]}>
          {items.map((o) => (
            <tr key={o.id}>
              <td className="dm-strong">{o.orderNumber}</td>
              <td>{o.customerName || "-"}</td>
              <td>{o.riderName || "-"}</td>
              <td>{peso(o.total)}</td>
              <td>{o.paymentMethod}</td>
              <td>{o.deliveredAt ? formatDate(o.deliveredAt) : "-"}</td>
              <td className="dm-reason">{o.deliveryNote || "-"}</td>
              <td>{o.hasPhoto ? <ProofButton orderId={o.id} /> : <span className="dm-muted">No photo</span>}</td>
            </tr>
          ))}
        </Table>
      )}
    </div>
  );
}

function emptyText(tab) {
  if (tab === "send") return "No confirmed orders are waiting to be sent to a rider.";
  if (tab === "riders") return "No orders are with a rider right now.";
  if (tab === "awaiting") return "No failed deliveries are waiting for confirmation.";
  return "There is nothing to show in this tab yet.";
}

function Table({ headers, children }) {
  return (
    <div className="dm-table-wrap">
      <table className="dm-table">
        <thead><tr>{headers.map((h) => <th key={h}>{h}</th>)}</tr></thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}

function SendToRider({ order, riders, onDone }) {
  const showToast = useToast();
  const [riderId, setRiderId] = useState("");
  const [eta, setEta] = useState("");
  const [busy, setBusy] = useState(false);
  const today = new Date().toISOString().slice(0, 10);

  async function send() {
    setBusy(true);
    try {
      await client.post(`/api/admin/orders/${order.id}/assign-rider`, { riderId: Number(riderId), estimatedDate: eta });
      showToast(`${order.orderNumber} sent to the rider.`, "success");
      onDone();
    } catch (err) {
      showToast(err.response?.data?.error || "The order could not be sent.", "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="dm-inline">
      <select value={riderId} onChange={(e) => setRiderId(e.target.value)} aria-label={`Rider for ${order.orderNumber}`}>
        <option value="">Choose a rider</option>
        {riders.map((r) => <option key={r.id} value={r.id}>{r.name}{r.phone ? ` (${r.phone})` : " (no phone)"}</option>)}
      </select>
      <input type="date" min={today} value={eta} onChange={(e) => setEta(e.target.value)} aria-label={`Estimated delivery date for ${order.orderNumber}`} title="Estimated delivery date" />
      <button type="button" className="btn btn-primary btn-sm" disabled={!riderId || !eta || busy} onClick={send}>Send to rider</button>
    </div>
  );
}

function ConfirmFailed({ item, onDone }) {
  const showToast = useToast();
  const [open, setOpen] = useState(false);
  const [date, setDate] = useState("");
  const [busy, setBusy] = useState(false);
  const today = new Date().toISOString().slice(0, 10);

  async function confirm() {
    setBusy(true);
    try {
      await client.post(`/api/admin/orders/${item.orderId}/confirm-failed`, { rescheduledFor: date });
      showToast(`${item.orderNumber} rescheduled for ${date}.`, "success");
      setOpen(false);
      onDone();
    } catch (err) {
      showToast(err.response?.data?.error || "The failed delivery could not be confirmed.", "error");
    } finally {
      setBusy(false);
    }
  }

  if (!open) return <button type="button" className="btn btn-primary btn-sm" onClick={() => setOpen(true)}>Confirm and set date</button>;
  return (
    <div className="dm-inline">
      <label className="dm-inline-label">New date
        <input type="date" min={today} value={date} onChange={(e) => setDate(e.target.value)} />
      </label>
      <button type="button" className="btn btn-primary btn-sm" disabled={!date || busy} onClick={confirm}>Confirm</button>
      <button type="button" className="btn btn-outline btn-sm" onClick={() => setOpen(false)}>Cancel</button>
    </div>
  );
}

function ProofButton({ orderId }) {
  const showToast = useToast();
  const [url, setUrl] = useState(null);
  const [busy, setBusy] = useState(false);

  async function open() {
    setBusy(true);
    try {
      const r = await client.get(`/api/admin/orders/${orderId}/delivery-proof`, { responseType: "blob" });
      setUrl(URL.createObjectURL(r.data));
    } catch {
      showToast("No photo is on file for this order.", "error");
    } finally {
      setBusy(false);
    }
  }
  useEffect(() => () => { if (url) URL.revokeObjectURL(url); }, [url]);

  if (url) {
    return (
      <div className="dm-proof">
        <img src={url} alt="Delivery photo" />
        <button type="button" className="link-btn" onClick={() => { URL.revokeObjectURL(url); setUrl(null); }}>Close</button>
      </div>
    );
  }
  return <button type="button" className="btn btn-outline btn-sm" disabled={busy} onClick={open}>{busy ? "Opening..." : "View photo"}</button>;
}
