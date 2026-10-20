import { useEffect, useState } from "react";
import client from "../../api/client";
import { resizeImage } from "../../utils/imageResize";
import { readQrText } from "../../utils/qrDecode";
import { useToast } from "../../context/ToastContext";

const EMPTY = { number: "", accountName: "", link: "", note: "", qr: "", qrPayload: "" };

export default function PaymentSettings() {
  const showToast = useToast();
  const [form, setForm] = useState(EMPTY);
  const [status, setStatus] = useState({ cardAvailable: false, cardDemoMode: false });
  const [saving, setSaving] = useState(false);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    client.get("/api/admin/settings/payment")
      .then((res) => {
        setForm({ ...EMPTY, ...res.data.gcash });
        setStatus({ cardAvailable: res.data.cardAvailable, cardDemoMode: res.data.cardDemoMode });
      })
      .catch(() => showToast("Could not load the payment settings", "error"))
      .finally(() => setLoaded(true));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  function update(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function pickQr(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      update("qr", await resizeImage(file, 700));
    } catch {
      showToast("That image could not be read", "error");
      return;
    }
    const text = await readQrText(file);
    if (text) {
      update("qrPayload", text);
      showToast("QR code read. Its amount will now be filled in for every order.", "success");
    } else {
      showToast("The QR picture was kept, but its text could not be read. Paste the QR text below.", "error");
    }
  }

  async function save(e) {
    e.preventDefault();
    setSaving(true);
    try {
      const res = await client.put("/api/admin/settings/payment", { gcash: form });
      setForm({ ...EMPTY, ...res.data.gcash });
      showToast("Payment settings saved", "success");
    } catch (err) {
      showToast(err.response?.data?.error || "Could not save the settings", "error");
    } finally {
      setSaving(false);
    }
  }

  const gcashReady = Boolean(form.number || form.link || form.qr || form.qrPayload);

  return (
    <div>
      <div className="admin-topbar">
        <div>
          <h1>Payment Settings</h1>
          <p>Choose what customers see when they pay with GCash.</p>
        </div>
      </div>

      <div className="admin-panel" style={{ maxWidth: 640 }}>
        <div className="panel-head">
          <h3 style={{ margin: 0 }}>GCash</h3>
          <span className={`pill ${gcashReady ? "pill-approved" : "pill-pending"}`}>{gcashReady ? "Shown at checkout" : "Not set up"}</span>
        </div>
        <p className="field-hint" style={{ marginTop: 0 }}>
          Customers who pick GCash see these details, send the payment, then enter their GCash reference number.
          You check it in your GCash account and mark the order as paid. Fill in at least one of: number, QR code, or link.
        </p>

        {loaded && (
          <form onSubmit={save}>
            <div className="field-row">
              <div className="field">
                <label>GCash number</label>
                <input value={form.number} placeholder="09xx xxx xxxx" onChange={(e) => update("number", e.target.value)} />
              </div>
              <div className="field">
                <label>Account name</label>
                <input value={form.accountName} placeholder="Name on the GCash account" onChange={(e) => update("accountName", e.target.value)} />
              </div>
            </div>
            <div className="field">
              <label>GCash payment link (optional)</label>
              <input value={form.link} placeholder="https://..." onChange={(e) => update("link", e.target.value)} />
            </div>
            <div className="field">
              <label>Note shown to customers (optional)</label>
              <input value={form.note} maxLength={300} placeholder="e.g. Please put your order number in the message" onChange={(e) => update("note", e.target.value)} />
            </div>
            <div className="field">
              <label>GCash QR code (optional)</label>
              <input type="file" accept="image/*" onChange={pickQr} />
              {form.qr && (
                <div style={{ marginTop: 10 }}>
                  <img src={form.qr} alt="GCash QR code" style={{ width: 160, borderRadius: 8, background: "#fff", padding: 6, border: "1px solid var(--line)" }} />
                  <div><button type="button" className="link-btn" style={{ marginTop: 6 }} onClick={() => update("qr", "")}>Remove QR code</button></div>
                </div>
              )}
            </div>
            <div className="field">
              <label>QR code text (fills in the amount automatically)</label>
              <textarea
                rows={3}
                className="mono"
                value={form.qrPayload}
                placeholder="Starts with 000201... It is filled in when you upload your QR picture above."
                onChange={(e) => update("qrPayload", e.target.value.trim())}
              />
              <div className="field-hint">
                {form.dynamicQrReady
                  ? "Saved. Customers get a QR code with their order amount already filled in."
                  : "Without this, customers must type the amount themselves. You can also scan your QR with a phone and paste the text here."}
              </div>
            </div>
            <div className="form-actions">
              <button type="submit" className="btn btn-primary" disabled={saving}>{saving ? "Saving..." : "Save settings"}</button>
            </div>
          </form>
        )}
      </div>

      <div className="admin-panel" style={{ maxWidth: 640 }}>
        <div className="panel-head">
          <h3 style={{ margin: 0 }}>Credit / Debit Card</h3>
          <span className={`pill ${status.cardAvailable ? "pill-approved" : "pill-pending"}`}>
            {status.cardAvailable ? (status.cardDemoMode ? "Demo mode" : "Available") : "Not set up"}
          </span>
        </div>
        <p className="field-hint" style={{ margin: 0 }}>
          Card payments go through PayMongo. To turn them on, set <span className="mono">PAYMONGO_SECRET_KEY</span> in the
          backend environment. Cash on Delivery is always available.
        </p>
      </div>
    </div>
  );
}
