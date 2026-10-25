import { useState } from "react";
import client from "../api/client";
import { useAuth } from "../context/AuthContext";
import { peso } from "../utils/format";

export default function ServiceBookingModal({ service, area, onClose, onBooked }) {
  const { user } = useAuth();
  const selected = service.selected;
  const [form, setForm] = useState({
    name: user?.name || "", phone: user?.phone || "", email: user?.email || "",
    address: user?.address?.line1 || "", preferredDate: "", notes: "",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function update(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function submit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      // Only the service and area are sent as choices. The server looks up the price itself.
      const res = await client.post("/api/services/bookings", { serviceId: service.id, area, ...form });
      onBooked(res.data.booking);
    } catch (err) {
      setError(err.response?.data?.error || "Could not send your request. Please try again.");
      setBusy(false);
    }
  }

  const today = new Date().toISOString().slice(0, 10);

  return (
    <div className="overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h3 style={{ margin: 0, fontSize: 19 }}>Request {service.name}</h3>
          <button type="button" className="modal-close" onClick={onClose}>&times;</button>
        </div>
        <form className="modal-body" onSubmit={submit}>
          <div className="service-status ok" style={{ marginBottom: 14 }}>
            <span className="service-price">{peso(selected.price)}</span>
            <span>{area}. Payment is arranged when the service is done.</span>
          </div>
          {error && <div className="alert alert-error">{error}</div>}
          <div className="field"><label>Full name</label><input required value={form.name} onChange={(e) => update("name", e.target.value)} /></div>
          <div className="field-row">
            <div className="field"><label>Contact number</label><input required value={form.phone} onChange={(e) => update("phone", e.target.value)} placeholder="09xx xxx xxxx" /></div>
            <div className="field"><label>Email</label><input type="email" value={form.email} onChange={(e) => update("email", e.target.value)} /></div>
          </div>
          <div className="field"><label>Address for the service</label><input required value={form.address} onChange={(e) => update("address", e.target.value)} /></div>
          <div className="field"><label>Preferred date (optional)</label><input type="date" min={today} value={form.preferredDate} onChange={(e) => update("preferredDate", e.target.value)} /></div>
          <div className="field"><label>Notes (optional)</label><textarea rows={2} maxLength={500} value={form.notes} onChange={(e) => update("notes", e.target.value)} /></div>
          <button type="submit" className="btn btn-primary btn-block" disabled={busy}>{busy ? "Sending..." : "Send request"}</button>
        </form>
      </div>
    </div>
  );
}
