import RiderReceiptModal from "../../components/RiderReceiptModal";
import { useEffect, useState } from "react";
import client from "../../api/client";
import { useToast } from "../../context/ToastContext";
import { peso } from "../../utils/format";

/** The rider's own deliveries: start, scan every unit, upload proof, then deliver. The server checks each step. */
export default function RiderDeliveries() {
  const [receiptFor, setReceiptFor] = useState(null);
  const showToast = useToast();
  const [orders, setOrders] = useState(null);
  const [busy, setBusy] = useState(false);
  const [codes, setCodes] = useState({});

  function load() {
    client.get("/api/rider").then((r) => setOrders(r.data.orders)).catch(() => setOrders([]));
  }
  useEffect(() => { load(); }, []);

  async function act(id, path, body, message) {
    setBusy(true);
    try {
      await client.post(`/api/rider/${id}/${path}`, body || {});
      if (message) showToast(message, "success");
      load();
    } catch (err) {
      showToast(err.response?.data?.error || "Something went wrong", "error");
    } finally {
      setBusy(false);
    }
  }

  async function scan(id) {
    const code = (codes[id] || "").trim();
    if (!code) return;
    setCodes((c) => ({ ...c, [id]: "" }));
    try {
      const r = await client.post(`/api/rider/${id}/scan`, { code });
      showToast(r.data.message, r.data.accepted ? "success" : "error");
      load();
    } catch (err) {
      showToast(err.response?.data?.message || err.response?.data?.error || "Scan failed", "error");
    }
  }

  async function uploadProof(id, file) {
    if (!file) return;
    const form = new FormData();
    form.append("image", file);
    setBusy(true);
    try {
      await client.post(`/api/rider/${id}/proof`, form);
      showToast("Proof uploaded", "success");
      load();
    } catch (err) {
      showToast(err.response?.data?.error || "Upload failed", "error");
    } finally {
      setBusy(false);
    }
  }

  if (orders === null) return <p className="field-hint">Loading your deliveries...</p>;
  if (orders.length === 0) return <div className="admin-topbar"><div><h1>My Deliveries</h1><p>No deliveries assigned to you right now.</p></div></div>;

  return (
    <div>
      <div className="admin-topbar"><div><h1>My Deliveries</h1><p>Scan every unit, upload the proof photo, then mark it delivered.</p></div></div>
      {orders.map((o) => {
        const ready = o.missing.length === 0 && o.hasProof;
        return (
          <div className="panel" key={o.id} style={{ marginBottom: 16 }}>
            <strong>{o.orderNumber}</strong> <span className={`status-pill status-${o.status}`}>{o.statusLabel}</span>
            <p style={{ margin: "8px 0" }}>{o.customer.name} · {o.customer.phone}<br />{o.address}</p>
            <button type="button" className="btn btn-outline btn-sm" onClick={() => setReceiptFor(o)}>Receipt and signature</button>
            {o.amountToCollect > 0 && <p><strong>Collect cash: {peso(o.amountToCollect)}</strong></p>}
            <ul style={{ paddingLeft: 18 }}>
              {o.items.map((i) => (
                <li key={`${o.id}-${i.productId}-${i.name}`}>
                  {i.name}: {o.scanned[String(i.productId)] || 0} of {i.quantity} scanned
                </li>
              ))}
            </ul>
            {o.status === "ready_for_delivery" && (
              <button className="btn btn-primary btn-block" disabled={busy} onClick={() => act(o.id, "start", {}, "Delivery started")}>
                Start delivery
              </button>
            )}
            {o.status === "shipped" && (
              <>
                <div className="field">
                  <label htmlFor={`code-${o.id}`}>Scan a product (barcode or QR code)</label>
                  <input id={`code-${o.id}`} autoComplete="off" value={codes[o.id] || ""} autoFocus
                    onChange={(e) => setCodes((c) => ({ ...c, [o.id]: e.target.value }))}
                    onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); scan(o.id); } }}
                    placeholder="Scan here or type the code, then press Enter" />
                </div>
                <div className="field">
                  <label htmlFor={`proof-${o.id}`}>Proof photo {o.hasProof && "(uploaded)"}</label>
                  {!o.hasProof && (
                    <input id={`proof-${o.id}`} type="file" accept="image/jpeg,image/png,image/webp" capture="environment"
                      onChange={(e) => uploadProof(o.id, e.target.files?.[0])} />
                  )}
                </div>
                {o.missing.length > 0 && (
                  <p className="field-hint">Still to scan: {o.missing.map((m) => `${m.name} (${m.scanned}/${m.required})`).join(", ")}</p>
                )}
                <button className="btn btn-primary btn-block" disabled={busy || !ready} onClick={() => act(o.id, "deliver", {}, "Marked delivered")}>
                  Mark delivered
                </button>
              </>
            )}
          </div>
        );
      })}
    {receiptFor && <RiderReceiptModal order={receiptFor} onClose={() => setReceiptFor(null)} onChanged={() => load()} />}
    </div>
  );
}
