import { useEffect, useState } from "react";
import client from "../api/client";
import { useAuth } from "../context/AuthContext";
import { useUI } from "../context/UIContext";
import { peso, formatDate } from "../utils/format";
import ServiceBookingModal from "../components/ServiceBookingModal";

function ServiceCard({ service, areaName, onRequest }) {
  const area = service.areas.find((a) => a.areaName === areaName);
  let status;
  if (!areaName) status = { label: "Choose a location to see the price", tone: "neutral" };
  else if (!area) status = { label: "Not offered in this location", tone: "bad" };
  else if (!area.isAvailable) status = { label: "Unavailable in this location", tone: "bad" };
  else status = { label: "Available", tone: "ok" };

  const canRequest = area?.isAvailable;

  return (
    <article className="service-card">
      <div className="service-card-top">
        {service.category && <span className="product-cat">{service.category}</span>}
        <span className={`service-status ${status.tone}`}>{status.label}</span>
      </div>
      <h3>{service.name}</h3>
      <p>{service.description}</p>
      {service.requirements && <p className="field-hint"><strong>Requirements:</strong> {service.requirements}</p>}
      {area?.note && <p className="field-hint">{area.note}</p>}
      <div className="service-card-foot">
        <span className="product-price">{canRequest ? peso(area.price) : "\u2014"}</span>
        <button type="button" className="btn btn-primary btn-sm" disabled={!canRequest} onClick={() => onRequest(service, area)}>
          Request service
        </button>
      </div>
    </article>
  );
}

export default function Services() {
  const { user } = useAuth();
  const { requireLogin } = useUI();
  const [data, setData] = useState({ services: [], areas: [] });
  const [loading, setLoading] = useState(true);
  const [areaName, setAreaName] = useState("");
  const [booking, setBooking] = useState(null);
  const [mine, setMine] = useState([]);

  useEffect(() => {
    client.get("/api/services").then((res) => setData(res.data)).finally(() => setLoading(false));
  }, []);

  function loadMine() {
    if (!user) { setMine([]); return; }
    client.get("/api/services/bookings/mine").then((res) => setMine(res.data.bookings)).catch(() => {});
  }
  useEffect(loadMine, [user]);

  function handleRequest(service, area) {
    if (!user) {
      requireLogin("login", "Please log in to request a service", "/services");
      return;
    }
    setBooking({ service, area });
  }

  return (
    <div className="container" style={{ paddingBottom: 80 }}>
      <div className="page-hero">
        <div className="eyebrow">Rainchem Services</div>
        <h1>Services near you</h1>
        <p>Prices and availability depend on your location. Pick where you are to see what applies.</p>
      </div>

      <div className="field service-area-picker">
        <label htmlFor="service-area">Your location</label>
        <select id="service-area" value={areaName} onChange={(e) => setAreaName(e.target.value)}>
          <option value="">Select a location</option>
          {data.areas.map((name) => <option key={name} value={name}>{name}</option>)}
        </select>
      </div>

      {loading ? null : data.services.length === 0 ? (
        <div className="empty-state">No services available right now.</div>
      ) : (
        <div className="service-list">
          {data.services.map((service) => (
            <ServiceCard key={service.id} service={service} areaName={areaName} onRequest={handleRequest} />
          ))}
        </div>
      )}

      {user && mine.length > 0 && (
        <section className="panel" style={{ marginTop: 32 }}>
          <h4>Your service requests</h4>
          <div className="table-wrap">
            <table className="admin-table">
              <thead><tr><th>Service</th><th>Location</th><th>Price</th><th>Status</th><th>Requested</th></tr></thead>
              <tbody>
                {mine.map((b) => (
                  <tr key={b.id}>
                    <td>{b.serviceName}</td><td>{b.areaName}</td><td>{peso(b.price)}</td>
                    <td><span className="badge">{b.status}</span></td>
                    <td>{formatDate(b.createdAt).split(",")[0]}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {booking && (
        <ServiceBookingModal
          service={booking.service} area={booking.area}
          onClose={() => setBooking(null)}
          onBooked={() => { setBooking(null); loadMine(); }}
        />
      )}
    </div>
  );
}
