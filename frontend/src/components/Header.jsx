import { useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useCart } from "../context/CartContext";
import { useUI } from "../context/UIContext";
import Brand from "./Brand";
import UserAvatar from "./UserAvatar";
import ThemeToggle from "./ThemeToggle";

export default function Header() {
  const { user } = useAuth();
  const { totalQty } = useCart();
  const { openCart, requireLogin } = useUI();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);

  function handleAccountClick() {
    setMenuOpen(false);
    if (!user) {
      requireLogin("login");
      return;
    }
    navigate("/account");
  }

  function handleOrdersClick() {
    setMenuOpen(false);
    if (!user) {
      requireLogin("login", "Please sign in to see your orders");
      return;
    }
    navigate("/account/orders");
  }

  function closeMenu() {
    setMenuOpen(false);
  }

  return (
    <header className="site-header">
      <div className="header-inner">
        <Link to="/" className="brand" onClick={closeMenu}>
          <Brand variant="wordmark" height={32} />
        </Link>

        <nav className={`nav-links ${menuOpen ? "open" : ""}`}>
          <NavLink to="/" end onClick={closeMenu}>Home</NavLink>
          <NavLink to="/shop" onClick={closeMenu}>Shop</NavLink>
          <NavLink to="/services" onClick={closeMenu}>Services</NavLink>
          <a href="/account/orders" className={window.location.pathname.startsWith("/account/orders") ? "active" : ""} onClick={(e) => { e.preventDefault(); handleOrdersClick(); }}>My Orders</a>
          <NavLink to="/faqs" onClick={closeMenu}>FAQs</NavLink>
        </nav>

        <div className="nav-actions">
          <ThemeToggle />
          {user ? (
            <button className="account-chip" title="My Account" onClick={handleAccountClick}>
              <UserAvatar user={user} size={36} />
              <span className="account-chip-name">{(user.name || "Account").split(" ")[0]}</span>
            </button>
          ) : (
            <button className="icon-btn" title="Log In" onClick={handleAccountClick}>
              <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="8" r="4" /><path d="M4 20c0-4 4-6 8-6s8 2 8 6" />
              </svg>
            </button>
          )}
          <button className="icon-btn" title="Cart" onClick={() => { closeMenu(); openCart(); }}>
            <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="9" cy="21" r="1" /><circle cx="19" cy="21" r="1" />
              <path d="M1 1h4l2.6 13.4a2 2 0 0 0 2 1.6h9.8a2 2 0 0 0 2-1.6L23 6H6" />
            </svg>
            {totalQty > 0 && <span className="cart-badge">{totalQty}</span>}
          </button>
          <button className="icon-btn nav-toggle" title="Menu" onClick={() => setMenuOpen((v) => !v)}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              {menuOpen ? (
                <path d="M6 6l12 12M18 6L6 18" />
              ) : (
                <path d="M3 6h18M3 12h18M3 18h18" />
              )}
            </svg>
          </button>
        </div>
      </div>
    </header>
  );
}