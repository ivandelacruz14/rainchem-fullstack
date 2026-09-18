import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";

export default function AccountLayout() {
  const { logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/");
  }

  return (
    <div className="container account-shell">
      <div className="account-nav">
        <NavLink to="/account" end className={({ isActive }) => (isActive ? "active" : "")}>Overview</NavLink>
        <NavLink to="/account/orders" className={({ isActive }) => (isActive ? "active" : "")}>My Orders</NavLink>
        <NavLink to="/account/track" className={({ isActive }) => (isActive ? "active" : "")}>Track Order</NavLink>
        <NavLink to="/account/address" className={({ isActive }) => (isActive ? "active" : "")}>Addresses</NavLink>
        <NavLink to="/account/profile" className={({ isActive }) => (isActive ? "active" : "")}>Profile</NavLink>
        <button onClick={handleLogout} style={{ color: "var(--red-700)", marginTop: 10 }}>Log Out</button>
      </div>
      <div>
        <Outlet />
      </div>
    </div>
  );
}
