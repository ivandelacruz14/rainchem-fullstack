import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";

const LINKS = [
  { to: "/account", label: "Overview", end: true },
  { to: "/account/orders", label: "My Orders" },
  { to: "/account/services", label: "Service Requests" },
  { to: "/account/address", label: "Addresses" },
  { to: "/account/profile", label: "Profile" },
  { to: "/account/settings", label: "Settings & Privacy" },
  { to: "/account/help", label: "Help Center" },
];

export default function AccountLayout() {
  const { logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    navigate("/", { replace: true });
    logout();
  }

  return (
    <div className="container account-shell">
      <nav className="account-nav" aria-label="Account">
        {LINKS.map((link) => (
          <NavLink key={link.to} to={link.to} end={link.end} className={({ isActive }) => (isActive ? "active" : "")}>
            {link.label}
          </NavLink>
        ))}
      </nav>
      <main className="account-main">
        <Outlet />
      </main>
      <div className="account-logout">
        <button type="button" className="btn btn-outline" onClick={handleLogout}>Log Out</button>
      </div>
    </div>
  );
}
