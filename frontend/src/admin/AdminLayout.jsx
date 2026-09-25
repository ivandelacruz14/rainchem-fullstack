import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useState } from "react";
import { useAdminAuth } from "../context/AdminAuthContext";

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
      { to: "/admin/tester", label: "AI Tester" },
      { to: "/admin/monitor", label: "Chat Monitor" },
    ],
  },
  { group: "System", links: [{ to: "/admin/accounts", label: "Admin Accounts" }] },
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
        <div className="brand"><span className="dot"></span>Rain<span className="sub">chem</span></div>
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
          <div style={{ fontSize: 12, color: "#8a8580", marginBottom: 8 }}>
            Signed in as<br /><strong style={{ color: "#fff" }}>{admin?.name}</strong>
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