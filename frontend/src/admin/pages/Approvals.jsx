import { useEffect, useState } from "react";
import client from "../../api/client";
import { useAdminAuth } from "../../context/AdminAuthContext";
import { useToast } from "../../context/ToastContext";
import { formatDate } from "../../utils/format";
import RequestDialog from "../approvals/RequestDialog";

const TABS = [["pending", "Waiting"], ["approved", "Approved"], ["rejected", "Rejected"], ["cancelled", "Cancelled"]];

export default function Approvals() {
  const { admin } = useAdminAuth();
  const showToast = useToast();
  const [status, setStatus] = useState("pending");
  const [requests, setRequests] = useState(null);
  const [openId, setOpenId] = useState(null);

  function load() {
    client.get("/api/admin/approvals", { params: { status } })
      .then((res) => setRequests(res.data.requests))
      .catch(() => setRequests([]));
  }
  useEffect(() => { setRequests(null); load(); }, [status]);

  function changed(message) {
    setOpenId(null);
    showToast(message, "success");
    load();
    window.dispatchEvent(new Event("rainchem:approvals-changed"));
  }

  return (
    <div>
      <div className="admin-topbar">
        <div>
          <h1>Approvals</h1>
          <p>
            {admin?.isHead
              ? "Product changes from your team wait here. To approve one you enter your password and then a code we email you."
              : "Your product changes wait here until the Head Admin approves them."}
          </p>
        </div>
      </div>

      <div className="tab-bar">
        {TABS.map(([key, label]) => (
          <button type="button" key={key} className={`tab-btn ${status === key ? "active" : ""}`} onClick={() => setStatus(key)}>{label}</button>
        ))}
      </div>

      <div className="admin-panel">
        <div className="table-wrap">
          <table className="admin-table stack">
            <thead><tr><th>Request</th><th>Asked by</th><th>Date</th><th>Status</th><th></th></tr></thead>
            <tbody>
              {requests === null ? (
                <tr><td colSpan={5}>Loading...</td></tr>
              ) : requests.length === 0 ? (
                <tr><td colSpan={5}>Nothing here.</td></tr>
              ) : requests.map((r) => (
                <tr key={r.id}>
                  <td data-label="Request" className="cell-name">{r.kindLabel}<div className="muted">{r.targetName}</div></td>
                  <td data-label="Asked by">{r.requestedBy.name}<div className="muted">{r.requestedBy.role}</div></td>
                  <td data-label="Date">{formatDate(r.createdAt).split(",").slice(0, 2).join(",")}</td>
                  <td data-label="Status"><span className={`status-pill req-${r.status}`}>{r.status}</span></td>
                  <td data-label="" className="row-cell">
                    <button type="button" className="icon-action wide" onClick={() => setOpenId(r.id)}>
                      {r.status === "pending" && admin?.isHead ? "Review" : "Details"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {openId && <RequestDialog requestId={openId} isHead={Boolean(admin?.isHead)} onClose={() => setOpenId(null)} onChanged={changed} />}
    </div>
  );
}
