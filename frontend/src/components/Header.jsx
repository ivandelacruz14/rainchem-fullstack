import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useCart } from "../context/CartContext";
import { useUI } from "../context/UIContext";

export default function Header() {
  const { user } = useAuth();
  const { totalQty } = useCart();
  const { openCart, requireLogin } = useUI();
  const navigate = useNavigate();

  function handleAccountClick() {
    if (!user) {
      requireLogin("login");
      return;
    }
    navigate("/account");
  }

  return (
    <header className="site-header">
      <div className="header-inner">
        <Link to="/" className="brand">
          <span className="dot"></span>Rain<span className="sub">chem</span>
        </Link>
        <nav className="nav-links">
          <a href="/#home">Home</a>
          <a href="/#shop">Shop</a>
          <a href="/#services">Services</a>
          <a href="/#faq">FAQ</a>
          <a href="/#contact">Contact</a>
        </nav>
        <div className="nav-actions">
          <button className="icon-btn" title={user ? "My Account" : "Log In"} onClick={handleAccountClick}>
            <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="8" r="4" /><path d="M4 20c0-4 4-6 8-6s8 2 8 6" />
            </svg>
          </button>
          <button className="icon-btn" title="Cart" onClick={openCart}>
            <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="9" cy="21" r="1" /><circle cx="19" cy="21" r="1" />
              <path d="M1 1h4l2.6 13.4a2 2 0 0 0 2 1.6h9.8a2 2 0 0 0 2-1.6L23 6H6" />
            </svg>
            {totalQty > 0 && <span className="cart-badge">{totalQty}</span>}
          </button>
        </div>
      </div>
    </header>
  );
}
