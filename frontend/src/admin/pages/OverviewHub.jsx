import { useState } from "react";
import { useAdminAuth } from "../../context/AdminAuthContext";
import Overview from "./Overview";
import RiderDeliveries from "./RiderDeliveries";

const DASHBOARD_PERMISSIONS = ["orders", "manage_orders", "analytics", "products", "services", "customers", "chatbot", "livechat"];

/** The Overview page: the dashboard and the rider's deliveries, as two tabs on one screen. */
export default function OverviewHub() {
  const { admin, can } = useAdminAuth();
  const hasDashboard = Boolean(admin?.isHead) || DASHBOARD_PERMISSIONS.some((k) => can(k));
  const hasDeliveries = admin?.role === "Rider" && can("deliveries");
  const tabs = [
    ...(hasDashboard ? [["dashboard", "Dashboard"]] : []),
    ...(hasDeliveries ? [["deliveries", "My Deliveries"]] : []),
  ];
  const [tab, setTab] = useState(hasDashboard ? "dashboard" : "deliveries");
  if (tabs.length === 0) {
    return <div className="alert alert-info">Your account has no dashboard or deliveries. Ask the Head Admin for the permissions you need.</div>;
  }
  const active = tabs.some(([key]) => key === tab) ? tab : tabs[0][0];
  return (
    <div>
      <div className="tab-bar" role="tablist" aria-label="Overview">
        {tabs.map(([key, label]) => (
          <button key={key} type="button" role="tab" aria-selected={active === key}
            className={`tab-btn ${active === key ? "active" : ""}`} onClick={() => setTab(key)}>
            {label}
          </button>
        ))}
      </div>
      {active === "dashboard" ? <Overview /> : <RiderDeliveries />}
    </div>
  );
}
