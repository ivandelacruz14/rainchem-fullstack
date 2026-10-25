import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import client from "../api/client";
import { useAdminAuth } from "../context/AdminAuthContext";
import Brand from "../components/Brand";
import ThemeToggle from "../components/ThemeToggle";

const NAV_ITEMS = [
  { group: "Overview", links: [{ to: "/admin", label: "Dashboard", end: true }] },
  {
    group: "Catalog & Sales",
    links: [
      { to: "/admin/products", label: "Products", permission: "products" },
      { to: "/admin/approvals", label: "Approvals", permission: "products", badge: true },
      { to: "/admin/sales", label: "Sales & Discounts", permission: "products" },
      { to: "/admin/services", label: "Services", permission: "services" },
      { to: "/admin/orders", label: "Orders", permission: "orders" },
      { to: "/admin/users", label: "Users", permission: "customers" },
      { to: "/admin/analytics", label: "Sales Analytics", permission: "analytics" },
    ],
  },
  {
    group: "AI / RAG Chatbot",
    links: [
      { to: "/admin/knowledge", label: "Knowledge Base", permission: "chatbot" },
      { to: "/admin/monitor", label: "Chat Monitor", permission: "chatbot" },
    ],
  },
  {
    group: "System",
    links: [
      { to: "/admin/payments", label: "Payment Settings", headOnly: true },
      { to: "/admin/accounts", label: "Admin Accounts", headOnly: true },
    ],
  },
];

export default function AdminLayout() {
  const { admin, logout, can } = useAdminAuth();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [pending, setPending] = useState(0);

  useEffect(() => {
    if (!admin || !can("products")) return undefined;
    const load = () => client.get("/api/admin/approvals/pending-count").then((res) => setPending(res.data.count)).catch(() => {});
    load();
    window.addEventListener("rainchem:approvals-changed", load);
    return () => window.removeEventListener("rainchem:approvals-changed", load);
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
          return (
            <div key={section.group}>
              <div className="admin-nav-group">{section.group}</div>
              {links.map((link) => (
                <NavLink
                  key={link.to} to={link.to} end={link.end}
                  className={({ isActive }) => `admin-nav-link ${isActive ? "active" : ""}`}
                >
                  {link.label}
                  {link.badge && pending > 0 && <span className="nav-badge">{pending}</span>}
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
        <Outlet />
      </main>
    </div>
  );
}
