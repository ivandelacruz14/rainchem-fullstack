import { useCallback, useEffect, useState } from "react";
import client from "../../api/client";
import { useToast } from "../../context/ToastContext";
import { peso, formatDate } from "../../utils/format";

const EMPTY_SERVICE = { name: "", category: "", description: "", requirements: "", isActive: true };
const EMPTY_AREA = { areaName: "", price: "", note: "", isAvailable: true };
const BOOKING_STATUSES = ["requested", "confirmed", "completed", "cancelled"];

function AreaRow({ service, area, onChanged }) {
  const showToast = useToast();
  const [price, setPrice] = useState(String(area.price));

  async function save(changes) {
    try {
      const res = await client.put(`/api/admin/services/${service.id}/areas/${area.id}`, changes);
      onChanged(res.data.service);
    } catch (err) {
      showToast(err.response?.data?.error || "Could not update this area", "error");
    }
  }

  async function remove() {
    if (!window.confirm(`Remove ${area.areaName}?`)) return;
    try {
      const res = await client.delete(`/api/admin/services/${service.id}/areas/${area.id}`);
      onChanged(res.data.service);
    } catch (err) {
      showToast(err.response?.data?.error || "Could not remove this area", "error");
    }
  }

  return (
    <tr>
      <td className="strong wrap-cell">{area.areaName}</td>
      <td>
        <input className="inline-input" type="number" min="0" step="0.01" value={price} onChange={(e) => setPrice(e.target.value)} />
      </td>
      <td>
        <label className="check-row compact">
          <input type="checkbox" checked={area.isAvailable} onChange={(e) => save({ isAvailable: e.target.checked })} />
          <span>{area.isAvailable ? "Available" : "Unavailable"}</span>
        </label>
      </td>
      <td>
        <div className="row-actions">
          <button type="button" className="icon-action" disabled={Number(price) === area.price} onClick={() => save({ price: Number(price) })}>Save price</button>
          <button type="button" className="icon-action" onClick={remove}>Remove</button>
        </div>
      </td>
    </tr>
  );
}

function ServiceEditor({ service, onChanged, onEdit }) {
  const showToast = useToast();
  const [area, setArea] = useState(EMPTY_AREA);

  async function addArea(e) {
    e.preventDefault();
    try {
      const res = await client.post(`/api/admin/services/${service.id}/areas`, { ...area, price: Number(area.price) });
      onChanged(res.data.service);
      setArea(EMPTY_AREA);
    } catch (err) {
      showToast(err.response?.data?.error || "Could not add this area", "error");
    }
  }

  async function toggleActive() {
    try {
      const res = await client.put(`/api/admin/services/${service.id}`, { isActive: !service.isActive });
      onChanged(res.data.service);
    } catch (err) {
      showToast(err.response?.data?.error || "Could not update this service", "error");
    }
  }

  return (
    <div className="admin-panel">
      <div className="panel-head">
        <div>
          <h3 style={{ margin: 0 }}>{service.name} {!service.isActive && <span className="badge">Disabled</span>}</h3>
          <p className="field-hint">{service.category || "No category"} &middot; {service.description}</p>
          {service.requirements && <p className="field-hint">Requirements: {service.requirements}</p>}
        </div>
        <div className="row-actions">
          <button type="button" className="btn btn-outline btn-sm" onClick={() => onEdit(service)}>Edit details</button>
          <button type="button" className="btn btn-outline btn-sm" onClick={toggleActive}>{service.isActive ? "Disable" : "Enable"}</button>
        </div>
      </div>

      <div className="table-wrap">
        <table className="admin-table">
          <thead><tr><th>Location / area</th><th>Price (&#8369;)</th><th>Availability</th><th></th></tr></thead>
          <tbody>
            {service.areas.length === 0 && <tr><td colSpan={4}>No areas yet. Customers cannot request this service until you add one.</td></tr>}
            {service.areas.map((a) => <AreaRow key={`${a.id}-${a.price}-${a.isAvailable}`} service={service} area={a} onChanged={onChanged} />)}
          </tbody>
        </table>
      </div>

      <form className="area-form" onSubmit={addArea}>
        <input required placeholder="Location or area" value={area.areaName} onChange={(e) => setArea({ ...area, areaName: e.target.value })} />
        <input required type="number" min="0" step="0.01" placeholder="Price" value={area.price} onChange={(e) => setArea({ ...area, price: e.target.value })} />
        <input placeholder="Note (optional)" value={area.note} onChange={(e) => setArea({ ...area, note: e.target.value })} />
        <button type="submit" className="btn btn-primary btn-sm">Add area</button>
      </form>
    </div>
  );
}

export default function Services() {
  const showToast = useToast();
  const [services, setServices] = useState([]);
  const [bookings, setBookings] = useState([]);
  const [form, setForm] = useState(null);

  const load = useCallback(() => {
    client.get("/api/admin/services").then((res) => setServices(res.data.services));
    client.get("/api/admin/services/bookings").then((res) => setBookings(res.data.bookings));
  }, []);
  useEffect(load, [load]);

  function replaceService(updated) {
    setServices((prev) => prev.map((s) => (s.id === updated.id ? updated : s)));
  }

  async function saveService(e) {
    e.preventDefault();
    try {
      if (form.id) {
        const res = await client.put(`/api/admin/services/${form.id}`, form);
        replaceService(res.data.service);
      } else {
        await client.post("/api/admin/services", form);
        load();
      }
      setForm(null);
      showToast("Service saved", "success");
    } catch (err) {
      showToast(err.response?.data?.error || "Could not save this service", "error");
    }
  }

  async function setBookingStatus(id, status) {
    try {
      await client.post(`/api/admin/services/bookings/${id}/status`, { status });
      load();
    } catch (err) {
      showToast(err.response?.data?.error || "Could not update this request", "error");
    }
  }

  return (
    <div>
      <div className="admin-topbar">
        <div><h1>Services</h1><p>Set where each service is offered and what it costs there. Disabling keeps all booking history.</p></div>
        <button type="button" className="btn btn-primary" onClick={() => setForm(EMPTY_SERVICE)}>+ Add Service</button>
      </div>

      {services.length === 0 && <div className="admin-panel"><p className="field-hint">No services yet.</p></div>}
      {services.map((s) => <ServiceEditor key={s.id} service={s} onChanged={replaceService} onEdit={setForm} />)}

      <div className="admin-panel">
        <h3>Service requests</h3>
        <div className="table-wrap">
          <table className="admin-table">
            <thead><tr><th>Service</th><th>Area</th><th>Price</th><th>Customer</th><th>Preferred</th><th>Status</th></tr></thead>
            <tbody>
              {bookings.length === 0 && <tr><td colSpan={6}>No requests yet.</td></tr>}
              {bookings.map((b) => (
                <tr key={b.id}>
                  <td className="wrap-cell">{b.serviceName}</td>
                  <td className="wrap-cell">{b.areaName}</td>
                  <td>{peso(b.price)}</td>
                  <td className="wrap-cell">{b.contactName}<br /><span className="field-hint">{b.contactPhone} &middot; {b.address}</span></td>
                  <td>{b.preferredDate ? formatDate(b.preferredDate).split(",")[0] : "Any"}</td>
                  <td>
                    <select value={b.status} onChange={(e) => setBookingStatus(b.id, e.target.value)}>
                      {BOOKING_STATUSES.map((st) => <option key={st}>{st}</option>)}
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {form && (
        <div className="overlay" onClick={() => setForm(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head"><h3>{form.id ? "Edit Service" : "Add Service"}</h3><button type="button" className="modal-close" onClick={() => setForm(null)}>&times;</button></div>
            <div className="modal-body">
              <form onSubmit={saveService}>
                <div className="field"><label>Name</label><input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
                <div className="field"><label>Category</label><input value={form.category || ""} onChange={(e) => setForm({ ...form, category: e.target.value })} /></div>
                <div className="field"><label>Description</label><textarea required rows="3" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></div>
                <div className="field"><label>Requirements or conditions</label><textarea rows="2" value={form.requirements || ""} onChange={(e) => setForm({ ...form, requirements: e.target.value })} /></div>
                <div className="form-actions">
                  <button type="button" className="btn btn-outline" onClick={() => setForm(null)}>Cancel</button>
                  <button type="submit" className="btn btn-primary">Save</button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
