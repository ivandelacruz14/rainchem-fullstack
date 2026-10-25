import { useEffect, useState } from "react";
import client from "../../api/client";
import { useAdminAuth } from "../../context/AdminAuthContext";
import { useToast } from "../../context/ToastContext";
import { formatDate, peso } from "../../utils/format";

const EMPTY_AREA = { name: "", price: "", isAvailable: true, notes: "" };
const EMPTY_FORM = { name: "", category: "", description: "", requirements: "", isActive: true, ownerId: "", areas: [{ ...EMPTY_AREA }] };
const NEXT_STATUS = { requested: ["confirmed", "cancelled"], confirmed: ["completed", "cancelled"], completed: [], cancelled: [] };

function AreaRows({ areas, onChange }) {
  function update(index, patch) {
    onChange(areas.map((a, i) => (i === index ? { ...a, ...patch } : a)));
  }
  return (
    <div className="area-editor">
      {areas.map((area, index) => (
        <div className="area-row" key={area.id || `new-${index}`}>
          <input aria-label="Area name" placeholder="Area (e.g. Quezon City)" value={area.name} onChange={(e) => update(index, { name: e.target.value })} />
          <input aria-label="Price" type="number" min="0" step="0.01" placeholder="Price" value={area.price} onChange={(e) => update(index, { price: e.target.value })} />
          <label className="perm-item">
            <input type="checkbox" checked={area.isAvailable} onChange={(e) => update(index, { isAvailable: e.target.checked })} />
            <span>Available</span>
          </label>
          <button type="button" className="icon-action wide" onClick={() => onChange(areas.filter((_, i) => i !== index))}>Remove</button>
        </div>
      ))}
      <button type="button" className="btn btn-outline btn-sm" onClick={() => onChange([...areas, { ...EMPTY_AREA }])}>+ Add area</button>
    </div>
  );
}

export default function AdminServices() {
  const { admin } = useAdminAuth();
  const showToast = useToast();
  const [tab, setTab] = useState("services");
  const [services, setServices] = useState([]);
  const [distributors, setDistributors] = useState([]);
  const [bookings, setBookings] = useState([]);
  const [editing, setEditing] = useState(null); // service or "new"
  const [form, setForm] = useState(EMPTY_FORM);
  const [busy, setBusy] = useState(false);

  function loadServices() {
    client.get("/api/admin/services").then((res) => {
      setServices(res.data.services);
      setDistributors(res.data.distributors || []);
    });
  }
  function loadBookings() {
    client.get("/api/admin/services/bookings").then((res) => setBookings(res.data.bookings));
  }
  useEffect(() => { loadServices(); loadBookings(); }, []);

  function openForm(service) {
    setEditing(service || "new");
    setForm(service ? {
      name: service.name, category: service.category || "", description: service.description,
      requirements: service.requirements || "", isActive: service.isActive, ownerId: service.ownerId || "",
      areas: service.areas.map((a) => ({ id: a.id, name: a.name, price: a.price, isAvailable: a.available, notes: a.notes || "" })),
    } : { ...EMPTY_FORM, areas: [{ ...EMPTY_AREA }] });
  }

  async function save(e) {
    e.preventDefault();
    const payload = {
      name: form.name, category: form.category, description: form.description, requirements: form.requirements,
      isActive: form.isActive, areas: form.areas.filter((a) => a.name.trim() || a.price !== ""),
    };
    if (!admin?.isScoped) payload.ownerId = form.ownerId ? Number(form.ownerId) : null;
    setBusy(true);
    try {
      if (editing === "new") await client.post("/api/admin/services", payload);
      else await client.put(`/api/admin/services/${editing.id}`, payload);
      showToast("Service saved", "success");
      setEditing(null);
      loadServices();
    } catch (err) {
      showToast(err.response?.data?.error || "Could not save this service", "error");
    } finally {
      setBusy(false);
    }
  }

  async function toggleActive(service) {
    try {
      await client.put(`/api/admin/services/${service.id}`, { isActive: !service.isActive });
      loadServices();
    } catch (err) {
      showToast(err.response?.data?.error || "Could not update this service", "error");
    }
  }

  async function remove(service) {
    if (!window.confirm(`Delete "${service.name}"? This cannot be undone.`)) return;
    try {
      await client.delete(`/api/admin/services/${service.id}`);
      showToast("Service deleted", "success");
      loadServices();
    } catch (err) {
      showToast(err.response?.data?.error || "Could not delete this service", "error");
    }
  }

  async function setStatus(booking, status) {
    try {
      await client.post(`/api/admin/services/bookings/${booking.id}/status`, { status });
      loadBookings();
    } catch (err) {
      showToast(err.response?.data?.error || "Could not update this booking", "error");
    }
  }

  const ownerName = (id) => (id ? distributors.find((d) => d.id === id)?.name || "Distributor" : "Head office");

  return (
    <div>
      <div className="admin-topbar">
        <div>
          <h1>Services</h1>
          <p>Set where each service is offered and what it costs in each area.</p>
        </div>
        <button type="button" className="btn btn-primary" onClick={() => openForm(null)}>+ Add Service</button>
      </div>

      <div className="tab-bar">
        <button type="button" className={`tab-btn ${tab === "services" ? "active" : ""}`} onClick={() => setTab("services")}>Services</button>
        <button type="button" className={`tab-btn ${tab === "bookings" ? "active" : ""}`} onClick={() => setTab("bookings")}>
          Requests{bookings.filter((b) => b.status === "requested").length > 0 && ` (${bookings.filter((b) => b.status === "requested").length})`}
        </button>
      </div>

      {tab === "services" && (
        services.length === 0 ? (
          <div className="admin-panel empty-state">No services yet. Add one and choose the areas where it is offered.</div>
        ) : (
          services.map((s) => (
            <div className="admin-panel" key={s.id}>
              <div className="panel-head">
                <div>
                  <h3 style={{ margin: 0 }}>{s.name} {!s.isActive && <span className="pill pill-low">Off</span>}</h3>
                  <p className="field-hint" style={{ margin: "2px 0 0" }}>
                    {s.category || "No category"}{!admin?.isScoped && ` \u00b7 ${ownerName(s.ownerId)}`}
                  </p>
                </div>
                <div className="row-actions">
                  <button type="button" className="icon-action wide" onClick={() => openForm(s)}>Edit</button>
                  <button type="button" className="icon-action wide" onClick={() => toggleActive(s)}>{s.isActive ? "Turn off" : "Turn on"}</button>
                  <button type="button" className="icon-action wide" onClick={() => remove(s)}>Delete</button>
                </div>
              </div>
              <p style={{ margin: "0 0 10px", color: "var(--muted)" }}>{s.description}</p>
              <div className="table-wrap">
                <table className="admin-table">
                  <thead><tr><th>Area</th><th>Price</th><th>Availability</th></tr></thead>
                  <tbody>
                    {s.areas.length === 0 ? <tr><td colSpan={3}>No areas yet, so customers cannot see this service.</td></tr> : s.areas.map((a) => (
                      <tr key={a.id}><td>{a.name}</td><td>{peso(a.price)}</td><td>{a.available ? "Available" : <span className="pill pill-low">Unavailable</span>}</td></tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))
        )
      )}

      {tab === "bookings" && (
        <div className="admin-panel">
          <div className="table-wrap">
            <table className="admin-table stack">
              <thead><tr><th>Reference</th><th>Service</th><th>Area</th><th>Price</th><th>Customer</th><th>Preferred</th><th>Status</th><th></th></tr></thead>
              <tbody>
                {bookings.length === 0 ? <tr><td colSpan={8}>No service requests yet.</td></tr> : bookings.map((b) => (
                  <tr key={b.id}>
                    <td data-label="Reference" className="mono">{b.bookingNumber}<div className="muted">{formatDate(b.createdAt).split(",")[0]}</div></td>
                    <td data-label="Service" className="cell-name">{b.serviceName}</td>
                    <td data-label="Area">{b.area}</td>
                    <td data-label="Price">{peso(b.price)}</td>
                    <td data-label="Customer" className="cell-wrap">{b.customer.name}<div className="muted">{b.customer.phone}</div><div className="muted">{b.address}</div>{b.notes && <div className="muted">Note: {b.notes}</div>}</td>
                    <td data-label="Preferred">{b.preferredDate || "-"}</td>
                    <td data-label="Status"><span className={`status-pill booking-${b.status}`}>{b.statusLabel}</span></td>
                    <td data-label="" className="row-cell">
                      <div className="row-actions">
                        {NEXT_STATUS[b.status].map((next) => (
                          <button type="button" key={next} className="icon-action wide" onClick={() => setStatus(b, next)}>{next[0].toUpperCase() + next.slice(1)}</button>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {editing && (
        <div className="overlay" onClick={() => setEditing(null)}>
          <div className="modal wide" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head">
              <h3 style={{ margin: 0 }}>{editing === "new" ? "Add service" : "Edit service"}</h3>
              <button type="button" className="modal-close" onClick={() => setEditing(null)}>&times;</button>
            </div>
            <form className="modal-body" onSubmit={save}>
              <div className="field-row">
                <div className="field"><label>Service name</label><input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
                <div className="field"><label>Category (optional)</label><input value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} /></div>
              </div>
              <div className="field"><label>Description</label><textarea required rows={3} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></div>
              <div className="field"><label>Requirements or conditions (optional)</label><textarea rows={2} value={form.requirements} onChange={(e) => setForm({ ...form, requirements: e.target.value })} /></div>
              {!admin?.isScoped && (
                <div className="field">
                  <label>Assigned to</label>
                  <select value={form.ownerId} onChange={(e) => setForm({ ...form, ownerId: e.target.value })}>
                    <option value="">Head office</option>
                    {distributors.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
                  </select>
                </div>
              )}
              <div className="field">
                <label>Areas and prices</label>
                <p className="field-hint" style={{ marginTop: 0 }}>Set the exact price for each area. Untick Available to stop offering it there without deleting it.</p>
                <AreaRows areas={form.areas} onChange={(areas) => setForm({ ...form, areas })} />
              </div>
              <label className="perm-item" style={{ marginBottom: 12 }}>
                <input type="checkbox" checked={form.isActive} onChange={(e) => setForm({ ...form, isActive: e.target.checked })} />
                <span>Service is switched on</span>
              </label>
              <div className="form-actions">
                <button type="button" className="btn btn-outline" onClick={() => setEditing(null)}>Cancel</button>
                <button type="submit" className="btn btn-primary" disabled={busy}>{busy ? "Saving..." : "Save service"}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
