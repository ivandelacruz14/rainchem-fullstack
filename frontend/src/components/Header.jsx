import { useEffect, useState } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useUI } from "../context/UIContext";
import Brand from "./Brand";
import AccountMenu from "./AccountMenu";

export default function Header() {
  const { user } = useAuth();
  const { requireLogin } = useUI();
  const { pathname, search } = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);
  const returnTo = pathname + search;

  useEffect(() => setMenuOpen(false), [pathname]);

  function openAuth(mode) {
    setMenuOpen(false);
    requireLogin(mode, null, returnTo);
  }

  return (
    <header className="site-header">
      <div className="header-inner">
        <Link to="/" className="brand" onClick={() => setMenuOpen(false)}>
          <Brand variant="wordmark" height={32} />
        </Link>

        <nav className={`nav-links ${menuOpen ? "open" : ""}`} aria-label="Main">
          <NavLink to="/" end>Home</NavLink>
          <NavLink to="/shop">Shop</NavLink>
          <NavLink to="/services">Services</NavLink>
          <NavLink to="/faqs">FAQs</NavLink>
          {!user && (
            <div className="nav-auth-mobile">
              <button type="button" className="btn btn-outline btn-sm" onClick={() => openAuth("login")}>Log In</button>
              <button type="button" className="btn btn-primary btn-sm" onClick={() => openAuth("register")}>Sign Up</button>
            </div>
          )}
        </nav>

        <div className="nav-actions">
          {user ? (
            <AccountMenu />
          ) : (
            <div className="auth-actions">
              <button type="button" className="btn btn-outline btn-sm" onClick={() => openAuth("login")}>Log In</button>
              <button type="button" className="btn btn-primary btn-sm auth-signup" onClick={() => openAuth("register")}>Sign Up</button>
            </div>
          )}
          <button
            type="button" className="icon-btn nav-toggle" aria-label="Toggle navigation" aria-expanded={menuOpen}
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
