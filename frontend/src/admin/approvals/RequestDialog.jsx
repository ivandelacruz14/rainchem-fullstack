import { useEffect, useState } from "react";
import client from "../../api/client";
import PasswordInput from "../../components/PasswordInput";
import { formatDate } from "../../utils/format";

// Steps for a Head Admin approving: review -> password -> code. Only the code step applies the change.
export default function RequestDialog({ requestId, isHead, onClose, onChanged }) {
  const [detail, setDetail] = useState(null);
  const [step, setStep] = useState("review");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [note, setNote] = useState("");
  const [sentTo, setSentTo] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    client.get(`/api/admin/approvals/${requestId}`)
      .then((res) => setDetail(res.data.request))
      .catch(() => setError("This request could not be loaded."));
  }, [requestId]);

  async function run(action, onOk) {
    setBusy(true);
    setError("");
    try {
      onOk(await action());
    } catch (err) {
      setError(err.response?.data?.error || "That did not work. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  const base = `/api/admin/approvals/${requestId}`;
  const sendCode = (e) => {
    e?.preventDefault();
    run(() => client.post(`${base}/approve/start`, { password }), (res) => {
      setSentTo(res.data.email);
      setPassword("");
      setCode("");
      setStep("code");
    });
  };
  const confirmCode = (e) => {
    e.preventDefault();
    run(() => client.post(`${base}/approve/confirm`, { code }), () => onChanged("Approved and applied"));
  };
  const reject = () => run(() => client.post(`${base}/reject`, { note }), () => onChanged("Request rejected"));
  const cancel = () => run(() => client.post(`${base}/cancel`), () => onChanged("Request cancelled"));

  const pending = detail?.status === "pending";

  return (
    <div className="overlay" onClick={onClose}>
      <div className="modal wide" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h3 style={{ margin: 0 }}>{detail ? `${detail.kindLabel}: ${detail.targetName}` : "Request"}</h3>
          <button type="button" className="modal-close" onClick={onClose}>&times;</button>
        </div>
        <div className="modal-body">
          {error && <div className="alert alert-error">{error}</div>}

          {detail && step === "review" && (
            <>
              <p className="field-hint" style={{ marginTop: 0 }}>
                Asked by <strong>{detail.requestedBy.name}</strong> ({detail.requestedBy.role}) on {formatDate(detail.createdAt)}
                {detail.status !== "pending" && <> &middot; <strong>{detail.status}</strong>{detail.decidedBy ? ` by ${detail.decidedBy}` : ""}</>}
              </p>
              {detail.note && <div className="alert alert-info">Note: {detail.note}</div>}

              {detail.changes.length === 0 ? (
                <p className="field-hint">No visible differences from the current product.</p>
              ) : (
                <div className="table-wrap">
                  <table className="admin-table">
                    <thead><tr><th>What</th><th>Now</th><th>Requested</th></tr></thead>
                    <tbody>
                      {detail.changes.map((c) => (
                        <tr key={c.field}><td><strong>{c.field}</strong></td><td className="cell-wrap">{c.from}</td><td className="cell-wrap">{c.to}</td></tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              {detail.photo && <img src={detail.photo} alt="Requested product" className="request-photo" />}

              {pending && isHead && (
                <>
                  <div className="field" style={{ marginTop: 14 }}>
                    <label htmlFor="reject-note">Reason if you reject (optional)</label>
                    <input id="reject-note" maxLength={255} value={note} onChange={(e) => setNote(e.target.value)} />
                  </div>
                  <div className="form-actions">
                    <button type="button" className="btn btn-outline" disabled={busy} onClick={reject}>Reject</button>
                    <button type="button" className="btn btn-primary" onClick={() => { setError(""); setStep("password"); }}>Approve...</button>
                  </div>
                </>
              )}
              {pending && !isHead && (
                <div className="form-actions">
                  <button type="button" className="btn btn-outline" disabled={busy} onClick={cancel}>Cancel this request</button>
                </div>
              )}
            </>
          )}

          {detail && step === "password" && (
            <form onSubmit={sendCode}>
              <p style={{ marginTop: 0 }}><strong>Step 1 of 2.</strong> Enter your password. We will then email you a one-time code.</p>
              <div className="field">
                <label>Your password</label>
                <PasswordInput value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
              </div>
              <div className="form-actions">
                <button type="button" className="btn btn-outline" onClick={() => setStep("review")}>Back</button>
                <button type="submit" className="btn btn-primary" disabled={busy || !password}>{busy ? "Sending..." : "Send code"}</button>
              </div>
            </form>
          )}

          {detail && step === "code" && (
            <form onSubmit={confirmCode}>
              <p style={{ marginTop: 0 }}><strong>Step 2 of 2.</strong> We sent a 6-digit code to {sentTo}. It lasts 10 minutes. The change is applied only after you enter it.</p>
              <div className="field">
                <label htmlFor="otp-code">Code</label>
                <input
                  id="otp-code" className="otp-input" inputMode="numeric" autoComplete="one-time-code" maxLength={6}
                  value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))} placeholder="123456"
                />
              </div>
              <div className="form-actions">
                <button type="button" className="btn btn-outline" onClick={() => setStep("password")}>Send a new code</button>
                <button type="submit" className="btn btn-primary" disabled={busy || code.length !== 6}>{busy ? "Checking..." : "Approve and apply"}</button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
