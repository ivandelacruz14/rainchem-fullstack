import { useEffect, useRef, useState } from "react";
import client from "../../api/client";
import { useUI } from "../../context/UIContext";
import useLiveChat from "../../hooks/useLiveChat";
import ConfirmDialog from "../ConfirmDialog";
import MessageThread from "./MessageThread";

const MAX_LENGTH = 2000;

export default function LiveChatPanel() {
  const { liveIntent, clearLiveIntent } = useUI();
  const chat = useLiveChat(true);
  const [draft, setDraft] = useState("");
  const [topic, setTopic] = useState(liveIntent?.topic || "other");
  const [orderId, setOrderId] = useState(liveIntent?.orderId ? String(liveIntent.orderId) : "");
  const [orders, setOrders] = useState([]);
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);
  const [toDelete, setToDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const handedOver = useRef(false);

  useEffect(() => {
    client.get("/api/live-chat/orders").then((res) => setOrders(res.data.orders)).catch(() => {});
  }, []);

  // Questions passed on from the AI assistant are sent once, then the request is cleared.
  useEffect(() => {
    if (!liveIntent || handedOver.current) return;
    handedOver.current = true;
    clearLiveIntent();
  }, [liveIntent, clearLiveIntent]);

  const unreadFromAdmin = chat.messages.some((m) => m.sender === "admin" && !m.deleted && m.status !== "read");
  useEffect(() => {
    if (unreadFromAdmin && document.visibilityState !== "hidden") chat.markRead();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [unreadFromAdmin, chat.messages.length]);

  const hasConversation = Boolean(chat.conversation);

  async function submit(e) {
    e.preventDefault();
    const body = draft.trim();
    if (!body || sending) return;
    setSending(true);
    setError("");
    try {
      const extra = hasConversation ? {} : { topic, orderId: topic === "order" && orderId ? Number(orderId) : undefined };
      await chat.send(body, extra);
      setDraft("");
    } catch (err) {
      setError(err.response?.data?.error || "Your message could not be sent. Please try again.");
    } finally {
      setSending(false);
    }
  }

  async function confirmDelete() {
    setDeleting(true);
    try {
      await chat.remove(toDelete);
      setToDelete(null);
    } catch (err) {
      setError(err.response?.data?.error || "That message could not be deleted.");
      setToDelete(null);
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="live-panel">
      <div className="chat-body live-body">
        {chat.loading ? (
          <div className="thread-empty">Loading...</div>
        ) : chat.error ? (
          <div className="thread-empty">{chat.error}</div>
        ) : (
          <MessageThread
            messages={chat.messages}
            viewer="user"
            canDelete={(m) => m.sender === "user" && !m.deleted}
            onDelete={setToDelete}
            empty={
              <>
                <strong>Chat with our admin</strong>
                <p>Tell us what you need help with. A person from our team will reply here. Your order, product, payment and account questions are welcome.</p>
              </>
            }
          />
        )}
      </div>

      <form className="live-compose" onSubmit={submit}>
        {!hasConversation && !chat.loading && (
          <div className="live-topic">
            <select aria-label="What do you need help with?" value={topic} onChange={(e) => setTopic(e.target.value)}>
              {(chat.topics.length ? chat.topics : [{ key: "other", label: "Something else" }]).map((t) => (
                <option key={t.key} value={t.key}>{t.label}</option>
              ))}
            </select>
            {topic === "order" && (
              <select aria-label="Which order?" value={orderId} onChange={(e) => setOrderId(e.target.value)}>
                <option value="">Which order? (optional)</option>
                {orders.map((o) => <option key={o.id} value={o.id}>{o.orderNumber} - {o.statusLabel}</option>)}
              </select>
            )}
          </div>
        )}
        {hasConversation && chat.conversation.orderNumber && (
          <div className="live-context">About order {chat.conversation.orderNumber}</div>
        )}
        {error && <div className="live-error" role="alert">{error}</div>}
        <div className="chat-input live-input">
          <input
            value={draft} maxLength={MAX_LENGTH} onChange={(e) => setDraft(e.target.value)}
            placeholder="Type a message to the admin..." aria-label="Message to the admin"
          />
          <button type="submit" disabled={sending || !draft.trim()} aria-label="Send message">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.4"><path d="M22 2 11 13M22 2l-7 20-4-9-9-4 20-7z" /></svg>
          </button>
        </div>
      </form>

      {toDelete && (
        <ConfirmDialog
          title="Delete this message?" busy={deleting} confirmLabel="Delete"
          message="It will be removed for you and for the admin. Both of you will see “This message was deleted”. This cannot be undone."
          onCancel={() => setToDelete(null)} onConfirm={confirmDelete}
        />
      )}
    </div>
  );
}
