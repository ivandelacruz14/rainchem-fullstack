import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";

const TABS = [
  { to: "/account", label: "Overview", end: true },
  { to: "/account/profile", label: "Profile" },
  { to: "/account/address", label: "Addresses" },
  { to: "/account/orders", label: "My Orders" },
  { to: "/account/settings", label: "Settings & Privacy" },
];

// Everything about the account lives inside My Account: profile, addresses, orders, settings, and privacy.
export default function AccountLayout() {
  const { user } = useAuth();

  return (
    <div className="container account-page">
      {user && user.accountTypeChosen === false && (
        <div className="account-banner" role="status">
          <strong>Tell us about your account.</strong> Is it for personal use or a business? Choose it in{" "}
          <NavLink to="/account/profile">Profile</NavLink>.
        </div>
      )}
      <nav className="account-tabs" aria-label="My Account sections">
        {TABS.map((tab) => (
          <NavLink key={tab.to} to={tab.to} end={tab.end} className={({ isActive }) => (isActive ? "active" : "")}>
            {tab.label}
          </NavLink>
        ))}
      </nav>
      <main className="account-main">
        <Outlet />
      </main>
    </div>
  );
}
