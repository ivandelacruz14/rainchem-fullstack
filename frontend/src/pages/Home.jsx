import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import client from "../api/client";
import ProductCard from "../components/ProductCard";
import ProductModal from "../components/ProductModal";
import { CategoryIcon } from "../components/ProductVisual";
import { useUI } from "../context/UIContext";
import { useAuth } from "../context/AuthContext";
import { CATEGORIES } from "../utils/categories";

export default function Home() {
  const HERO_PRODUCT_IMAGE = null;
  const [products, setProducts] = useState([]);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [expandedCategory, setExpandedCategory] = useState(null);
  const [faqs, setFaqs] = useState([]);
  const { requireLogin, toggleChat } = useUI();
  const { user } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    client.get("/api/products").then((res) => setProducts(res.data.products));
    client.get("/api/chat/faq").then((res) => setFaqs(res.data.faqs));
  }, []);

  function openCategory(category) {
    navigate(`/shop?category=${encodeURIComponent(category)}`);
  }

  return (
    <>
      <section className="hero" id="home">
        <div className="container hero-inner">
          <div className="hero-copy">
            <div className="eyebrow">Rainchem International - Since 1995</div>
            <h1>Powering performance. <em>Delivering</em> confidence.</h1>
            <p>
              Maker of RAIMOL engine oil, RadCool coolant, and industrial lubricants, a 100%
              Filipino-owned, ISO-certified lube blending company trusted by riders and
              corporations across the Philippines. Now with an AI assistant trained on our
              own product knowledge.
            </p>
            <div className="hero-cta">
              <Link to="/shop" className="btn btn-primary">Shop Products</Link>
            </div>
            <div className="hero-stats">
              <div className="stat-card"><div className="value">30 Yrs</div><div className="label">Since 1995</div></div>
              <div className="stat-card"><div className="value">ISO</div><div className="label">Certified Blending</div></div>
              <div className="stat-card"><div className="value">24/7</div><div className="label">AI Support</div></div>
            </div>
          </div>
           <div className="hero-visual">
            <div className="hero-ring">
              <img
                className="hero-logo"
                src="/images/raimol-hero.png"
                alt="RAIMOL Motor Oil and Lubricants"
              />
            </div>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="container">
          <div className="section-head">
            <div className="eyebrow">Shop by Category</div>
            <h2>Everything your bike needs, in one place</h2>
            <p>From full-synthetic engine oil to RadCool coolant and wear parts, sourced and tested for Philippine roads and climate.</p>
          </div>
          <div className="category-strip">
            {CATEGORIES.map((cat) => (
              <button key={cat.name} className="cat-card" onClick={() => openCategory(cat.name)}>
                <div className="cat-icon"><CategoryIcon category={cat.name} /></div>
                <h4>{cat.name}</h4>
                <p>{cat.blurb}</p>
              </button>
            ))}
          </div>
        </div>
      </section>

      <section className="section" id="shop" style={{ background: "var(--surface)" }}>
  <div className="container">
    <div className="section-head">
      <div className="eyebrow">Full Catalog</div>
      <h2>Products</h2>
      <p>Browse by category, swipe to see more in each line.</p>
      <Link className="see-all" to="/shop">See all products &rarr;</Link>
    </div>
    {CATEGORIES.map((cat) => {
      const items = products.filter((p) => p.category === cat.name);
      if (items.length === 0) return null;
      return (
        <div className="product-row-block" key={cat.name}>
          <div className="product-row-head">
            <h3>{cat.name}</h3>
            <div className="product-row-head-right">
              <span className="product-row-count">{items.length} item{items.length > 1 ? "s" : ""}</span>
              <Link className="see-all" to={`/shop?category=${encodeURIComponent(cat.name)}`}>See all &rarr;</Link>
            </div>
          </div>
          <div className="product-row">
            {items.map((p) => (
              <div className="product-row-item" key={p.id}>
                <ProductCard product={p} onOpen={setSelectedProduct} />
              </div>
            ))}
          </div>
        </div>
      );
    })}
  </div>
</section>

      <section className="section">
        <div className="container">
          <div className="section-head">
            <div className="eyebrow">Rider Feedback</div>
            <h2>Trusted by everyday commuters and weekend riders</h2>
          </div>
          <div className="testi-grid">
            <div className="testi-card">
              <div className="testi-stars">{"\u2605\u2605\u2605\u2605\u2605"}</div>
              <p>"Switched to RadCool after my radiator kept overheating in traffic. Temps stay stable now even in EDSA gridlock."</p>
              <strong>Marco T.</strong><div>Daily commuter, Quezon City</div>
            </div>
            <div className="testi-card">
              <div className="testi-stars">{"\u2605\u2605\u2605\u2605\u2605"}</div>
              <p>"The AI chat actually answered my question about mixing ratios correctly. Didn't expect that from a shop website."</p>
              <strong>Angeline R.</strong><div>Weekend rider, Cavite</div>
            </div>
            <div className="testi-card">
              <div className="testi-stars">{"\u2605\u2605\u2605\u2605"}</div>
              <p>"Ordered oil online. Tracking number worked, arrived on time."</p>
              <strong>Josef M.</strong><div>Delivery rider, Manila</div>
            </div>
          </div>
        </div>
      </section>

      <section className="section" id="faq" style={{ background: "var(--surface)" }}>
        <div className="container">
          <div className="section-head">
            <div className="eyebrow">Common Questions</div>
            <h2>Have a question? Ask our AI assistant</h2>
            <p>Answers below are pulled from the same admin-curated knowledge base our chatbot uses.</p>
          </div>
          <div style={{ maxWidth: 760 }}>
            {faqs.map((f) => (
              <details key={f.id} style={{ borderBottom: "1px solid var(--line)", padding: "14px 0" }}>
                <summary style={{ fontWeight: 700, cursor: "pointer" }}>{f.question}</summary>
                <p style={{ margin: "10px 0 0", color: "var(--muted)", fontSize: 14 }}>{f.answer}</p>
              </details>
            ))}
          </div>
          <div style={{ display: "flex", gap: 16, alignItems: "center", marginTop: 20, flexWrap: "wrap" }}>
            <button className="btn btn-primary" onClick={toggleChat}>Ask the AI Assistant</button>
            <Link className="see-all" to="/faqs">See all FAQs &rarr;</Link>
          </div>
        </div>
      </section>

      {!user && (
  <section className="cta-band" id="contact">
    <h2>Ready to ride worry-free?</h2>
    <p>Sign in with Google to track orders, save addresses, and check out faster.</p>
    <button className="btn btn-white" onClick={() => requireLogin("login")}>Continue with Google</button>
  </section>
)}

     {selectedProduct && (
  <ProductModal
    product={selectedProduct}
    allProducts={products}
    onSelectProduct={setSelectedProduct}
    onClose={() => setSelectedProduct(null)}
  />
)}
    </>
  );
}
