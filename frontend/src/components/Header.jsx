import { useEffect, useState } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useCart } from "../context/CartContext";
import { useUI } from "../context/UIContext";
import Brand from "./Brand";
import UserMenu from "./UserMenu";

export default function Header() {
  const { user, loading } = useAuth();
  const { requireLogin, openCart } = useUI();
  const { totalQty } = useCart();
  const { pathname } = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    setMenuOpen(false);
  }, [pathname]);

  function openAuth(mode) {
    setMenuOpen(false);
    requireLogin(mode);
  }

  return (
    <header className="site-header">
      <div className="header-inner">
        <Link to="/" className="brand">
          <Brand variant="wordmark" height={32} />
        </Link>

        <nav className={`nav-links ${menuOpen ? "open" : ""}`} aria-label="Main">
          <NavLink to="/" end>Home</NavLink>
          <NavLink to="/shop">Shop</NavLink>
          <NavLink to="/services">Services</NavLink>
          <NavLink to="/faqs">FAQs</NavLink>
          {user && <NavLink to="/account/orders">My Orders</NavLink>}
          {!user && !loading && (
            <div className="nav-auth-mobile">
              <button type="button" className="btn btn-outline btn-sm" onClick={() => openAuth("login")}>Log In</button>
              <button type="button" className="btn btn-primary btn-sm" onClick={() => openAuth("register")}>Sign Up</button>
            </div>
          )}
        </nav>

        <div className="nav-actions">
          {user ? (
            <>
              <button type="button" className="icon-btn cart-btn" aria-label="Cart" title="Cart" onClick={openCart}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="9" cy="20" r="1.5" />
                  <circle cx="18" cy="20" r="1.5" />
                  <path d="M2 3h3l2.6 12.4a2 2 0 0 0 2 1.6h8.7a2 2 0 0 0 2-1.6L22 7H6" />
                </svg>
                {totalQty > 0 && <span className="chip-badge">{totalQty}</span>}
              </button>
              <UserMenu />
            </>
          ) : (
            !loading && (
              <div className="auth-buttons">
                <button type="button" className="btn btn-outline btn-sm" onClick={() => openAuth("login")}>Log In</button>
                <button type="button" className="btn btn-primary btn-sm" onClick={() => openAuth("register")}>Sign Up</button>
              </div>
            )
          )}
          <button
            type="button" className="icon-btn nav-toggle" aria-label="Menu" aria-expanded={menuOpen}
            onClick={() => setMenuOpen((v) => !v)}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              {menuOpen ? <path d="M6 6l12 12M18 6L6 18" /> : <path d="M3 6h18M3 12h18M3 18h18" />}
            </svg>
          </button>
        </div>
      </div>
    </header>
  );
}
