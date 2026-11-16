import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";

const Icon = ({ d }) => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d={d} />
  </svg>
);

const LINKS = [
  { to: "/account", label: "Overview", end: true, icon: "M3 12l9-9 9 9M5 10v10h14V10" },
  { to: "/account/profile", label: "My Profile", icon: "M20 21a8 8 0 0 0-16 0M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z" },
  { to: "/account/orders", label: "My Orders", icon: "M6 2h9l5 5v15H6zM14 2v6h6M9 13h6M9 17h6" },
  { to: "/track", label: "Track My Order", icon: "M1 3h15v13H1zM16 8h4l3 3v5h-7zM5.5 18.5a2 2 0 1 0 0 .01M18.5 18.5a2 2 0 1 0 0 .01" },
  { to: "/account/address", label: "My Addresses", icon: "M21 10c0 7-9 13-9 13S3 17 3 10a9 9 0 0 1 18 0zM12 10m-3 0a3 3 0 1 0 6 0 3 3 0 1 0-6 0" },
  { to: "/account/settings", label: "Settings & Privacy", icon: "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z" },
  { to: "/account/help", label: "Help & Support", icon: "M9 9a3 3 0 1 1 4 2.8c-.7.3-1 1-1 1.7M12 17h.01M12 22a10 10 0 1 1 0-20 10 10 0 0 1 0 20z" },
];

export default function AccountLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    navigate("/", { replace: true });
    logout();
  }

  return (
    <div className="acct-page">
      <div className="acct-shell">
        <aside className="acct-side" aria-label="My Account menu">
          <div className="acct-side-user">
            <div className="acct-side-avatar">
              {user?.avatarPhoto ? <img src={user.avatarPhoto} alt="" /> : <span>{(user?.name || "?").charAt(0).toUpperCase()}</span>}
            </div>
            <div className="acct-side-name">{user?.name}</div>
            <div className="acct-side-email">{user?.email}</div>
          </div>
          <nav className="acct-nav">
            {LINKS.map((link) => (
              <NavLink key={link.to} to={link.to} end={link.end} className={({ isActive }) => (isActive ? "active" : "")}>
                <Icon d={link.icon} />
                <span>{link.label}</span>
              </NavLink>
            ))}
          </nav>
          <button type="button" className="acct-logout" onClick={handleLogout}>
            <Icon d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9" />
            <span>Logout</span>
          </button>
        </aside>

        <main className="acct-main">
          {user && user.accountTypeChosen === false && (
            <div className="account-banner" role="status">
              <strong>Tell us about your account.</strong> Is it for personal use or a business? Choose it in{" "}
              <NavLink to="/account/profile">My Profile</NavLink>.
            </div>
          )}
          <Outlet />
        </main>
      </div>
    </div>
  );
}
