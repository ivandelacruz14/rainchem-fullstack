import { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { useUI } from "../context/UIContext";
import client from "../api/client";
import AiChat from "./chat/AiChat";
import LiveChatPanel from "./chat/LiveChatPanel";

const UNREAD_POLL_MS = 15000;

export default function ChatWidget() {
  const { user } = useAuth();
  const { chatOpen, toggleChat, requireLogin, liveIntent } = useUI();
  const [tab, setTab] = useState("ai");
  const [liveUnread, setLiveUnread] = useState(0);

  // A request to talk to the admin (for example from Track My Order) opens the live tab.
  useEffect(() => {
    if (liveIntent) setTab("live");
  }, [liveIntent]);

  // Unread admin replies, for the badge on the button. Only while the live tab is not open.
  useEffect(() => {
    if (!user) {
      setLiveUnread(0);
      return undefined;
    }
    const check = () => {
      if (document.visibilityState === "hidden") return;
      client.get("/api/live-chat/unread").then((res) => setLiveUnread(res.data.unread)).catch(() => {});
    };
    if (chatOpen && tab === "live") {
      setLiveUnread(0);
      return undefined;
    }
    check();
    const timer = setInterval(check, UNREAD_POLL_MS);
    return () => clearInterval(timer);
  }, [user, chatOpen, tab]);

  function handleLauncherClick() {
    if (!user) {
      requireLogin("login", "Please log in to chat with our assistant");
      return;
    }
    toggleChat();
  }

  return (
    <>
      <button className="chat-launcher" onClick={handleLauncherClick} title="Chat">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
        </svg>
        {liveUnread > 0 && <span className="launcher-badge" aria-label={`${liveUnread} unread messages`}>{liveUnread}</span>}
      </button>

      {user && (
        <div className="chat-panel" hidden={!chatOpen}>
          <div className="chat-head">
            <h4>{tab === "ai" ? "Rainchem Assistant" : "Chat with our admin"}</h4>
            <p>{tab === "ai" ? "AI answers from our admin-verified knowledge base" : "Messages go to our team. Replies appear here."}</p>
            <div className="chat-tabs" role="tablist">
              <button type="button" role="tab" aria-selected={tab === "ai"} className={tab === "ai" ? "active" : ""} onClick={() => setTab("ai")}>AI Assistant</button>
              <button type="button" role="tab" aria-selected={tab === "live"} className={tab === "live" ? "active" : ""} onClick={() => setTab("live")}>
                Live Chat{liveUnread > 0 && tab !== "live" && <span className="tab-badge">{liveUnread}</span>}
              </button>
            </div>
          </div>
          <div className="chat-pane" hidden={tab !== "ai"}>
            <AiChat onOpenLive={() => setTab("live")} />
          </div>
          {chatOpen && tab === "live" && (
            <div className="chat-pane">
              <LiveChatPanel />
            </div>
          )}
        </div>
      )}
    </>
  );
}
