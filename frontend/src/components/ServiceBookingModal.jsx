import { useState } from "react";
import client from "../api/client";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { peso } from "../utils/format";

export default function ServiceBookingModal({ service, area, onClose, onBooked }) {
  const { user } = useAuth();
  const showToast = useToast();
  const [form, setForm] = useState({
    name: user?.name || "",
    phone: user?.phone || "",
    address: user?.address?.line1 || "",
    preferredDate: "",
    notes: "",
  });
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  function update(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      await client.post(`/api/services/${service.id}/bookings`, { ...form, areaId: area.id });
      showToast("Service request sent. We will confirm it with you.", "success");
      onBooked();
    } catch (err) {
      setError(err.response?.data?.error || "Could not send your request. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h3 style={{ margin: 0, fontSize: 19 }}>Request {service.name}</h3>
          <button type="button" className="modal-close" onClick={onClose}>&times;</button>
        </div>
        <div className="modal-body">
          <div className="alert alert-info">
            {area.areaName} &middot; <strong>{peso(area.price)}</strong>. This sends a service request; it is not a product purchase.
          </div>
          {error && <div className="alert alert-error">{error}</div>}
          <form onSubmit={handleSubmit}>
            <div className="field"><label>Full Name</label><input required value={form.name} onChange={(e) => update("name", e.target.value)} /></div>
            <div className="field"><label>Contact Number</label><input required placeholder="09xx xxx xxxx" value={form.phone} onChange={(e) => update("phone", e.target.value)} /></div>
            <div className="field"><label>Service Address</label><input required maxLength={255} value={form.address} onChange={(e) => update("address", e.target.value)} /></div>
            <div className="field">
              <label>Preferred Date (optional)</label>
              <input type="date" min={new Date().toISOString().slice(0, 10)} value={form.preferredDate} onChange={(e) => update("preferredDate", e.target.value)} />
            </div>
            <div className="field"><label>Notes (optional)</label><textarea rows="3" maxLength={500} value={form.notes} onChange={(e) => update("notes", e.target.value)} /></div>
            <div className="form-actions">
              <button type="button" className="btn btn-outline" onClick={onClose}>Cancel</button>
              <button type="submit" className="btn btn-primary" disabled={saving}>{saving ? "Sending..." : "Send Request"}</button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
