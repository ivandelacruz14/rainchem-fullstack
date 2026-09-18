import { useState, useEffect, useRef } from "react";
import { useAuth } from "../context/AuthContext";
import { useUI } from "../context/UIContext";
import client from "../api/client";

export default function ChatWidget() {
  const { user } = useAuth();
  const { chatOpen, toggleChat, requireLogin } = useUI();
  const [messages, setMessages] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [input, setInput] = useState("");
  const [started, setStarted] = useState(false);
  const bodyRef = useRef(null);

  useEffect(() => {
    if (chatOpen && user && !started) {
      setStarted(true);
      setMessages([{
        from: "bot",
        text: "Hi! I'm the Rainchem assistant. Ask me about engine oil, RadCool coolant, services, or your orders.",
      }]);
      client.get("/api/chat/suggestions").then((res) => setSuggestions(res.data.suggestions));
    }
  }, [chatOpen, user, started]);

  useEffect(() => {
    if (bodyRef.current) bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
  }, [messages]);

  function handleLauncherClick() {
    if (!user) {
      requireLogin("login", "Please log in to chat with our AI assistant");
      return;
    }
    toggleChat();
  }

  async function ask(question) {
    setMessages((prev) => [...prev, { from: "user", text: question }]);
    try {
      const res = await client.post("/api/chat/ask", { question });
      setMessages((prev) => [
        ...prev,
        { from: "bot", text: res.data.answer, confidence: res.data.resolved ? res.data.confidence : null },
      ]);
    } catch {
      setMessages((prev) => [...prev, { from: "bot", text: "Sorry, something went wrong. Please try again." }]);
    }
  }

  function handleSend() {
    const question = input.trim();
    if (!question) return;
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
              <div key={i} className={`chat-msg ${m.from}`}>
                {m.text}
                {m.confidence != null && (
                  <div style={{ fontSize: 10, marginTop: 4, opacity: 0.7 }}>Match confidence: {m.confidence}%</div>
                )}
              </div>
            ))}
          </div>
          {suggestions.length > 0 && (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6, padding: "0 14px 10px" }}>
              {suggestions.map((s) => (
                <button
                  key={s.id}
                  onClick={() => ask(s.question)}
                  style={{ fontSize: 11, padding: "5px 9px", borderRadius: 20, border: "1px solid rgba(24,20,15,.15)", background: "#fff" }}
                >
                  {s.question}
                </button>
              ))}
            </div>
          )}
          <div className="chat-input">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
              placeholder="Ask about oil, coolant, orders..."
            />
            <button onClick={handleSend}>
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
