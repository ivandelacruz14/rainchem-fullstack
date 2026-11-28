import { useEffect, useState } from "react";
import client from "../../api/client";
import { useToast } from "../../context/ToastContext";
import PinLocation from "../../components/PinLocation";

const LABELS = ["Home", "Work", "Temporary", "Other"];
const EMPTY = {
  label: "Home", regionCode: "", provinceCode: "", cityCode: "", barangayCode: "", zipCode: "",
  houseNumber: "", street: "", subdivision: "", village: "", unit: "", landmark: "", instructions: "", latitude: "", longitude: "", makeDefault: false,
};

/** Saved addresses. Each choice only offers the places inside the one before it (region, province, city, barangay). */
export default function AccountAddress() {
  const showToast = useToast();
  const [list, setList] = useState(null);
  const [regions, setRegions] = useState([]);
  const [provinces, setProvinces] = useState([]);
  const [cities, setCities] = useState([]);
  const [barangays, setBarangays] = useState([]);
  const [form, setForm] = useState(EMPTY);
  const [editingId, setEditingId] = useState(null);
  const [zip, setZip] = useState({ available: false, zipCode: null });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function loadList() {
    client.get("/api/addresses").then((r) => setList(r.data.addresses)).catch(() => setList([]));
  }

  async function places(parent) {
    const r = await client.get("/api/addresses/locations", { params: { parent } });
    return r.data.places;
  }

  useEffect(() => {
    loadList();
    places(undefined).then(setRegions).catch(() => {});
  }, []);

  async function chooseRegion(code) {
    const inside = code ? await places(code) : [];
    setProvinces(inside.filter((p) => p.level === "Prov"));
    setCities(inside.filter((p) => p.level === "City" || p.level === "Mun"));
    setBarangays([]);
    setZip({ available: false, zipCode: null });
    setForm((f) => ({ ...f, regionCode: code, provinceCode: "", cityCode: "", barangayCode: "", zipCode: "" }));
  }

  async function chooseProvince(code) {
    const inside = code ? await places(code) : [];
    setCities(inside.filter((p) => p.level === "City" || p.level === "Mun"));
    setBarangays([]);
    setForm((f) => ({ ...f, provinceCode: code, cityCode: "", barangayCode: "", zipCode: "" }));
  }

  async function chooseCity(code) {
    const inside = code ? await places(code) : [];
    setBarangays(inside.filter((p) => p.level === "Bgy" || p.level === "SubMun"));
    setForm((f) => ({ ...f, cityCode: code, barangayCode: "", zipCode: "" }));
  }

  async function chooseBarangay(code) {
    setForm((f) => ({ ...f, barangayCode: code }));
    if (!code) return;
    const r = await client.get(`/api/addresses/locations/${code}/zip`);
    setZip(r.data);
    setForm((f) => ({ ...f, zipCode: r.data.zipCode || f.zipCode || "" }));
  }

  function startNew() {
    setEditingId(null);
    setForm(EMPTY);
    setProvinces([]);
    setCities([]);
    setBarangays([]);
    setZip({ available: false, zipCode: null });
    setError("");
  }

  async function startEdit(a) {
    setEditingId(a.id);
    setError("");
    await chooseRegion(a.region.code);
    if (a.province) await chooseProvince(a.province.code);
    await chooseCity(a.city.code);
    await chooseBarangay(a.barangay.code);
    setForm({
      label: a.label, regionCode: a.region.code, provinceCode: a.province?.code || "", cityCode: a.city.code,
      barangayCode: a.barangay.code, zipCode: a.zipCode || "", houseNumber: a.houseNumber || "", street: a.street || "",
      subdivision: a.subdivision || "", village: a.village || "", unit: a.unit || "", landmark: a.landmark || "",
      instructions: a.instructions || "", latitude: a.latitude ?? "", longitude: a.longitude ?? "", makeDefault: a.isDefault,
    });
  }

  async function save(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const body = { ...form, provinceCode: form.provinceCode || null };
      if (editingId) await client.put(`/api/addresses/${editingId}`, body);
      else await client.post("/api/addresses", body);
      showToast("Address saved", "success");
      startNew();
      loadList();
    } catch (err) {
      setError(err.response?.data?.error || "The address could not be saved.");
    } finally {
      setBusy(false);
    }
  }

  async function makeDefault(id) {
    await client.post(`/api/addresses/${id}/default`);
    loadList();
  }

  async function remove(id) {
    if (!window.confirm("Delete this address?")) return;
    await client.delete(`/api/addresses/${id}`);
    if (editingId === id) startNew();
    loadList();
  }

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  return (
    <div className="acct-addr-page">
      <h2 className="acct-title">My Addresses</h2>
      <p className="acct-subtitle">Your delivery addresses. The default one is used at checkout.</p>
      <div className="acct-addr-grid">
        <section className="acct-card acct-addr-list">
          <h3>Saved addresses</h3>
      {list === null && <p className="field-hint">Loading...</p>}
      {list && list.length === 0 && <p className="field-hint">No saved addresses yet. Add one below.</p>}
      {list && list.map((a) => (
        <div className="panel" key={a.id} style={{ marginBottom: 12 }}>
          <strong>{a.label}</strong>{a.isDefault && <span className="pill" style={{ marginLeft: 8 }}>Default</span>}
          <p style={{ margin: "6px 0" }}>{a.formatted}</p>
          <div className="row-actions">
            <button type="button" className="btn btn-outline btn-sm" onClick={() => startEdit(a)}>Edit</button>
            {!a.isDefault && <button type="button" className="btn btn-outline btn-sm" onClick={() => makeDefault(a.id)}>Set as default</button>}
            <button type="button" className="btn btn-outline btn-sm" onClick={() => remove(a.id)}>Delete</button>
          </div>
        </div>
      ))}

        </section>
        <section className="acct-card acct-addr-form">
      <h3>{editingId ? "Edit address" : "Add an address"}</h3>
      {error && <div className="alert alert-error" role="alert">{error}</div>}
      <form onSubmit={save} style={{ maxWidth: 560 }}>
        <div className="field"><label htmlFor="ad-label">Address type</label>
          <select id="ad-label" value={form.label} onChange={set("label")}>{LABELS.map((l) => <option key={l}>{l}</option>)}</select></div>
        <div className="field"><label htmlFor="ad-region">Region</label>
          <select id="ad-region" required value={form.regionCode} onChange={(e) => chooseRegion(e.target.value)}>
            <option value="">Choose a region</option>{regions.map((r) => <option key={r.code} value={r.code}>{r.name}</option>)}
          </select></div>
        {provinces.length > 0 && (
          <div className="field"><label htmlFor="ad-prov">Province</label>
            <select id="ad-prov" required value={form.provinceCode} onChange={(e) => chooseProvince(e.target.value)}>
              <option value="">Choose a province</option>{provinces.map((p) => <option key={p.code} value={p.code}>{p.name}</option>)}
            </select></div>
        )}
        <div className="field"><label htmlFor="ad-city">City or municipality</label>
          <select id="ad-city" required value={form.cityCode} onChange={(e) => chooseCity(e.target.value)} disabled={!form.regionCode}>
            <option value="">Choose a city or municipality</option>{cities.map((c) => <option key={c.code} value={c.code}>{c.name}</option>)}
          </select></div>
        <div className="field"><label htmlFor="ad-bgy">Barangay</label>
          <select id="ad-bgy" required value={form.barangayCode} onChange={(e) => chooseBarangay(e.target.value)} disabled={!form.cityCode}>
            <option value="">Choose a barangay</option>{barangays.map((b) => <option key={b.code} value={b.code}>{b.name}</option>)}
          </select></div>
        <div className="field"><label htmlFor="ad-zip">ZIP code</label>
          <input id="ad-zip" inputMode="numeric" maxLength={4} value={form.zipCode} readOnly={zip.available}
            onChange={(e) => setForm((f) => ({ ...f, zipCode: e.target.value.replace(/\D/g, "") }))} />
          <p className="field-hint">
            {!form.barangayCode ? "Choose a barangay first." : zip.available
              ? "ZIP code from the official postal list."
              : "No official ZIP code is on file for this barangay yet. Enter the 4-digit ZIP from your address."}
          </p></div>
        <div className="field"><label htmlFor="ad-house">House or building number</label><input id="ad-house" value={form.houseNumber} onChange={set("houseNumber")} /></div>
        <div className="field"><label htmlFor="ad-street">Street *</label><input id="ad-street" required value={form.street} onChange={set("street")} /></div>
        <div className="field"><label htmlFor="ad-unit">Floor or unit</label><input id="ad-unit" value={form.unit} onChange={set("unit")} /></div>
        <div className="field"><label htmlFor="ad-landmark">Landmark</label><input id="ad-landmark" value={form.landmark} onChange={set("landmark")} /></div>
        <div className="field"><label htmlFor="ad-instr">Delivery instructions</label><textarea id="ad-instr" rows={2} value={form.instructions} onChange={set("instructions")} /></div>
        <PinLocation lat={form.latitude} lng={form.longitude} onChange={(la, ln) => setForm((f) => ({ ...f, latitude: la, longitude: ln }))} />
        <label style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 12 }}>
          <input type="checkbox" checked={form.makeDefault} onChange={(e) => setForm((f) => ({ ...f, makeDefault: e.target.checked }))} />
          Use as my default delivery address
        </label>
        <div className="form-actions">
          {editingId && <button type="button" className="btn btn-outline" onClick={startNew}>Cancel</button>}
          <button type="submit" className="btn btn-primary" disabled={busy || !form.barangayCode || !form.street.trim()}>
            {busy ? "Saving..." : editingId ? "Save changes" : "Save address"}
          </button>
        </div>
      </form>
        </section>
      </div>
    </div>
  );
}
