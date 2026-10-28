import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import client from "../../api/client";
import ConfirmDialog from "../../components/ConfirmDialog";
import MessageThread from "../../components/chat/MessageThread";
import { useAdminAuth } from "../../context/AdminAuthContext";
import { useToast } from "../../context/ToastContext";
import { formatTime, formatDay } from "../../utils/format";

const LIST_POLL_MS = 5000;
const THREAD_POLL_MS = 3000;

function merge(current, incoming) {
  const byId = new Map(current.map((m) => [m.id, m]));
  incoming.forEach((m) => byId.set(m.id, m));
  return [...byId.values()].sort((a, b) => a.id - b.id);
}

function Thread({ conversation, onBack, onDeleted, canDeleteConversation }) {
  const showToast = useToast();
  const [messages, setMessages] = useState([]);
  const [info, setInfo] = useState(conversation);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [toDelete, setToDelete] = useState(null); // a message or "conversation"
  const [deleting, setDeleting] = useState(false);
  const cursor = useRef(null);
  const busy = useRef(false);

  const load = useCallback(async (initial) => {
    if (busy.current) return;
    busy.current = true;
    try {
      const res = await client.get(`/api/admin/live-chat/conversations/${conversation.id}`, {
        params: initial || !cursor.current ? {} : { since: cursor.current },
      });
      const incoming = res.data.messages;
      cursor.current = incoming.reduce((max, m) => (!max || m.updatedAt > max ? m.updatedAt : max), cursor.current);
      setInfo(res.data.conversation);
      setMessages((prev) => (initial ? incoming : merge(prev, incoming)));
    } catch {
      /* the next poll retries */
    } finally {
      busy.current = false;
    }
  }, [conversation.id]);

  useEffect(() => {
    cursor.current = null;
    setMessages([]);
    load(true);
    const timer = setInterval(() => {
      if (document.visibilityState !== "hidden") load(false);
    }, THREAD_POLL_MS);
    return () => clearInterval(timer);
  }, [load]);

  // Opening the conversation marks the customer's messages as read.
  const unread = messages.some((m) => m.sender === "user" && !m.deleted && m.status !== "read");
  useEffect(() => {
    if (unread && document.visibilityState !== "hidden") {
      client.post(`/api/admin/live-chat/conversations/${conversation.id}/read`).catch(() => {});
    }
  }, [unread, messages.length, conversation.id]);

  async function send(e) {
    e.preventDefault();
    const body = draft.trim();
    if (!body || sending) return;
    setSending(true);
    setError("");
    try {
      const res = await client.post(`/api/admin/live-chat/conversations/${conversation.id}/messages`, { body });
      setMessages((prev) => merge(prev, [res.data.message]));
      setDraft("");
    } catch (err) {
      setError(err.response?.data?.error || "The reply could not be sent.");
    } finally {
      setSending(false);
    }
  }

  async function confirmDelete() {
    setDeleting(true);
    try {
      if (toDelete === "conversation") {
        await client.delete(`/api/admin/live-chat/conversations/${conversation.id}`);
        showToast("Conversation deleted", "success");
        onDeleted();
      } else {
        const res = await client.delete(`/api/admin/live-chat/messages/${toDelete.id}`);
        setMessages((prev) => merge(prev, [res.data.message]));
      }
      setToDelete(null);
    } catch (err) {
      showToast(err.response?.data?.error || "Could not delete", "error");
      setToDelete(null);
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="lc-thread">
      <div className="lc-thread-head">
        <button type="button" className="btn btn-outline btn-sm lc-back" onClick={onBack}>&larr; Inbox</button>
        <div className="lc-thread-title">
          <strong>{info.user?.name}</strong>
          <span>{info.user?.email}</span>
          <span>{info.topicLabel}{info.orderNumber ? ` \u00b7 Order ${info.orderNumber}` : ""}</span>
        </div>
        {canDeleteConversation && (
          <button type="button" className="btn btn-outline btn-sm" onClick={() => setToDelete("conversation")}>Delete conversation</button>
        )}
      </div>
      <div className="lc-messages">
        <MessageThread
          messages={messages} viewer="admin" canDelete={(m) => !m.deleted} onDelete={setToDelete}
          empty="No messages yet."
        />
      </div>
      <form className="lc-compose" onSubmit={send}>
        {error && <div className="live-error" role="alert">{error}</div>}
        <div className="lc-compose-row">
          <textarea
            rows={2} maxLength={2000} value={draft} onChange={(e) => setDraft(e.target.value)} aria-label="Reply to the customer"
            placeholder="Write a reply..." onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) send(e); }}
          />
          <button type="submit" className="btn btn-primary" disabled={sending || !draft.trim()}>{sending ? "Sending..." : "Send"}</button>
        </div>
      </form>

      {toDelete && (
        <ConfirmDialog
          title={toDelete === "conversation" ? "Delete this whole conversation?" : "Delete this message?"}
          busy={deleting}
          confirmLabel={toDelete === "conversation" ? "Delete conversation" : "Delete message"}
          message={toDelete === "conversation"
            ? `All messages with ${info.user?.name} will be permanently deleted for you and for the customer. This cannot be undone.`
            : "The text is permanently erased. Both sides will see “This message was deleted”."}
          onCancel={() => setToDelete(null)} onConfirm={confirmDelete}
        />
      )}
    </div>
  );
}

export default function LiveChat() {
  const { admin } = useAdminAuth();
  const [params, setParams] = useSearchParams();
  const [rows, setRows] = useState(null);
  const [search, setSearch] = useState("");
  const [openId, setOpenId] = useState(Number(params.get("conversation")) || null);

  const loadList = useCallback(() => {
    client.get("/api/admin/live-chat/conversations", { params: search ? { search } : {} })
      .then((res) => setRows(res.data.conversations))
      .catch(() => setRows((prev) => prev || []));
  }, [search]);

  useEffect(() => {
    loadList();
    const timer = setInterval(() => {
      if (document.visibilityState !== "hidden") loadList();
    }, LIST_POLL_MS);
    return () => clearInterval(timer);
  }, [loadList]);

  function open(id) {
    setOpenId(id);
    setParams(id ? { conversation: id } : {}, { replace: true });
  }

  const current = rows?.find((r) => r.id === openId) || null;

  return (
    <div>
      <div className="admin-topbar">
        <div>
          <h1>Live Chat</h1>
          <p>Customers who contacted you. Replies appear in their chat window within a few seconds.</p>
        </div>
      </div>

      <div className={`lc-shell ${current ? "has-open" : ""}`}>
        <aside className="lc-list admin-panel">
          <div className="field" style={{ marginBottom: 10 }}>
            <input type="search" aria-label="Search customers" placeholder="Search name or email..." value={search} onChange={(e) => setSearch(e.target.value)} />
          </div>
          {rows === null ? <p className="field-hint">Loading...</p> : rows.length === 0 ? (
            <p className="field-hint">{search ? "No customers match." : "No customer has written to you yet."}</p>
          ) : (
            <ul className="lc-rows">
              {rows.map((r) => (
                <li key={r.id}>
                  <button type="button" className={`lc-row ${r.id === openId ? "active" : ""}`} onClick={() => open(r.id)}>
                    <div className="lc-row-top">
                      <strong>{r.user?.name}</strong>
                      {r.unread > 0 && <span className="nav-badge">{r.unread}</span>}
                    </div>
                    <div className="lc-row-preview">
                      {r.lastMessage ? `${r.lastMessage.from === "admin" ? "You: " : ""}${r.lastMessage.text}` : "No messages"}
                    </div>
                    <div className="lc-row-meta">
                      <span>{r.topicLabel}{r.orderNumber ? ` \u00b7 ${r.orderNumber}` : ""}</span>
                      <span>{r.lastMessageAt ? `${formatDay(r.lastMessageAt)} ${formatTime(r.lastMessageAt)}` : ""}</span>
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </aside>

        <section className="lc-pane admin-panel">
          {current ? (
            <Thread
              key={current.id} conversation={current} onBack={() => open(null)}
              canDeleteConversation={Boolean(admin?.isHead)}
              onDeleted={() => { open(null); loadList(); }}
            />
          ) : (
            <p className="field-hint" style={{ margin: "30px auto", textAlign: "center" }}>Choose a customer on the left to read and reply.</p>
          )}
        </section>
      </div>
    </div>
  );
}
