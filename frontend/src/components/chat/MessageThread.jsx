import { useEffect, useRef } from "react";
import { formatDate, formatDay, formatTime, serverDate } from "../../utils/format";
import Ticks from "./Ticks";

function dayKey(iso) {
  const d = serverDate(iso);
  return d ? `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}` : "";
}

/**
 * The conversation, shared by the customer and the admin screens.
 * `viewer` is "user" or "admin". `canDelete(message)` decides which messages show a delete button.
 */
export default function MessageThread({ messages, viewer, canDelete, onDelete, empty }) {
  const endRef = useRef(null);

  const lastChange = messages[messages.length - 1]?.updatedAt;
  useEffect(() => {
    endRef.current?.scrollIntoView?.({ block: "end" });
  }, [messages.length, lastChange]);

  if (messages.length === 0) return <div className="thread-empty">{empty}</div>;

  return (
    <div className="thread" aria-live="polite">
      {messages.map((m, index) => {
        const showDay = index === 0 || dayKey(m.createdAt) !== dayKey(messages[index - 1].createdAt);
        const mine = m.sender === viewer;
        const label = m.sender === "admin" ? `${m.senderName || "Admin"} (Admin)` : m.senderName;
        return (
          <div key={m.id}>
            {showDay && <div className="thread-day">{formatDay(m.createdAt)}</div>}
            <div className={`bubble-row ${mine ? "mine" : "theirs"}`}>
              <div className={`bubble ${mine ? "mine" : "theirs"} ${m.deleted ? "deleted" : ""} ${m.sender === "admin" ? "from-admin" : ""}`}>
                {!mine && <div className="bubble-from">{label}</div>}
                {m.kind === "context" && !m.deleted && <div className="bubble-tag">Sent from AI chat</div>}
                {m.deleted ? <span className="bubble-text">This message was deleted</span> : <span className="bubble-text">{m.body}</span>}
                <div className="bubble-meta">
                  <time dateTime={m.createdAt} title={formatDate(m.createdAt)}>{formatTime(m.createdAt)}</time>
                  {mine && !m.deleted && <Ticks status={m.status} />}
                  {!m.deleted && canDelete?.(m) && (
                    <button type="button" className="bubble-delete" aria-label="Delete message" title="Delete message" onClick={() => onDelete(m)}>
                      &times;
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
        );
      })}
      <div ref={endRef} />
    </div>
  );
}
