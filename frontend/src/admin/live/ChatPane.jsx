import { useCallback, useEffect, useRef, useState } from "react";
import client from "../../api/client";
import Avatar from "../../components/chat/Avatar";
import Composer from "../../components/chat/Composer";
import MessageThread from "../../components/chat/MessageThread";
import ConfirmDialog from "../../components/ConfirmDialog";
import { useToast } from "../../context/ToastContext";
import { photoPath } from "./ConversationList";

const THREAD_POLL_MS = 3000;

function merge(current, incoming) {
  const byId = new Map(current.map((m) => [m.id, m]));
  incoming.forEach((m) => byId.set(m.id, m));
  return [...byId.values()].sort((a, b) => a.id - b.id);
}

export default function ChatPane({ conversation, canDeleteConversation, onBack, onInfo, onDeleted, onChanged }) {
  const showToast = useToast();
  const [messages, setMessages] = useState([]);
  const [info, setInfo] = useState(conversation);
  const [maxMb, setMaxMb] = useState(3);
  const [toDelete, setToDelete] = useState(null); // a message, or "conversation"
  const [deleting, setDeleting] = useState(false);
  const cursor = useRef(null);
  const busy = useRef(false);

  const load = useCallback(async (initial) => {
    if (busy.current) return;
    busy.current = true;
    try {
      const res = await client.get(`/api/admin/live-chat/conversations/${conversation.id}`, { params: initial || !cursor.current ? {} : { since: cursor.current } });
      const incoming = res.data.messages;
      cursor.current = incoming.reduce((max, m) => (!max || m.updatedAt > max ? m.updatedAt : max), cursor.current);
      setInfo(res.data.conversation);
      setMaxMb(res.data.maxUploadMb || 3);
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
    const timer = setInterval(() => { if (document.visibilityState !== "hidden") load(false); }, THREAD_POLL_MS);
    return () => clearInterval(timer);
  }, [load]);

  // Having the conversation open marks the customer's messages as read.
  const unread = messages.some((m) => m.sender === "user" && !m.deleted && m.status !== "read");
  useEffect(() => {
    if (unread && document.visibilityState !== "hidden") {
      client.post(`/api/admin/live-chat/conversations/${conversation.id}/read`).then(() => onChanged?.()).catch(() => {});
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [unread, messages.length, conversation.id]);

  async function send({ body, file }) {
    let payload = { body };
    if (file) {
      payload = new FormData();
      payload.append("image", file);
      if (body) payload.append("body", body);
    }
    const res = await client.post(`/api/admin/live-chat/conversations/${conversation.id}/messages`, payload);
    setMessages((prev) => merge(prev, [res.data.message]));
    if (res.data.conversation) setInfo(res.data.conversation);
    onChanged?.();
  }

  async function setStatus(status) {
    try {
      const res = await client.post(`/api/admin/live-chat/conversations/${conversation.id}/status`, { status });
      setInfo(res.data.conversation);
      onChanged?.();
      showToast(status === "resolved" ? "Marked as resolved" : "Conversation reopened", "success");
    } catch (err) {
      showToast(err.response?.data?.error || "Could not change the status", "error");
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

  const resolved = info.status === "resolved";

  return (
    <section className="lc-chat" aria-label={`Conversation with ${info.user?.name}`}>
      <header className="lc-chat-head">
        <button type="button" className="btn btn-outline btn-sm lc-back" onClick={onBack}>&larr; Inbox</button>
        <Avatar user={info.user} photoPath={photoPath(info.user)} online={info.online} size={42} />
        <div className="lc-chat-title">
          <strong>{info.user?.name}</strong>
          <span>{info.online ? "Online now" : "Offline"} &middot; {info.topicLabel}{info.orderNumber ? ` \u00b7 Order ${info.orderNumber}` : ""}</span>
        </div>
        <span className={`status-pill chat-${info.status}`}>{info.statusLabel}</span>
        <div className="lc-chat-actions">
          <button type="button" className="btn btn-outline btn-sm lc-info-btn" onClick={onInfo}>Customer &amp; orders</button>
          <button type="button" className="btn btn-outline btn-sm" onClick={() => setStatus(resolved ? "open" : "resolved")}>{resolved ? "Reopen" : "Mark as resolved"}</button>
          {canDeleteConversation && <button type="button" className="btn btn-outline btn-sm" onClick={() => setToDelete("conversation")}>Delete conversation</button>}
        </div>
      </header>
      <div className="lc-messages">
        <MessageThread messages={messages} viewer="admin" canDelete={(m) => !m.deleted} onDelete={setToDelete} empty="No messages yet. Say hello below." imageBase="/api/admin/live-chat/attachments" />
      </div>
      <Composer onSend={send} inputLabel="Reply to the customer" sendLabel="Send" placeholder="Write a reply..." maxMb={maxMb} multiline />

      {toDelete && (
        <ConfirmDialog
          title={toDelete === "conversation" ? "Delete this whole conversation?" : "Delete this message?"} busy={deleting}
          confirmLabel={toDelete === "conversation" ? "Delete conversation" : "Delete message"}
          message={toDelete === "conversation"
            ? `All messages and images with ${info.user?.name} will be permanently deleted for you and for the customer. A record that this happened is kept in the audit log. This cannot be undone.`
            : "The text or image is permanently erased. Both sides will see “This message was deleted”, and a record of the deletion is kept in the audit log."}
          onCancel={() => setToDelete(null)} onConfirm={confirmDelete}
        />
      )}
    </section>
  );
}
