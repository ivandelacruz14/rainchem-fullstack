import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useState } from "react";
import { useAdminAuth } from "../context/AdminAuthContext";
import Brand from "../components/Brand";
import ThemeToggle from "../components/ThemeToggle";

const NAV_ITEMS = [
  { group: "Overview", links: [{ to: "/admin", label: "Dashboard", end: true }] },
  {
    group: "Catalog & Sales",
    links: [
      { to: "/admin/products", label: "Products" },
      { to: "/admin/orders", label: "Orders" },
      { to: "/admin/users", label: "Users" },
      { to: "/admin/analytics", label: "Sales Analytics" },
    ],
  },
  {
    group: "AI / RAG Chatbot",
    links: [
      { to: "/admin/knowledge", label: "Knowledge Base" },
      { to: "/admin/monitor", label: "Chat Monitor" },
    ],
  },
  {
    group: "System",
    links: [
      { to: "/admin/payments", label: "Payment Settings" },
      { to: "/admin/accounts", label: "Admin Accounts" },
    ],
  },
];

export default function AdminLayout() {
  const { admin, logout } = useAdminAuth();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  function handleLogout() {
    logout();
    navigate("/admin/login");
  }

  return (
    <div className="admin-shell">
      <aside className={`admin-sidebar ${sidebarOpen ? "open" : ""}`}>
        <div className="brand"><Brand height={90} onDark /></div>
        {NAV_ITEMS.map((section) => (
          <div key={section.group}>
            <div className="admin-nav-group">{section.group}</div>
            {section.links.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                end={link.end}
                className={({ isActive }) => `admin-nav-link ${isActive ? "active" : ""}`}
                onClick={() => setSidebarOpen(false)}
              >
                {link.label}
              </NavLink>
            ))}
          </div>
        ))}
        <div className="sidebar-foot">
          <div style={{ fontSize: 12, color: "var(--soft)", marginBottom: 8 }}>
            Signed in as<br /><strong style={{ color: "#fff" }}>{admin?.name}</strong>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
            <ThemeToggle style={{ width: 36, height: 36, borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center", background: "rgba(255,255,255,.08)", border: "1px solid rgba(255,255,255,.14)", color: "#fff" }} />
            <span style={{ fontSize: 12, color: "#b8b2ac" }}>Dark / light mode</span>
          </div>
          <button className="admin-nav-link" style={{ color: "#ff9a9e" }} onClick={handleLogout}>Log Out</button>
        </div>
      </aside>
      <main className="admin-main">
        <button className="btn btn-outline btn-sm admin-menu-toggle" style={{ marginBottom: 10 }} onClick={() => setSidebarOpen((v) => !v)}>
          ☰ Menu
        </button>
        <Outlet />
      </main>
    </div>
  );
}