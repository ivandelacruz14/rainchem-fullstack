import { Link } from "react-router-dom";
import { useUI } from "../context/UIContext";

export default function Footer() {
  const { toggleChat } = useUI();

  return (
    <footer className="site-footer">
      <div className="container">
        <div className="footer-grid">
          <div>
            <div className="brand" style={{ color: "#fff", marginBottom: 12 }}>
              <span className="dot"></span>Rain<span className="sub">chem</span>
            </div>
            <p style={{ fontSize: 13.5, maxWidth: 280 }}>
              RAIMOL engine oil, RadCool coolant, and maintenance essentials, plus an AI assistant
              trained on our own product knowledge. 100% Filipino-owned since 1995.
            </p>
          </div>
          <div>
            <h5>Shop</h5>
            <ul>
              <li><a href="/#shop">Oils &amp; Fluids</a></li>
              <li><a href="/#shop">Coolant</a></li>
              <li><a href="/#shop">Filters</a></li>
              <li><a href="/#shop">Brakes</a></li>
            </ul>
          </div>
          <div>
            <h5>Support</h5>
            <ul>
              <li><a href="/#faq">FAQ</a></li>
              <li><button className="link-btn" onClick={toggleChat}>Chat with AI</button></li>
              <li><Link to="/account">Track an Order</Link></li>
            </ul>
          </div>
          <div>
            <h5>Contact</h5>
            <ul>
              <li>cs@raincheminternational.com</li>
              <li>(02) 8888 6531</li>
              <li>Paranaque City, Metro Manila</li>
            </ul>
          </div>
        </div>
        <div className="footer-bottom">
          <span>&copy; 2026 Rainchem. All rights reserved.</span>
          <span>Prices in PHP</span>
        </div>
      </div>
    </footer>
  );
}
