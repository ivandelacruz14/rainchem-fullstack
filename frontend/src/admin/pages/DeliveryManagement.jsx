import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import client from "../../api/client";
import { useToast } from "../../context/ToastContext";
import { useAdminAuth } from "../../context/AdminAuthContext";
import StickerDocument from "../../components/StickerDocument";
import { peso, formatDate } from "../../utils/format";

const TABS = [
  { key: "awaiting", label: "Failed deliveries", help: "Riders reported these as failed. Confirm each one and set the new delivery date." },
  { key: "rescheduled", label: "Rescheduled", help: "Confirmed failed deliveries with their new delivery date." },
  { key: "delivered", label: "Delivered", help: "Completed deliveries. Open the photo the rider took." },
  { key: "stickers", label: "Print stickers", help: "Print the QR code and barcode sticker for each order before it goes out." },
];

const STICKER_STATUSES = ["confirmed", "processing", "ready_for_delivery", "rescheduled", "shipped"];

/** Delivery Management: failed deliveries, rescheduling, delivered proof, and package stickers. */
export default function DeliveryManagement() {
  const { can } = useAdminAuth();
  const [tab, setTab] = useState("awaiting");
  const [items, setItems] = useState(null);
  const [error, setError] = useState("");
  const [refresh, setRefresh] = useState(0);
  const activeTab = TABS.find((t) => t.key === tab);
  const canManage = can("manage_orders");

  useEffect(() => {
    let active = true;
    setError("");
    setItems(null);
    const request = tab === "awaiting" || tab === "rescheduled"
      ? client.get("/api/admin/failed-deliveries", { params: { tab } }).then((r) => r.data.items)
      : tab === "delivered"
        ? client.get("/api/admin/delivered-orders").then((r) => r.data.orders)
        : client.get("/api/admin/orders").then((r) => r.data.orders.filter((o) => STICKER_STATUSES.includes(o.status)));
    Promise.resolve(request)
      .then((list) => { if (active) setItems(list); })
      .catch((err) => { if (active) { setItems([]); setError(err.response?.data?.error || "The list could not be loaded. Check your connection and refresh."); } });
    return () => { active = false; };
  }, [tab, refresh]);

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
        <button type="button" className="btn btn-outline btn-sm" onClick={() => setRefresh((n) => n + 1)}>Refresh</button>
      </div>

      {error && <div className="alert alert-error" role="alert">{error}</div>}
      {items === null && <div className="loading-state" role="status"><span className="spinner" /> Loading...</div>}
      {items && items.length === 0 && !error && (
        <div className="empty-state"><strong>Nothing here</strong><span>{tab === "awaiting" ? "No failed deliveries are waiting for confirmation." : "There is nothing to show in this tab yet."}</span></div>
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
              <td className="dm-act">{canManage ? <ConfirmFailed item={i} onDone={() => setRefresh((n) => n + 1)} /> : <span className="dm-muted">View only</span>}</td>
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

      {items && items.length > 0 && tab === "stickers" && (
        <Table headers={["Order", "Customer", "Status", "Payment", "Sticker"]}>
          {items.map((o) => (
            <tr key={o.id}>
              <td className="dm-strong">{o.orderNumber}</td>
              <td>{o.customer?.name || "-"}</td>
              <td>{o.statusLabel}</td>
              <td>{o.paymentMethod}</td>
              <td className="dm-act"><PrintStickerButton orderId={o.id} /></td>
            </tr>
          ))}
        </Table>
      )}
    </div>
  );
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

function PrintStickerButton({ orderId }) {
  const showToast = useToast();
  const [sticker, setSticker] = useState(null);
  const [qrUrl, setQrUrl] = useState(null);
  const [busy, setBusy] = useState(false);

  async function prepare() {
    setBusy(true);
    try {
      const [s, q] = await Promise.all([
        client.get(`/api/admin/orders/${orderId}/sticker`),
        client.get(`/api/admin/orders/${orderId}/receipt/qr.png`, { responseType: "blob" }),
      ]);
      setQrUrl(URL.createObjectURL(q.data));
      setSticker(s.data.sticker);
      setTimeout(() => { window.print(); }, 300);
    } catch (err) {
      showToast(err.response?.data?.error || "The sticker could not be prepared.", "error");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (!sticker) return undefined;
    const t = setTimeout(() => { setSticker(null); if (qrUrl) URL.revokeObjectURL(qrUrl); setQrUrl(null); }, 1500);
    return () => clearTimeout(t);
  }, [sticker, qrUrl]);

  return (
    <>
      <button type="button" className="btn btn-primary btn-sm" disabled={busy} onClick={prepare}>{busy ? "Preparing..." : "Print sticker"}</button>
      {sticker && createPortal(<div className="print-root"><StickerDocument sticker={sticker} qrUrl={qrUrl} /></div>, document.body)}
    </>
  );
}
