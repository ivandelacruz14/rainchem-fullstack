import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useCart } from "../context/CartContext";
import { useTheme } from "../context/ThemeContext";
import { useUI } from "../context/UIContext";
import { useToast } from "../context/ToastContext";
import UserAvatar from "./UserAvatar";

export default function AccountMenu() {
  const { user, logout } = useAuth();
  const { totalQty } = useCart();
  const { theme, toggleTheme } = useTheme();
  const { openCart } = useUI();
  const showToast = useToast();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const [open, setOpen] = useState(false);
  const rootRef = useRef(null);

  useEffect(() => setOpen(false), [pathname]);

  useEffect(() => {
    if (!open) return undefined;
    function onPointerDown(event) {
      if (rootRef.current && !rootRef.current.contains(event.target)) setOpen(false);
    }
    function onKeyDown(event) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("touchstart", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("touchstart", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  function go(path) {
    setOpen(false);
    navigate(path);
  }

  function handleLogout() {
    setOpen(false);
    logout();
    navigate("/", { replace: true });
    showToast("You have been logged out", "success");
  }

  const dark = theme === "dark";
  const firstName = (user.name || "Account").split(" ")[0];

  return (
    <div className="account-menu" ref={rootRef}>
      <button
        type="button" className="account-chip" aria-haspopup="menu" aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <UserAvatar user={user} size={34} />
        <span className="account-chip-name">{firstName}</span>
        <svg className="account-chip-caret" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
          <path d="m6 9 6 6 6-6" />
        </svg>
        {totalQty > 0 && <span className="cart-badge">{totalQty}</span>}
      </button>

      {open && (
        <div className="account-dropdown" role="menu">
          <div className="account-dropdown-head">
            <strong>{user.name}</strong>
            <span>{user.email}</span>
          </div>
          <button type="button" role="menuitem" className="account-dropdown-item" onClick={() => go("/account")}>My Account</button>
          <button type="button" role="menuitem" className="account-dropdown-item" onClick={() => go("/account/orders")}>My Orders</button>
          <button type="button" role="menuitem" className="account-dropdown-item" onClick={() => { setOpen(false); openCart(); }}>
            <span>Cart</span>
            {totalQty > 0 && <span className="account-dropdown-count">{totalQty}</span>}
          </button>
          <button type="button" role="menuitemcheckbox" aria-checked={dark} className="account-dropdown-item" onClick={toggleTheme}>
            <span>Dark Mode</span>
            <span className={`switch ${dark ? "on" : ""}`} aria-hidden="true"><span /></span>
          </button>
          <button type="button" role="menuitem" className="account-dropdown-item danger" onClick={handleLogout}>Log Out</button>
        </div>
      )}
    </div>
  );
}
