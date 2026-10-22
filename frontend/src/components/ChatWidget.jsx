import { useState, useEffect, useRef } from "react";
import { useAuth } from "../context/AuthContext";
import { useUI } from "../context/UIContext";
import client from "../api/client";

const WELCOME = "Hi! I'm the Rainchem assistant. Ask me about engine oil, RadCool coolant, payments, or your orders. You can ask in English or Tagalog.";

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

export default function ChatWidget() {
  const { user } = useAuth();
  const { chatOpen, toggleChat, requireLogin } = useUI();
  const [messages, setMessages] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [input, setInput] = useState("");
  const [started, setStarted] = useState(false);
  const [typing, setTyping] = useState(false);
  const lastQuestion = useRef(null);
  const bodyRef = useRef(null);

  useEffect(() => {
    if (chatOpen && user && !started) {
      setStarted(true);
      setMessages([{ from: "bot", text: WELCOME }]);
      client.get("/api/chat/suggestions").then((res) => setSuggestions(res.data.suggestions)).catch(() => {});
    }
  }, [chatOpen, user, started]);

  useEffect(() => {
    if (bodyRef.current) bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
  }, [messages, typing]);

  function handleLauncherClick() {
    if (!user) {
      requireLogin("login", "Please log in to chat with our AI assistant");
      return;
    }
    toggleChat();
  }

  async function ask(question) {
    setMessages((prev) => [...prev, { from: "user", text: question }]);
    setSuggestions([]);
    setTyping(true);
    try {
      const res = await client.post("/api/chat/ask", { question, previousQuestion: lastQuestion.current });
      lastQuestion.current = question;
      const { answer, confidence, resolved, related, logId, canRate } = res.data;
      setMessages((prev) => [
        ...prev,
        {
          from: "bot", text: answer, confidence: resolved ? confidence : null,
          related: related || [], logId, canRate: Boolean(canRate && logId), rating: 0,
        },
      ]);
    } catch (err) {
      const status = err.response?.status;
      const text = status === 401 || status === 422
        ? "Your session expired. Please log in again to keep chatting."
        : !err.response
          ? "I can't reach the server right now. Please check your connection and try again."
          : err.response?.data?.error || "Sorry, something went wrong. Please try again.";
      setMessages((prev) => [...prev, { from: "bot", text }]);
    } finally {
      setTyping(false);
    }
  }

  async function rate(message, rating) {
    setMessages((prev) => prev.map((m) => (m === message ? { ...m, rating } : m)));
    try {
      await client.post("/api/chat/feedback", { logId: message.logId, rating });
    } catch {
      /* rating is a nice-to-have: never interrupt the chat for it */
    }
  }

  function handleSend() {
    const question = input.trim();
    if (!question || typing) return;
    setInput("");
    ask(question);
  }

  return (
    <>
      <button className="chat-launcher" onClick={handleLauncherClick} title="AI Assistant">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
        </svg>
      </button>

      {chatOpen && user && (
        <div className="chat-panel">
          <div className="chat-head">
            <h4>Rainchem Assistant</h4>
            <p>Trained on our admin-verified knowledge base</p>
          </div>
          <div className="chat-body" ref={bodyRef}>
            {messages.map((m, i) => (
              <div key={i} className={`chat-block ${m.from}`}>
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
        </div>
      )}
    </>
  );
}
