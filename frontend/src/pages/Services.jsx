import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import client from "../api/client";
import ServiceCard from "../components/ServiceCard";
import ServiceBookingModal from "../components/ServiceBookingModal";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { useUI } from "../context/UIContext";

const AREA_KEY = "rainchem_service_area";

export default function Services() {
  const { user } = useAuth();
  const { requireLogin } = useUI();
  const showToast = useToast();
  const navigate = useNavigate();

  const [areas, setAreas] = useState([]);
  const [area, setArea] = useState(() => localStorage.getItem(AREA_KEY) || "");
  const [services, setServices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [booking, setBooking] = useState(null);

  useEffect(() => {
    client.get("/api/services/areas").then((res) => {
      setAreas(res.data.areas);
      // A remembered area that no service offers any more is dropped.
      setArea((current) => (current && !res.data.areas.includes(current) ? "" : current));
    }).catch(() => {});
  }, []);

  useEffect(() => {
    setLoading(true);
    client.get("/api/services", { params: area ? { area } : {} })
      .then((res) => { setServices(res.data.services); setError(false); })
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [area]);

  function chooseArea(value) {
    setArea(value);
    if (value) localStorage.setItem(AREA_KEY, value);
    else localStorage.removeItem(AREA_KEY);
  }

  function handleBook(service) {
    if (!user) {
      requireLogin("login", "Please log in to request a service", "/services");
      return;
    }
    setBooking(service);
  }

  function handleBooked() {
    setBooking(null);
    showToast("Request sent. We will confirm it with you.", "success");
    navigate("/account/services");
  }

  return (
    <div className="container" style={{ paddingBottom: 80 }}>
      <div className="page-hero">
        <div className="eyebrow">Rainchem Service Bays</div>
        <h1>Services near you</h1>
        <p>Prices and availability depend on where you are. Pick your area to see what is offered and what it costs.</p>
      </div>

      <div className="area-picker">
        <label htmlFor="service-area">Your area</label>
        <select id="service-area" value={area} onChange={(e) => chooseArea(e.target.value)}>
          <option value="">Select your area</option>
          {areas.map((name) => <option key={name} value={name}>{name}</option>)}
        </select>
        {areas.length === 0 && !loading && <span className="field-hint">No service areas have been set up yet.</span>}
      </div>

      {error ? (
        <div className="alert alert-error">Services could not be loaded. Please try again in a moment.</div>
      ) : loading ? null : services.length === 0 ? (
        <div className="empty-state">No services are available right now.</div>
      ) : (
        <div className="service-grid-list">
          {services.map((service) => (
            <ServiceCard key={service.id} service={service} area={area} onBook={handleBook} />
          ))}
        </div>
      )}

      {booking && (
        <ServiceBookingModal service={booking} area={area} onClose={() => setBooking(null)} onBooked={handleBooked} />
      )}
    </div>
  );
}
