import { useEffect, useState } from "react";
import client from "../../api/client";
import { useAdminAuth } from "../../context/AdminAuthContext";
import { useToast } from "../../context/ToastContext";

/** Fulfilment steps for one order. Out for delivery and delivered are set by the rider, not here. */
export default function OrderFulfilment({ order, onChanged }) {
  const { admin } = useAdminAuth();
  const showToast = useToast();
  const [riders, setRiders] = useState([]);
  const [riderId, setRiderId] = useState("");
  const [busy, setBusy] = useState(false);
  const [proofUrl, setProofUrl] = useState(null);
  const [reason, setReason] = useState("");

  useEffect(() => {
    if (order.status !== "ready_for_delivery") return;
    client.get("/api/admin/orders/riders").then((r) => setRiders(r.data.riders)).catch(() => setRiders([]));
  }, [order.status]);

  useEffect(() => {
    if (order.status !== "delivered") return undefined;
    let url = null;
    client.get(`/api/admin/orders/${order.id}/delivery-proof`, { responseType: "blob" })
      .then((r) => { url = URL.createObjectURL(r.data); setProofUrl(url); })
      .catch(() => setProofUrl(null));
    return () => { if (url) URL.revokeObjectURL(url); };
  }, [order.id, order.status]);

  async function run(path, body, message) {
    setBusy(true);
    try {
      await client.post(`/api/admin/orders/${order.id}/${path}`, body);
      showToast(message, "success");
      onChanged();
    } catch (err) {
      showToast(err.response?.data?.error || "Could not update this order", "error");
    } finally {
      setBusy(false);
    }
  }

  const s = order.status;
  return (
    <div className="field" style={{ marginTop: 16 }}>
      <label>Fulfilment</label>
      {s === "confirmed" && (
        <button className="btn btn-outline btn-block" disabled={busy} onClick={() => run("status", { status: "processing" }, "Order is being processed")}>
          Start processing
        </button>
      )}
      {s === "processing" && (
        <button className="btn btn-outline btn-block" disabled={busy} onClick={() => run("status", { status: "ready_for_delivery" }, "Marked ready for delivery")}>
          Mark ready for delivery
        </button>
      )}
      {s === "ready_for_delivery" && (
        <>
          <select value={riderId} onChange={(e) => setRiderId(e.target.value)} aria-label="Rider">
            <option value="">Choose a rider</option>
            {riders.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
          </select>
          <button className="btn btn-primary btn-block" style={{ marginTop: 8 }} disabled={busy || !riderId}
            onClick={() => run("assign-rider", { riderId: Number(riderId) }, "Rider assigned")}>
            Assign rider
          </button>
          {riders.length === 0 && <p className="field-hint">No active rider yet. Add one in Admin Accounts with the Rider role.</p>}
        </>
      )}
      {s === "shipped" && <p className="field-hint">Out for delivery. The rider completes it with scanning and proof.</p>}
      {s === "delivered" && (
        <>
          <p className="field-hint">Delivered by the rider.</p>
          {proofUrl ? <img src={proofUrl} alt="Delivery proof" style={{ maxWidth: "100%", borderRadius: 8, marginTop: 8 }} />
            : <p className="field-hint">No proof image on file.</p>}
          {admin?.isHead && (
            <div style={{ marginTop: 12 }}>
              <label htmlFor="corr-reason">Correction (Head Admin only)</label>
              <input id="corr-reason" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Why is this order not delivered?" />
              <button className="btn btn-outline btn-block" style={{ marginTop: 8 }} disabled={busy || !reason.trim()}
                onClick={() => run("delivery-correction", { status: "shipped", reason: reason.trim() }, "Order moved back to out for delivery")}>
                Move back to out for delivery
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
