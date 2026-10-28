import { useEffect, useRef, useState } from "react";
import client from "../../api/client";

const WELCOME = "Hi! I'm the Rainchem assistant. Ask me about engine oil, RadCool coolant, payments, or your orders. You can ask in English or Tagalog.";
const SUGGEST_AGAIN_AFTER = 4; // AI replies before the admin suggestion may appear again

function Star({ filled }) {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill={filled ? "#f5b301" : "none"} stroke={filled ? "#f5b301" : "#b9b3ab"} strokeWidth="1.8">
      <path d="m12 2.5 2.9 6 6.6.9-4.8 4.6 1.2 6.5L12 17.4l-5.9 3.1 1.2-6.5L2.5 9.4l6.6-.9z" />
    </svg>
  );
}

function Rating({ message, onRate }) {
  const [hover, setHover] = useState(0);
  const value = message.rating || 0;
  return (
    <div className="chat-feedback">
      <div className="chat-stars" onMouseLeave={() => setHover(0)}>
        {[1, 2, 3, 4, 5].map((n) => (
          <button
            key={n} type="button" className="star-btn" aria-label={`Rate ${n} star${n > 1 ? "s" : ""}`}
            onMouseEnter={() => setHover(n)} onClick={() => onRate(message, n)}
          >
            <Star filled={n <= (hover || value)} />
          </button>
        ))}
      </div>
      <div className="chat-feedback-note">{value ? "Thanks for your feedback!" : "Was this helpful?"}</div>
    </div>
  );
}

function HandoffCard({ message, onAccept, onDismiss }) {
  const { human } = message;
  return (
    <div className="handoff-card" role="group" aria-label="Chat with our admin">
      <p>{human.message}</p>
      {human.error && <p className="handoff-error" role="alert">{human.error}</p>}
      <div className="handoff-actions">
        <button type="button" className="btn btn-primary btn-sm" disabled={human.busy} onClick={() => onAccept(message)}>
          {human.busy ? "Opening..." : "Chat with admin"}
        </button>
        <button type="button" className="btn btn-outline btn-sm" onClick={() => onDismiss(message)}>Not now</button>
      </div>
      {human.reason !== "requested" && <p className="handoff-note">Your question and my answer will be shared with the admin so you do not have to repeat it.</p>}
    </div>
  );
}

/** The AI assistant tab. It stays mounted while the chat is open so the conversation is kept. */
export default function AiChat({ onOpenLive }) {
  const [messages, setMessages] = useState([{ uid: 0, from: "bot", text: WELCOME }]);
  const nextUid = useRef(1);
  const newUid = () => {
    nextUid.current += 1;
    return nextUid.current;
  };
  const [suggestions, setSuggestions] = useState([]);
  const [input, setInput] = useState("");
  const [typing, setTyping] = useState(false);
  const lastQuestion = useRef(null);
  const botReplies = useRef(0);
  const suggestedAt = useRef(null);
  const bodyRef = useRef(null);

  useEffect(() => {
    client.get("/api/chat/suggestions").then((res) => setSuggestions(res.data.suggestions)).catch(() => {});
  }, []);

  useEffect(() => {
    if (bodyRef.current) bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
  }, [messages, typing]);

  // The admin suggestion is shown when the AI says so, but not after every message.
  function allowSuggestion(reason) {
    if (reason === "requested") return true;
    return suggestedAt.current === null || botReplies.current - suggestedAt.current >= SUGGEST_AGAIN_AFTER;
  }

  function withHuman(data) {
    if (!data.needsHuman || !allowSuggestion(data.humanReason)) return null;
    suggestedAt.current = botReplies.current;
    return { message: data.humanMessage, reason: data.humanReason };
  }

  async function ask(question) {
    setMessages((prev) => [...prev, { uid: newUid(), from: "user", text: question }]);
    setSuggestions([]);
    setTyping(true);
    try {
      const res = await client.post("/api/chat/ask", { question, previousQuestion: lastQuestion.current });
      lastQuestion.current = question;
      const { answer, confidence, resolved, related, logId, canRate } = res.data;
      botReplies.current += 1;
      setMessages((prev) => [
        ...prev,
        {
          uid: newUid(), from: "bot", text: answer, confidence: resolved ? confidence : null,
          related: related || [], logId, canRate: Boolean(canRate && logId), rating: 0,
          human: withHuman(res.data),
        },
      ]);
    } catch (err) {
      const status = err.response?.status;
      const text = status === 401 || status === 422
        ? "Your session expired. Please log in again to keep chatting."
        : !err.response
          ? "I can't reach the server right now. Please check your connection and try again."
          : err.response?.data?.error || "Sorry, something went wrong. Please try again.";
      setMessages((prev) => [...prev, { uid: newUid(), from: "bot", text }]);
    } finally {
      setTyping(false);
    }
  }

  async function rate(message, rating) {
    setMessages((prev) => prev.map((m) => (m.uid === message.uid ? { ...m, rating } : m)));
    try {
      const res = await client.post("/api/chat/feedback", { logId: message.logId, rating });
      const human = res.data.needsHuman && !message.human ? withHuman(res.data) : null;
      if (human) setMessages((prev) => prev.map((m) => (m.logId === message.logId ? { ...m, human } : m)));
    } catch {
      /* rating is a nice-to-have: never interrupt the chat for it */
    }
  }

  function patchHuman(message, patch) {
    setMessages((prev) => prev.map((m) => (m.uid === message.uid ? { ...m, human: m.human && { ...m.human, ...patch } } : m)));
  }

  async function accept(message) {
    // For an explicit "talk to a person" request there is nothing useful to hand over.
    if (message.human.reason === "requested") {
      patchHuman(message, { busy: false });
      onOpenLive();
      return;
    }
    const recent = messages.filter((m) => m.logId).map((m) => m.logId).slice(-3);
    const logIds = recent.includes(message.logId) ? recent : [...recent.slice(-2), message.logId].filter(Boolean);
    patchHuman(message, { busy: true, error: null });
    try {
      await client.post("/api/live-chat/from-ai", { logIds });
      patchHuman(message, { busy: false });
      onOpenLive();
    } catch (err) {
      patchHuman(message, { busy: false, error: err.response?.data?.error || "Could not open the live chat. Please try again." });
    }
  }

  function dismiss(message) {
    setMessages((prev) => prev.map((m) => (m.uid === message.uid ? { ...m, human: null } : m)));
  }

  function handleSend() {
    const question = input.trim();
    if (!question || typing) return;
    setInput("");
    ask(question);
  }

  return (
    <>
      <div className="chat-body" ref={bodyRef}>
        {messages.map((m) => (
          <div key={m.uid} className={`chat-block ${m.from}`}>
            {m.from === "bot" && <span className="chat-label ai">AI assistant</span>}
            <div className={`chat-msg ${m.from}`}>
              {m.text}
              {m.confidence != null && (
                <div style={{ fontSize: 10, marginTop: 4, opacity: 0.7 }}>Match confidence: {m.confidence}%</div>
              )}
            </div>
            {m.related?.length > 0 && (
              <div className="chat-chips">
                {m.related.map((r, j) => (
                  <button key={`${r.id}-${j}`} type="button" className="chat-chip" disabled={typing} onClick={() => ask(r.question)}>
                    {r.question}
                  </button>
                ))}
              </div>
            )}
            {m.human && <HandoffCard message={m} onAccept={accept} onDismiss={dismiss} />}
            {m.canRate && <Rating message={m} onRate={rate} />}
          </div>
        ))}
        {typing && (
          <div className="chat-block bot">
            <div className="chat-msg bot chat-typing"><span /><span /><span /></div>
          </div>
        )}
      </div>
      {suggestions.length > 0 && (
        <div className="chat-chips" style={{ padding: "0 14px 10px" }}>
          {suggestions.map((s) => (
            <button key={s.id} type="button" className="chat-chip" onClick={() => ask(s.question)}>{s.question}</button>
          ))}
        </div>
      )}
      <div className="chat-input">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder="Ask about oil, coolant, orders..."
          maxLength={500}
        />
        <button onClick={handleSend} disabled={typing} aria-label="Send">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.4">
            <path d="M22 2 11 13M22 2l-7 20-4-9-9-4 20-7z" />
          </svg>
        </button>
      </div>
    </>
  );
}
