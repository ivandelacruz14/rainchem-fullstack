import { useEffect, useMemo, useState } from "react";
import client from "../../api/client";
import { useToast } from "../../context/ToastContext";
import { formatDate, peso } from "../../utils/format";
import { PRESETS, presetRange, salePrice } from "../sales/salePresets";

const QUICK_PERCENTS = [10, 20, 30, 50];
const STATUS_LABELS = { active: "Running now", scheduled: "Scheduled", ended: "Ended" };

function emptyForm() {
  return { productIds: [], percent: 30, label: "", preset: "today", ...presetRange("today") };
}

function dateText(iso) {
  return formatDate(`${iso}T00:00:00`).split(",").slice(0, 2).join(",");
}

export default function AdminSales() {
  const showToast = useToast();
  const [sales, setSales] = useState([]);
  const [products, setProducts] = useState([]);
  const [filter, setFilter] = useState("all");
  const [form, setForm] = useState(null);
  const [search, setSearch] = useState("");
  const [busy, setBusy] = useState(false);

  function load() {
    client.get("/api/admin/sales").then((res) => setSales(res.data.sales));
  }
  useEffect(() => {
    load();
    client.get("/api/products/manage").then((res) => setProducts(res.data.products));
  }, []);

  const visible = sales.filter((s) => filter === "all" || s.status === filter);
  const counts = useMemo(() => Object.fromEntries(["active", "scheduled", "ended"].map((k) => [k, sales.filter((s) => s.status === k).length])), [sales]);

  function update(patch) {
    setForm((prev) => ({ ...prev, ...patch }));
  }

  function choosePreset(key) {
    update({ preset: key, ...presetRange(key) });
  }

  function toggleProduct(id) {
    setForm((prev) => ({
      ...prev,
      productIds: prev.productIds.includes(id) ? prev.productIds.filter((p) => p !== id) : [...prev.productIds, id],
    }));
  }

  async function save(e) {
    e.preventDefault();
    if (form.productIds.length === 0) {
      showToast("Choose at least one product", "error");
      return;
    }
    setBusy(true);
    try {
      await client.post("/api/admin/sales", {
        productIds: form.productIds, percent: Number(form.percent), label: form.label,
        startDate: form.startDate, endDate: form.endDate,
      });
      showToast("Sale saved", "success");
      setForm(null);
      load();
    } catch (err) {
      showToast(err.response?.data?.error || "Could not save this sale", "error");
    } finally {
      setBusy(false);
    }
  }

  async function endSale(sale) {
    const text = sale.status === "active" ? "End this sale now? Customers will see the regular price again." : "Cancel this scheduled sale?";
    if (!window.confirm(text)) return;
    try {
      await client.post(`/api/admin/sales/${sale.id}/end`);
      showToast(sale.status === "active" ? "Sale ended" : "Sale cancelled", "success");
      load();
    } catch (err) {
      showToast(err.response?.data?.error || "Could not update this sale", "error");
    }
  }

  const term = search.trim().toLowerCase();
  const pickable = products.filter((p) => !term || p.name.toLowerCase().includes(term));
  const picked = products.filter((p) => form?.productIds.includes(p.id));

  return (
    <div>
      <div className="admin-topbar">
        <div>
          <h1>Sales</h1>
          <p>Put products on sale for a set time. Customers see the regular price crossed out and the sale price, and the discount is applied at checkout automatically.</p>
        </div>
        <button type="button" className="btn btn-primary" onClick={() => { setForm(emptyForm()); setSearch(""); }}>+ New Sale</button>
      </div>

      <div className="tab-bar">
        {[["all", "All"], ["active", "Running"], ["scheduled", "Scheduled"], ["ended", "Ended"]].map(([key, label]) => (
          <button type="button" key={key} className={`tab-btn ${filter === key ? "active" : ""}`} onClick={() => setFilter(key)}>
            {label}{key !== "all" && counts[key] > 0 ? ` (${counts[key]})` : ""}
          </button>
        ))}
      </div>

      <div className="admin-panel">
        <div className="table-wrap">
          <table className="admin-table stack">
            <thead><tr><th>Product</th><th>Regular</th><th>Discount</th><th>Sale price</th><th>Dates</th><th>Status</th><th></th></tr></thead>
            <tbody>
              {visible.length === 0 ? (
                <tr><td colSpan={7}>No sales here yet. Press New Sale to add one.</td></tr>
              ) : visible.map((s) => (
                <tr key={s.id}>
                  <td data-label="Product" className="cell-name">{s.productName}{s.label && <div className="muted">{s.label}</div>}</td>
                  <td data-label="Regular">{peso(s.originalPrice)}</td>
                  <td data-label="Discount">{s.percent}% off</td>
                  <td data-label="Sale price"><strong>{peso(s.salePrice)}</strong></td>
                  <td data-label="Dates">{s.startDate === s.endDate ? dateText(s.startDate) : `${dateText(s.startDate)} to ${dateText(s.endDate)}`}</td>
                  <td data-label="Status"><span className={`status-pill sale-${s.status}`}>{STATUS_LABELS[s.status]}</span></td>
                  <td data-label="" className="row-cell">
                    {s.status !== "ended" && (
                      <button type="button" className="icon-action wide" onClick={() => endSale(s)}>{s.status === "active" ? "End now" : "Cancel"}</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {form && (
        <div className="overlay" onClick={() => setForm(null)}>
          <div className="modal wide" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head">
              <h3 style={{ margin: 0 }}>New sale</h3>
              <button type="button" className="modal-close" onClick={() => setForm(null)}>&times;</button>
            </div>
            <form className="modal-body" onSubmit={save}>
              <div className="field">
                <label>When</label>
                <div className="chip-row">
                  {PRESETS.map((p) => (
                    <button type="button" key={p.key} className={`chip ${form.preset === p.key ? "active" : ""}`} onClick={() => choosePreset(p.key)}>{p.label}</button>
                  ))}
                </div>
                <div className="field-row" style={{ marginTop: 10 }}>
                  <div className="field"><label htmlFor="sale-from">From</label><input id="sale-from" type="date" required value={form.startDate} onChange={(e) => update({ startDate: e.target.value, preset: "" })} /></div>
                  <div className="field"><label htmlFor="sale-to">Until (included)</label><input id="sale-to" type="date" required min={form.startDate} value={form.endDate} onChange={(e) => update({ endDate: e.target.value, preset: "" })} /></div>
                </div>
              </div>

              <div className="field">
                <label htmlFor="sale-percent">Discount (%)</label>
                <div className="chip-row">
                  {QUICK_PERCENTS.map((n) => (
                    <button type="button" key={n} className={`chip ${Number(form.percent) === n ? "active" : ""}`} onClick={() => update({ percent: n })}>{n}% off</button>
                  ))}
                </div>
                <input id="sale-percent" type="number" min="1" max="90" step="1" required value={form.percent} onChange={(e) => update({ percent: e.target.value })} style={{ marginTop: 10, maxWidth: 140 }} />
              </div>

              <div className="field">
                <label htmlFor="sale-label">Sale name (optional)</label>
                <input id="sale-label" maxLength={60} value={form.label} onChange={(e) => update({ label: e.target.value })} placeholder="Weekend Sale" />
              </div>

              <div className="field">
                <label>Products ({form.productIds.length} chosen)</label>
                <div className="pick-tools">
                  <input placeholder="Search products..." value={search} onChange={(e) => setSearch(e.target.value)} />
                  <button type="button" className="btn btn-outline btn-sm" onClick={() => update({ productIds: pickable.map((p) => p.id) })}>Select shown</button>
                  <button type="button" className="btn btn-outline btn-sm" onClick={() => update({ productIds: [] })}>Clear</button>
                </div>
                <div className="pick-list">
                  {pickable.map((p) => (
                    <label className="perm-item pick-item" key={p.id}>
                      <input type="checkbox" checked={form.productIds.includes(p.id)} onChange={() => toggleProduct(p.id)} />
                      <span>{p.name}</span>
                      <span className="muted">{peso(p.price)}</span>
                    </label>
                  ))}
                  {pickable.length === 0 && <p className="field-hint">No products found.</p>}
                </div>
              </div>

              {picked.length > 0 && (
                <div className="sale-preview">
                  <strong>Customers will see</strong>
                  {picked.slice(0, 5).map((p) => (
                    <div key={p.id}><span className="cell-name">{p.name}</span>: <s>{peso(p.price)}</s> <strong>{peso(salePrice(p.price, form.percent))}</strong></div>
                  ))}
                  {picked.length > 5 && <div className="muted">and {picked.length - 5} more</div>}
                </div>
              )}

              <div className="form-actions">
                <button type="button" className="btn btn-outline" onClick={() => setForm(null)}>Cancel</button>
                <button type="submit" className="btn btn-primary" disabled={busy}>{busy ? "Saving..." : "Save sale"}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
