import { useEffect, useState } from "react";
import client from "../../api/client";
import { useToast } from "../../context/ToastContext";
import { peso, formatDate } from "../../utils/format";

/** Cash on delivery: what each rider collected, what the office has received, and what is still with the rider.
 *  Also how many deliveries each rider completed and failed. */
export default function CodRemittance() {
  const showToast = useToast();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [picked, setPicked] = useState({});   // order id -> true
  const [busy, setBusy] = useState(false);

  function load() {
    client.get("/api/admin/remittances")
      .then((r) => { setData(r.data); setError(""); })
      .catch((err) => setError(err.response?.data?.error || "The cash report could not be loaded."));
  }
  useEffect(load, []);

  const toggle = (id) => setPicked((p) => ({ ...p, [id]: !p[id] }));
  const allFor = (rider, on) => setPicked((p) => {
    const next = { ...p };
    rider.pending.forEach((o) => { next[o.id] = on; });
    return next;
  });
  const chosenIds = Object.keys(picked).filter((id) => picked[id]).map(Number);

  async function receive(ids) {
    if (!ids.length) return;
    setBusy(true);
    try {
      const r = await client.post("/api/admin/remittances/receive", { orderIds: ids });
      showToast(`Recorded ${peso(r.data.amount)} received (${r.data.received} order${r.data.received === 1 ? "" : "s"}).`, "success");
      setPicked({});
      load();
    } catch (err) {
      showToast(err.response?.data?.error || "That could not be saved.", "error");
    } finally {
      setBusy(false);
    }
  }

  if (error) return <div className="alert alert-error" role="alert">{error}</div>;
  if (!data) return <p className="field-hint">Loading the cash report...</p>;

  return (
    <div className="dc-page">
      <header>
        <p className="eyebrow">Sales and orders</p>
        <h1>Cash on Delivery</h1>
        <p className="field-hint">The rider records the cash at the door. When the rider hands it to the office, tick the orders and press Mark as received.</p>
      </header>

      <div className="rd-cards" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12 }}>
        <div className="admin-panel" style={{ padding: 14 }}><span className="muted">Collected by riders</span><h2>{peso(data.totals.collected)}</h2></div>
        <div className="admin-panel" style={{ padding: 14 }}><span className="muted">Received by the office</span><h2>{peso(data.totals.remitted)}</h2></div>
        <div className="admin-panel" style={{ padding: 14 }}><span className="muted">Still with riders</span><h2>{peso(data.totals.outstanding)}</h2></div>
      </div>

      {data.riders.length === 0 && <p className="field-hint">No riders yet. Add one in Admin Accounts with the Rider role.</p>}

      {data.riders.map((rider) => (
        <section key={rider.riderId} className="admin-panel" style={{ padding: 16, display: "grid", gap: 10 }} aria-label={`Cash of ${rider.riderName}`}>
          <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", gap: 8 }}>
            <div>
              <h2 style={{ margin: 0 }}>{rider.riderName}{!rider.isActive && <span className="pill pill-low"> Disabled</span>}</h2>
              <span className="muted">{rider.phone || "No phone number"} · Delivered {rider.delivered} · Failed {rider.failed}</span>
            </div>
            <div style={{ textAlign: "right" }}>
              <div>Collected {peso(rider.collected)} · Received {peso(rider.remitted)}</div>
              <strong>Still with the rider: {peso(rider.outstanding)}</strong>
            </div>
          </div>
          {rider.pending.length > 0 && (
            <>
              <div className="table-wrap">
                <table className="admin-table stack">
                  <thead><tr>
                    <th><input type="checkbox" aria-label={`Select all orders of ${rider.riderName}`}
                      checked={rider.pending.every((o) => picked[o.id])} onChange={(e) => allFor(rider, e.target.checked)} /></th>
                    <th>Order</th><th>Customer</th><th>Delivered</th><th>Cash</th>
                  </tr></thead>
                  <tbody>
                    {rider.pending.map((o) => (
                      <tr key={o.id}>
                        <td><input type="checkbox" aria-label={`Select ${o.orderNumber}`} checked={Boolean(picked[o.id])} onChange={() => toggle(o.id)} /></td>
                        <td data-label="Order" className="mono">{o.orderNumber}</td>
                        <td data-label="Customer">{o.customer}</td>
                        <td data-label="Delivered">{o.deliveredAt ? formatDate(o.deliveredAt) : "-"}</td>
                        <td data-label="Cash">{peso(o.amount)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div>
                <button type="button" className="btn btn-primary btn-sm" disabled={busy || !rider.pending.some((o) => picked[o.id])}
                  onClick={() => receive(rider.pending.filter((o) => picked[o.id]).map((o) => o.id))}>
                  Mark selected as received
                </button>
              </div>
            </>
          )}
        </section>
      ))}
      {chosenIds.length > 0 && <p className="field-hint" role="status">{chosenIds.length} order(s) selected.</p>}
    </div>
  );
}
