import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import client from "../api/client";
import ProductCard from "../components/ProductCard";
import ProductModal from "../components/ProductModal";
import { CategoryIcon } from "../components/ProductVisual";
import { useUI } from "../context/UIContext";

const CATEGORIES = [
  { name: "Oils & Fluids", blurb: "Synthetic & semi-synthetic engine oil, brake fluid." },
  { name: "Coolant", blurb: "RadCool concentrate & ready-to-use coolant." },
  { name: "Filters", blurb: "Oil filters and washable air filters." },
  { name: "Brakes", blurb: "Brake pads and hydraulic system parts." },
  { name: "Accessories", blurb: "Chain lube, spark plugs, and small parts." },
  { name: "Services", blurb: "Book professional installs at partner bays." },
];

export default function Home() {
  const [products, setProducts] = useState([]);
  const [filter, setFilter] = useState("All");
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [faqs, setFaqs] = useState([]);
  const { requireLogin, toggleChat } = useUI();
  const navigate = useNavigate();

  useEffect(() => {
    client.get("/api/products").then((res) => setProducts(res.data.products));
    client.get("/api/chat/faq").then((res) => setFaqs(res.data.faqs));
  }, []);

  const visibleProducts = filter === "All" ? products : products.filter((p) => p.category === filter);

  function scrollToShop(category) {
    setFilter(category);
    document.getElementById("shop")?.scrollIntoView({ behavior: "smooth" });
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
              <a href="#shop" className="btn btn-primary">Shop Products</a>
              <a href="#services" className="btn btn-outline">Book a Service</a>
            </div>
            <div className="hero-stats">
              <div className="stat-card"><div className="value">30 Yrs</div><div className="label">Since 1995</div></div>
              <div className="stat-card"><div className="value">ISO</div><div className="label">Certified Blending</div></div>
              <div className="stat-card"><div className="value">24/7</div><div className="label">AI Support</div></div>
            </div>
          </div>
          <div className="hero-visual">
            <div className="hero-ring">
              <svg width="56%" viewBox="0 0 120 200" fill="none">
                <rect x="30" y="20" width="60" height="150" rx="10" fill="#e1131f" />
                <rect x="42" y="4" width="36" height="22" rx="4" fill="#18140f" />
                <rect x="34" y="70" width="52" height="60" rx="4" fill="#fff" opacity=".92" />
                <rect x="40" y="80" width="40" height="6" fill="#e1131f" />
                <rect x="40" y="92" width="40" height="4" fill="#b5121b" />
                <rect x="40" y="100" width="30" height="4" fill="#b5121b" />
                <rect x="40" y="108" width="34" height="4" fill="#b5121b" />
              </svg>
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
              <button key={cat.name} className="cat-card" onClick={() => scrollToShop(cat.name)}>
                <div className="cat-icon"><CategoryIcon category={cat.name} /></div>
                <h4>{cat.name}</h4>
                <p>{cat.blurb}</p>
              </button>
            ))}
          </div>
        </div>
      </section>

      <section className="section" id="shop" style={{ background: "#fff" }}>
        <div className="container">
          <div className="section-head">
            <div className="eyebrow">Full Catalog</div>
            <h2>Products &amp; services</h2>
            <p>Filter by category, or browse for exactly what your bike needs.</p>
          </div>
          <div className="filter-bar">
            {["All", ...CATEGORIES.map((c) => c.name)].map((c) => (
              <button key={c} className={`chip ${filter === c ? "active" : ""}`} onClick={() => setFilter(c)}>{c}</button>
            ))}
          </div>
          <div className="product-grid">
            {visibleProducts.map((p) => (
              <ProductCard key={p.id} product={p} onOpen={setSelectedProduct} />
            ))}
          </div>
        </div>
      </section>

      <section className="section services-band" id="services">
        <div className="container">
          <div className="section-head">
            <div className="eyebrow">Rainchem Service Bays</div>
            <h2>Book a service, not just a bottle</h2>
            <p>Our partner service bays handle the install, you just bring your order confirmation.</p>
          </div>
          <div className="service-grid">
            <div className="service-card">
              <h4>Oil Change Service</h4>
              <p>Full labor and eco-friendly used oil disposal at any Rainchem partner bay.</p>
              <div className="service-price">&#8369;150</div>
            </div>
            <div className="service-card">
              <h4>Radiator Flush &amp; RadCool Service</h4>
              <p>Complete flush of your old coolant and refill with RadCool to manufacturer levels.</p>
              <div className="service-price">&#8369;250</div>
            </div>
            <div className="service-card">
              <h4>Full Maintenance Check-up</h4>
              <p>Chain, brakes, filters, and fluid levels inspected by a certified technician.</p>
              <div className="service-price">&#8369;300</div>
            </div>
          </div>
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
              <p>"Ordered oil and booked the change service together. Tracking number worked, arrived on time."</p>
              <strong>Josef M.</strong><div>Delivery rider, Manila</div>
            </div>
          </div>
        </div>
      </section>

      <section className="section" id="faq" style={{ background: "#fff" }}>
        <div className="container">
          <div className="section-head">
            <div className="eyebrow">Common Questions</div>
            <h2>Have a question? Ask our AI assistant</h2>
            <p>Answers below are pulled from the same admin-curated knowledge base our chatbot uses.</p>
          </div>
          <div style={{ maxWidth: 760 }}>
            {faqs.map((f) => (
              <details key={f.id} style={{ borderBottom: "1px solid rgba(24,20,15,.08)", padding: "14px 0" }}>
                <summary style={{ fontWeight: 700, cursor: "pointer" }}>{f.question}</summary>
                <p style={{ margin: "10px 0 0", color: "#57524c", fontSize: 14 }}>{f.answer}</p>
              </details>
            ))}
          </div>
          <button className="btn btn-primary" style={{ marginTop: 20 }} onClick={toggleChat}>Ask the AI Assistant</button>
        </div>
      </section>

      <section className="cta-band" id="contact">
        <h2>Ready to ride worry-free?</h2>
        <p>Create an account to track orders, save addresses, and check out faster.</p>
        <button className="btn btn-white" onClick={() => requireLogin("register")}>Create Free Account</button>
      </section>

      {selectedProduct && (
        <ProductModal product={selectedProduct} onClose={() => setSelectedProduct(null)} />
      )}
    </>
  );
}
