import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import client from "../api/client";

const POLL_MS = 60000;

function when(iso) {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "" : d.toLocaleString("en-PH", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

/** The customer's bell: rider assigned, out for delivery, delivered, rescheduled. Checks again every minute. */
export default function NotificationBell() {
  const navigate = useNavigate();
  const [items, setItems] = useState([]);
  const [unread, setUnread] = useState(0);
  const [open, setOpen] = useState(false);
  const rootRef = useRef(null);

  const load = useCallback(() => {
    client.get("/api/notifications")
      .then((r) => { setItems(r.data.notifications); setUnread(r.data.unread); })
      .catch(() => {});
  }, []);

  useEffect(() => {
    load();
    const timer = setInterval(load, POLL_MS);
    return () => clearInterval(timer);
  }, [load]);

  useEffect(() => {
    if (!open) return undefined;
    const onDown = (e) => { if (rootRef.current && !rootRef.current.contains(e.target)) setOpen(false); };
    const onKey = (e) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("mousedown", onDown); document.removeEventListener("keydown", onKey); };
  }, [open]);

  function toggle() {
    const next = !open;
    setOpen(next);
    if (next && unread > 0) {
      client.post("/api/notifications/read", {}).then(() => setUnread(0)).catch(() => {});
    }
  }

  function go(n) {
    setOpen(false);
    if (n.link) navigate(n.link);
  }

  return (
    <div className="notif" ref={rootRef}>
      <button type="button" className="icon-btn notif-btn" aria-label={unread ? `Notifications, ${unread} new` : "Notifications"}
        aria-expanded={open} onClick={toggle}>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" />
          <path d="M13.7 21a2 2 0 0 1-3.4 0" />
        </svg>
        {unread > 0 && <span className="chip-badge">{unread > 9 ? "9+" : unread}</span>}
      </button>
      {open && (
        <div className="notif-panel" role="dialog" aria-label="Notifications">
          <div className="notif-head">Notifications</div>
          {items.length === 0 ? (
            <p className="notif-empty">Nothing yet. Updates about your orders show up here.</p>
          ) : (
            <ul className="notif-list">
              {items.map((n) => (
                <li key={n.id}>
                  <button type="button" className={`notif-item ${n.isRead ? "" : "unread"}`} onClick={() => go(n)}>
                    <strong>{n.subject}</strong>
                    <span>{n.body}</span>
                    <em>{when(n.sentAt)}</em>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
