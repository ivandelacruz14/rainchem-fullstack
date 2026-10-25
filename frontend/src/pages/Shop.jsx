import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import client from "../api/client";
import ProductCard from "../components/ProductCard";
import ProductModal from "../components/ProductModal";
import { CATEGORIES } from "../utils/categories";

export default function Shop() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);
  const [search, setSearch] = useState("");
  const [params, setParams] = useSearchParams();

  const onSaleOnly = params.get("sale") === "1";
  const category = CATEGORIES.some((c) => c.name === params.get("category")) ? params.get("category") : "All";

  useEffect(() => {
    client.get("/api/products").then((res) => setProducts(res.data.products)).finally(() => setLoading(false));
  }, []);

  // Links like /shop?product=12 (used to come back after logging in) open that product.
  const linkedProductId = Number(params.get("product")) || null;
  useEffect(() => {
    if (!linkedProductId || products.length === 0) return;
    const match = products.find((p) => p.id === linkedProductId);
    if (match) setSelected(match);
  }, [linkedProductId, products]);

  function closeProduct() {
    setSelected(null);
    if (params.has("product")) {
      const next = new URLSearchParams(params);
      next.delete("product");
      setParams(next, { replace: true });
    }
  }

  function chooseCategory(name) {
    setParams(name === "All" ? {} : { category: name });
  }

  function toggleSale() {
    const next = new URLSearchParams(params);
    if (onSaleOnly) next.delete("sale");
    else next.set("sale", "1");
    setParams(next);
  }

  const saleCount = products.filter((p) => p.onSale).length;

  const term = search.trim().toLowerCase();
  const visible = products.filter((p) => {
    if (category !== "All" && p.category !== category) return false;
    if (onSaleOnly && !p.onSale) return false;
    if (!term) return true;
    return `${p.name} ${p.shortDesc || ""} ${p.category}`.toLowerCase().includes(term);
  });

  return (
    <div className="container" style={{ paddingBottom: 80 }}>
      <div className="page-hero">
        <div className="eyebrow">Shop</div>
        <h1>{category === "All" ? "All products" : category}</h1>
        <p>
          {category === "All"
            ? "Engine oil, RadCool coolant, filters, brakes, and accessories."
            : CATEGORIES.find((c) => c.name === category)?.blurb}
        </p>
      </div>

      <div className="shop-toolbar">
        <div className="chip-row">
          {["All", ...CATEGORIES.map((c) => c.name)].map((name) => (
            <button key={name} className={`chip ${category === name ? "active" : ""}`} onClick={() => chooseCategory(name)}>
              {name}
            </button>
          ))}
          {saleCount > 0 && (
            <button className={`chip chip-sale ${onSaleOnly ? "active" : ""}`} onClick={toggleSale}>
              On Sale ({saleCount})
            </button>
          )}
        </div>
        <input placeholder="Search products..." value={search} onChange={(e) => setSearch(e.target.value)} />
      </div>

      {loading ? null : visible.length === 0 ? (
        <div className="empty-state">No products found.</div>
      ) : (
        <div className="product-grid">
          {visible.map((p) => <ProductCard key={p.id} product={p} onOpen={setSelected} />)}
        </div>
      )}

      {selected && (
        <ProductModal product={selected} allProducts={products} onSelectProduct={setSelected} onClose={closeProduct} />
      )}
    </div>
  );
}
