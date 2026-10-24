import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { useAdminAuth } from "../context/AdminAuthContext";
import Brand from "../components/Brand";
import ThemeToggle from "../components/ThemeToggle";

const NAV_ITEMS = [
  { group: "Overview", links: [{ to: "/admin", label: "Dashboard", end: true, headOnly: true }] },
  {
    group: "Catalog & Sales",
    links: [
      { to: "/admin/products", label: "Products", permission: "manage_products" },
      { to: "/admin/services", label: "Services", permission: "manage_services" },
      { to: "/admin/orders", label: "Orders", permission: "view_orders" },
      { to: "/admin/users", label: "Users", headOnly: true },
      { to: "/admin/analytics", label: "Sales Analytics", permission: "view_sales" },
    ],
  },
  {
    group: "AI / RAG Chatbot",
    links: [
      { to: "/admin/knowledge", label: "Knowledge Base", headOnly: true },
      { to: "/admin/monitor", label: "Chat Monitor", headOnly: true },
    ],
  },
  {
    group: "System",
    links: [
      { to: "/admin/payments", label: "Payment Settings", headOnly: true },
      { to: "/admin/accounts", label: "Accounts & Roles", headOnly: true },
    ],
  },
];

export default function AdminLayout() {
  const { admin, logout, can } = useAdminAuth();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => setSidebarOpen(false), [pathname]);

  function handleLogout() {
    logout();
    navigate("/admin/login");
  }

  const visible = (link) => (link.headOnly ? admin.isHead : can(link.permission));

  return (
    <div className="admin-shell">
      <header className="admin-topbar-mobile">
        <button type="button" className="btn btn-outline btn-sm" aria-expanded={sidebarOpen} onClick={() => setSidebarOpen((v) => !v)}>
          {sidebarOpen ? "Close" : "Menu"}
        </button>
        <span className="admin-topbar-title">Rainchem Admin</span>
      </header>
      {sidebarOpen && <div className="admin-backdrop" onClick={() => setSidebarOpen(false)} />}

      <aside className={`admin-sidebar ${sidebarOpen ? "open" : ""}`}>
        <div className="brand"><Brand height={90} onDark /></div>
        {NAV_ITEMS.map((section) => {
          const links = section.links.filter(visible);
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
                </NavLink>
              ))}
            </div>
          );
        })}
        <div className="sidebar-foot">
          <div className="sidebar-user">
            Signed in as<br /><strong>{admin?.name}</strong>
            <span className="badge">{admin?.role}</span>
          </div>
          <div className="sidebar-theme">
            <ThemeToggle className="sidebar-theme-btn" />
            <span>Dark / light mode</span>
          </div>
          <button type="button" className="admin-nav-link danger" onClick={handleLogout}>Log Out</button>
        </div>
      </aside>
      <main className="admin-main">
        <Outlet />
      </main>
    </div>
  );
}
