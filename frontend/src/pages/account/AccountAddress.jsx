import { useState } from "react";
import client from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import { useToast } from "../../context/ToastContext";

export default function AccountAddress() {
  const { user, setUser } = useAuth();
  const showToast = useToast();
  const [form, setForm] = useState({
    line1: user?.address?.line1 || "",
    city: user?.address?.city || "",
    province: user?.address?.province || "",
    region: user?.address?.region || "",
    zip: user?.address?.zip || "",
  });

  function update(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    try {
      const res = await client.put("/api/auth/me/address", form);
      setUser(res.data.user);
      showToast("Address saved", "success");
    } catch {
      showToast("Could not save address", "error");
    }
  }

  return (
    <div>
      <h2>Saved Address</h2>
      <form className="panel" style={{ maxWidth: 520 }} onSubmit={handleSubmit}>
        <div className="field"><label>Street Address</label><input value={form.line1} onChange={(e) => update("line1", e.target.value)} /></div>
        <div className="field-row">
          <div className="field"><label>City</label><input value={form.city} onChange={(e) => update("city", e.target.value)} /></div>
          <div className="field"><label>Province</label><input value={form.province} onChange={(e) => update("province", e.target.value)} /></div>
        </div>
        <div className="field-row">
          <div className="field"><label>Region</label><input value={form.region} onChange={(e) => update("region", e.target.value)} /></div>
          <div className="field"><label>ZIP</label><input value={form.zip} onChange={(e) => update("zip", e.target.value)} /></div>
        </div>
        <button className="btn btn-primary" type="submit">Save Address</button>
      </form>
    </div>
  );
}
