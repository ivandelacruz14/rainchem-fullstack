import { useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useCart } from "../context/CartContext";
import { useTheme } from "../context/ThemeContext";
import { useUI } from "../context/UIContext";
import UserAvatar from "./UserAvatar";

export default function UserMenu() {
  const { user, logout } = useAuth();
  const { totalQty } = useCart();
  const { theme, toggleTheme } = useTheme();
  const { openCart } = useUI();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const [open, setOpen] = useState(false);
  const rootRef = useRef(null);

  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!open) return undefined;
    function onPointerDown(event) {
      if (rootRef.current && !rootRef.current.contains(event.target)) setOpen(false);
    }
    function onKey(event) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  function handleLogout() {
    setOpen(false);
    navigate("/", { replace: true });
    logout();
  }

  const firstName = (user.name || "Account").split(" ")[0];
  const dark = theme === "dark";

  return (
    <div className="user-menu" ref={rootRef}>
      <button
        type="button" className="account-chip" aria-haspopup="menu" aria-expanded={open}
        aria-label="Account menu" onClick={() => setOpen((v) => !v)}
      >
        <UserAvatar user={user} size={36} />
        <span className="account-chip-name">{firstName}</span>
        {totalQty > 0 && <span className="chip-badge">{totalQty}</span>}
      </button>

      {open && (
        <div className="user-menu-panel" role="menu">
          <div className="user-menu-head">
            <strong>{user.name}</strong>
            <span>{user.email}</span>
          </div>
          <Link role="menuitem" to="/account" className="user-menu-item">My Account</Link>
          <Link role="menuitem" to="/account/orders" className="user-menu-item">My Orders</Link>
          <Link role="menuitem" to="/account/services" className="user-menu-item">Service Requests</Link>
          <button role="menuitem" type="button" className="user-menu-item" onClick={() => { setOpen(false); openCart(); }}>
            <span>Cart</span>
            {totalQty > 0 && <span className="menu-count">{totalQty}</span>}
          </button>
          <button
            role="menuitemcheckbox" aria-checked={dark} type="button" className="user-menu-item"
            onClick={toggleTheme}
          >
            <span>Dark mode</span>
            <span className={`switch ${dark ? "on" : ""}`} aria-hidden="true"><span /></span>
          </button>
          <button role="menuitem" type="button" className="user-menu-item danger" onClick={handleLogout}>
            Log Out
          </button>
        </div>
      )}
    </div>
  );
}
