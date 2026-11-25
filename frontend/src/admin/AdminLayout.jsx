import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import client from "../api/client";
import { useAdminAuth } from "../context/AdminAuthContext";
import Brand from "../components/Brand";
import ThemeToggle from "../components/ThemeToggle";

const NAV_ITEMS = [
  { group: "Overview", links: [{ to: "/admin", label: "Overview", end: true }] },
  {
    group: "Catalog & Sales",
    links: [
      { to: "/admin/products", label: "Products", permission: "products" },
      { to: "/admin/approvals", label: "Approvals", permission: "products", badge: true },
      { to: "/admin/sales", label: "Sales & Discounts", permission: "products" },
      { to: "/admin/services", label: "Services", permission: "services" },
      { to: "/admin/orders", label: "Orders", permission: "orders", ordersBadge: true },
      { to: "/admin/delivery-confirmations", label: "Delivery Confirmation", permission: "orders" },
      { to: "/admin/users", label: "Users", permission: "customers" },
      { to: "/admin/sales-records", label: "Sales Records", permission: "analytics" },
      { to: "/admin/analytics", label: "Sales Analytics", permission: "analytics" },
      { to: "/admin/inventory", label: "Inventory Alerts", permission: "products", inventoryBadge: true },
    ],
  },
  {
    group: "AI / RAG Chatbot",
    links: [
      { to: "/admin/live-chat", label: "Live Chat", permission: "livechat", liveBadge: true },
      { to: "/admin/knowledge", label: "Knowledge Base", permission: "chatbot" },
      { to: "/admin/product-knowledge", label: "Product Knowledge", permission: "chatbot" },
      { to: "/admin/monitor", label: "Chat Monitor", permission: "chatbot" },
    ],
  },
  {
    group: "System",
    links: [
      { to: "/admin/account", label: "My Account" },
      { to: "/admin/payments", label: "Payment Settings", headOnly: true },
      { to: "/admin/accounts", label: "Admin Accounts", headOnly: true },
    ],
  },
];

export default function AdminLayout() {
  const { admin, logout, can, warningSeconds, extendSession } = useAdminAuth();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [pending, setPending] = useState(0);
  const [liveUnread, setLiveUnread] = useState(0);
  const [alerts, setAlerts] = useState(0);
  const [ordersWaiting, setOrdersWaiting] = useState(0);
  const [openGroups, setOpenGroups] = useState({});

  useEffect(() => {
    if (!admin || !can("products")) return undefined;
    client.get("/api/admin/inventory/alerts/count").then((res) => setAlerts(res.data.open)).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [admin?.id, pathname]);

  useEffect(() => {
    if (!admin || !can("livechat")) return undefined;
    const load = () => {
      if (document.visibilityState === "hidden") return;
      client.get("/api/admin/live-chat/unread-count").then((res) => setLiveUnread(res.data.unread)).catch(() => {});
    };
    load();
    const timer = setInterval(load, 10000);
    return () => clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [admin?.id, pathname]);

  useEffect(() => {
    if (!admin || !can("products")) return undefined;
    const load = () => client.get("/api/admin/approvals/pending-count").then((res) => setPending(res.data.count)).catch(() => {});
    load();
    window.addEventListener("rainchem:approvals-changed", load);
    return () => window.removeEventListener("rainchem:approvals-changed", load);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [admin?.id, pathname]);

  useEffect(() => {
    if (!admin || !can("orders") || admin.role === "Rider") return undefined;
    const load = () => {
      if (document.visibilityState === "hidden") return;
      client.get("/api/admin/orders/attention-count").then((res) => setOrdersWaiting(res.data.count)).catch(() => {});
    };
    load();
    const timer = setInterval(load, 15000);
    return () => clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [admin?.id, pathname]);

  useEffect(() => setSidebarOpen(false), [pathname]);

  useEffect(() => {
    document.body.classList.toggle("no-scroll", sidebarOpen);
    return () => document.body.classList.remove("no-scroll");
  }, [sidebarOpen]);

  function handleLogout() {
    navigate("/admin/login", { replace: true });
    logout();
  }

  const allowed = (link) => (link.headOnly ? admin?.isHead : link.permission ? can(link.permission) : true);

  return (
    <div className="admin-shell">
      <header className="admin-mobilebar">
        <button type="button" className="btn btn-outline btn-sm" aria-label="Open menu" aria-expanded={sidebarOpen} onClick={() => setSidebarOpen((v) => !v)}>
          &#9776; Menu
        </button>
        <span className="admin-mobilebar-title">Admin Console</span>
      </header>

      {sidebarOpen && <div className="admin-backdrop" onClick={() => setSidebarOpen(false)} />}

      <aside className={`admin-sidebar ${sidebarOpen ? "open" : ""}`}>
        <div className="brand"><Brand height={90} onDark /></div>
        {NAV_ITEMS.map((section) => {
          const links = section.links.filter(allowed);
          if (links.length === 0) return null;
          const open = openGroups[section.group] !== false;
          return (
            <div className="admin-nav-section" key={section.group}>
              <button type="button" className="admin-nav-group admin-nav-group-btn" aria-expanded={open}
                onClick={() => setOpenGroups((g) => ({ ...g, [section.group]: !open }))}>
                <span>{section.group}</span>
                <span className={`admin-nav-chevron ${open ? "open" : ""}`} aria-hidden="true">&#9662;</span>
              </button>
              {open && links.map((link) => (
                <NavLink
                  key={link.to} to={link.to} end={link.end}
                  className={({ isActive }) => `admin-nav-link ${isActive ? "active" : ""}`}
                >
                  {link.label}
                  {link.ordersBadge && ordersWaiting > 0 && <span className="nav-badge">{ordersWaiting}</span>}
                  {link.badge && pending > 0 && <span className="nav-badge">{pending}</span>}
                  {link.liveBadge && liveUnread > 0 && <span className="nav-badge">{liveUnread}</span>}
                  {link.inventoryBadge && alerts > 0 && <span className="nav-badge">{alerts}</span>}
                </NavLink>
              ))}
            </div>
          );
        })}
        <div className="sidebar-foot">
          <div className="sidebar-user">
            Signed in as<br /><strong>{admin?.name}</strong>
            <span className="sidebar-role">{admin?.role}</span>
          </div>
          <div className="sidebar-theme">
            <ThemeToggle className="theme-toggle sidebar-theme-btn" />
            <span>Dark / light mode</span>
          </div>
          <button type="button" className="admin-nav-link logout" onClick={handleLogout}>Log Out</button>
        </div>
      </aside>

      <main className="admin-main">
        {ordersWaiting > 0 && (
          <div className="admin-alert" role="alert">
            <strong>{ordersWaiting} new order{ordersWaiting === 1 ? "" : "s"} waiting for your confirmation.</strong>
            <NavLink to="/admin/orders" className="admin-alert-link">Review now</NavLink>
          </div>
        )}
        <Outlet />
      </main>

      {warningSeconds !== null && (
        <div className="overlay" role="alertdialog" aria-modal="true" aria-label="Your session is about to expire">
          <div className="modal confirm-dialog">
            <div className="modal-head"><h3 style={{ margin: 0, fontSize: 18 }}>Your session is about to expire</h3></div>
            <div className="modal-body">
              <p style={{ marginTop: 0 }}>
                You will be signed out in <strong>{warningSeconds}</strong> seconds due to inactivity.
              </p>
              <div className="form-actions">
                <button type="button" className="btn btn-outline" onClick={() => { navigate("/admin/login", { replace: true }); logout(); }}>Sign out</button>
                <button type="button" className="btn btn-primary" onClick={extendSession}>Stay signed in</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
