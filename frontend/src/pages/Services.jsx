import { useState, useEffect } from "react";
import client from "../api/client";
import ProductCard from "../components/ProductCard";
import ProductModal from "../components/ProductModal";

export default function Services() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    client.get("/api/products").then((res) => setProducts(res.data.products)).finally(() => setLoading(false));
  }, []);

  const services = products.filter((p) => p.category === "Services");

  return (
    <div className="container" style={{ paddingBottom: 80 }}>
      <div className="page-hero">
        <div className="eyebrow">Rainchem Service Bays</div>
        <h1>Book a service, not just a bottle</h1>
        <p>Our partner service bays handle the install. Add a service to your cart together with your parts.</p>
      </div>

      <div className="steps-row">
        <div className="step-box"><strong>1. Add to cart</strong>Pick a service, with or without parts.</div>
        <div className="step-box"><strong>2. Check out</strong>Pay by Cash on Delivery, GCash, or card.</div>
        <div className="step-box"><strong>3. Visit a partner bay</strong>Bring your order confirmation and we'll take care of the rest.</div>
      </div>

      {loading ? null : services.length === 0 ? (
        <div className="empty-state">No services available right now.</div>
      ) : (
        <div className="product-grid">
          {services.map((p) => <ProductCard key={p.id} product={p} onOpen={setSelected} />)}
        </div>
      )}

      {selected && (
        <ProductModal product={selected} allProducts={products} onSelectProduct={setSelected} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}
