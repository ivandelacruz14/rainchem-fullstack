import Avatar from "../../components/chat/Avatar";
import { formatDay, formatTime } from "../../utils/format";

const FILTERS = [["all", "All"], ["unread", "Unread"], ["open", "Open"], ["pending", "Pending"], ["resolved", "Resolved"]];
const SORTS = [["latest", "Latest activity"], ["unread", "Most unread"], ["oldest", "Oldest first"]];

export function photoPath(user) {
  return user ? `/api/admin/live-chat/users/${user.id}/photo` : null;
}

export default function ConversationList({ rows, counts, filter, onFilter, search, onSearch, sort, onSort, openId, onOpen }) {
  return (
    <aside className="lc-list" aria-label="Conversations">
      <div className="lc-list-tools">
        <input type="search" aria-label="Search customers" placeholder="Search name or email..." value={search} onChange={(e) => onSearch(e.target.value)} />
        <select aria-label="Sort conversations" value={sort} onChange={(e) => onSort(e.target.value)}>
          {SORTS.map(([key, label]) => <option key={key} value={key}>{label}</option>)}
        </select>
      </div>
      <div className="lc-filters" role="tablist" aria-label="Filter conversations">
        {FILTERS.map(([key, label]) => (
          <button key={key} type="button" role="tab" aria-selected={filter === key} className={`chip ${filter === key ? "active" : ""}`} onClick={() => onFilter(key)}>
            {label}{counts?.[key] ? ` (${counts[key]})` : ""}
          </button>
        ))}
      </div>

      {rows === null ? <p className="field-hint">Loading...</p> : rows.length === 0 ? (
        <p className="field-hint">{search || filter !== "all" ? "No conversations match." : "No customer has written to you yet."}</p>
      ) : (
        <ul className="lc-rows">
          {rows.map((r) => (
            <li key={r.id}>
              <button type="button" className={`lc-row ${r.id === openId ? "active" : ""} ${r.needsAttention ? "attention" : ""}`} onClick={() => onOpen(r.id)}>
                <Avatar user={r.user} photoPath={photoPath(r.user)} online={r.online} size={42} />
                <span className="lc-row-body">
                  <span className="lc-row-top">
                    <strong>{r.user?.name}</strong>
                    <time className="lc-row-time">{r.lastMessageAt ? (new Date().toDateString() === new Date(r.lastMessageAt + "Z").toDateString() ? formatTime(r.lastMessageAt) : formatDay(r.lastMessageAt)) : ""}</time>
                  </span>
                  <span className="lc-row-preview">{r.lastMessage ? `${r.lastMessage.from === "admin" ? "You: " : ""}${r.lastMessage.text}` : "No messages"}</span>
                  <span className="lc-row-meta">
                    <span className={`status-pill chat-${r.status}`}>{r.statusLabel}</span>
                    <span className="lc-row-topic">{r.topicLabel}{r.orderNumber ? ` \u00b7 ${r.orderNumber}` : ""}</span>
                    {r.unread > 0 && <span className="nav-badge" aria-label={`${r.unread} unread`}>{r.unread}</span>}
                  </span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </aside>
  );
}
