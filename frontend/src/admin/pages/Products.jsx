import { useState, useEffect } from "react";
import client from "../../api/client";
import { peso } from "../../utils/format";
import { useToast } from "../../context/ToastContext";

const CATEGORIES = ["Oils & Fluids", "Coolant", "Filters", "Brakes", "Accessories", "Services"];
const emptyForm = { name: "", category: CATEGORIES[0], price: "", stock: "", rating: "4.5", shortDesc: "", description: "", specs: "", benefits: "", usage: "" };

function resizeImage(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const img = new Image();
      img.onload = () => {
        const maxWidth = 600;
        const scale = Math.min(1, maxWidth / img.width);
        const canvas = document.createElement("canvas");
        canvas.width = img.width * scale;
        canvas.height = img.height * scale;
        canvas.getContext("2d").drawImage(img, 0, 0, canvas.width, canvas.height);
        resolve(canvas.toDataURL("image/jpeg", 0.85));
      };
      img.onerror = reject;
      img.src = reader.result;
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

export default function Products() {
  const [products, setProducts] = useState([]);
  const [search, setSearch] = useState("");
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(emptyForm);
  const [imagePreview, setImagePreview] = useState(null);
  const [pendingImage, setPendingImage] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const showToast = useToast();

  function loadProducts() {
    client.get("/api/products").then((res) => setProducts(res.data.products));
  }
  useEffect(loadProducts, []);

  function openAdd() {
    setEditing(null);
    setForm(emptyForm);
    setImagePreview(null);
    setPendingImage(null);
    setShowForm(true);
  }

  function openEdit(product) {
    setEditing(product);
    setForm({
      name: product.name, category: product.category, price: product.price, stock: product.stock,
      rating: product.rating, shortDesc: product.shortDesc, description: product.description,
      specs: product.specs.join("\n"), benefits: product.benefits.join("\n"), usage: product.usage.join("\n"),
    });
    setImagePreview(product.imagePhoto);
    setPendingImage(null);
    setShowForm(true);
  }

  async function handleImageChange(e) {
    const file = e.target.files[0];
    if (!file) return;
    const dataUrl = await resizeImage(file);
    setPendingImage(dataUrl);
    setImagePreview(dataUrl);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    const payload = {
      name: form.name, category: form.category, price: parseFloat(form.price), stock: parseInt(form.stock),
      rating: parseFloat(form.rating) || 4.5, shortDesc: form.shortDesc, description: form.description,
      specs: form.specs.split("\n").map((s) => s.trim()).filter(Boolean),
      benefits: form.benefits.split("\n").map((s) => s.trim()).filter(Boolean),
      usage: form.usage.split("\n").map((s) => s.trim()).filter(Boolean),
    };
    if (pendingImage) payload.imagePhoto = pendingImage;

    if (!form.price || isNaN(parseFloat(form.price))) {
  showToast("Please enter a valid price", "error");
  return;
}
if (!form.stock || isNaN(parseInt(form.stock))) {
  showToast("Please enter a valid stock number", "error");
  return;
}

    try {
      if (editing) {
        await client.put(`/api/products/${editing.id}`, payload);
        showToast("Product updated", "success");
      } else {
        await client.post("/api/products", payload);
        showToast("Product added", "success");
      }
      setShowForm(false);
      loadProducts();
    } catch (err) {
      const detail = err.response?.data?.error || err.message;
      showToast(`Could not save this product: ${detail}`, "error");
      console.error("Product save failed:", err.response?.data || err);
      }
  }

  async function handleDelete(id) {
    if (!window.confirm("Delete this product? This cannot be undone.")) return;
    await client.delete(`/api/products/${id}`);
    showToast("Product deleted", "error");
    loadProducts();
  }

  const filtered = products.filter((p) => p.name.toLowerCase().includes(search.toLowerCase()));

  return (
    <div>
      <div className="admin-topbar">
        <div><h1>Products</h1><p>Manage catalog, pricing, and stock levels.</p></div>
        <button className="btn btn-primary" onClick={openAdd}>+ Add Product</button>
      </div>

      <div className="admin-panel">
        <div className="panel-head">
          <div className="search-input">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="8" /><path d="m21 21-4.3-4.3" /></svg>
            <input placeholder="Search products..." value={search} onChange={(e) => setSearch(e.target.value)} />
          </div>
        </div>
        <div className="table-wrap">
          <table className="admin-table">
            <thead><tr><th></th><th>Product</th><th>Category</th><th>Price</th><th>Stock</th><th>Rating</th><th></th></tr></thead>
            <tbody>
              {filtered.map((p) => (
                <tr key={p.id}>
                  <td>
                    <div style={{ width: 40, height: 40, borderRadius: 6, overflow: "hidden", background: "var(--red-100)" }}>
                      {p.imagePhoto && <img src={p.imagePhoto} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} />}
                    </div>
                  </td>
                  <td style={{ fontWeight: 600, maxWidth: 260 }}>{p.name}</td>
                  <td>{p.category}</td>
                  <td>{peso(p.price)}</td>
                  <td>{p.stock < 20 ? <span className="pill pill-low">{p.stock} left</span> : p.stock}</td>
                  <td>{"\u2605"} {p.rating}</td>
                  <td>
                    <div className="row-actions">
                      <button className="icon-action" onClick={() => openEdit(p)}>Edit</button>
                      <button className="icon-action" onClick={() => handleDelete(p.id)}>Delete</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {showForm && (
        <div className="overlay" onClick={() => setShowForm(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head">
              <h3 style={{ margin: 0 }}>{editing ? "Edit Product" : "Add Product"}</h3>
              <button className="modal-close" onClick={() => setShowForm(false)}>&times;</button>
            </div>
            <div className="modal-body">
              <form onSubmit={handleSubmit}>
                <div className="field">
                  <label>Product Photo</label>
                  <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
                    <div style={{ width: 72, height: 72, borderRadius: 8, overflow: "hidden", border: "1px solid rgba(24,20,15,.12)", background: "var(--fog)" }}>
                      {imagePreview && <img src={imagePreview} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} />}
                    </div>
                    <div>
                      <input type="file" accept="image/*" onChange={handleImageChange} />
                      <div className="field-hint">JPG or PNG. Resized automatically, no image path needed.</div>
                    </div>
                  </div>
                </div>
                <div className="field"><label>Product Name</label><input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
                <div className="field-row">
                  <div className="field">
                    <label>Category</label>
                    <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
                      {CATEGORIES.map((c) => <option key={c}>{c}</option>)}
                    </select>
                  </div>
                  <div className="field"><label>Price (&#8369;)</label><input required type="number" step="0.01" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} /></div>
                </div>
                <div className="field-row">
                  <div className="field"><label>Stock (units available)</label><input required type="number" value={form.stock} onChange={(e) => setForm({ ...form, stock: e.target.value })} /></div>
                  <div className="field"><label>Rating (0-5)</label><input type="number" step="0.1" max="5" value={form.rating} onChange={(e) => setForm({ ...form, rating: e.target.value })} /></div>
                </div>
                <div className="field"><label>Short Description</label><input required value={form.shortDesc} onChange={(e) => setForm({ ...form, shortDesc: e.target.value })} /></div>
                <div className="field"><label>Full Description</label><textarea required rows="3" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></div>
                <div className="field"><label>Specs (one per line)</label><textarea rows="3" value={form.specs} onChange={(e) => setForm({ ...form, specs: e.target.value })} /></div>
                <div className="field"><label>Key Benefits (one per line)</label><textarea rows="3" value={form.benefits} onChange={(e) => setForm({ ...form, benefits: e.target.value })} /></div>
                <div className="field"><label>How to Use (one per line)</label><textarea rows="3" value={form.usage} onChange={(e) => setForm({ ...form, usage: e.target.value })} /></div>
                <div className="form-actions">
                  <button type="button" className="btn btn-outline" onClick={() => setShowForm(false)}>Cancel</button>
                  <button type="submit" className="btn btn-primary">{editing ? "Save Changes" : "Add Product"}</button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
