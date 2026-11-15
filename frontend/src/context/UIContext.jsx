import { createContext, useContext, useState } from "react";
import { useToast } from "./ToastContext";

const UIContext = createContext(null);

const CLOSED = { open: false, mode: "login", returnTo: null };

export function UIProvider({ children }) {
  const [cartOpen, setCartOpen] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [authModal, setAuthModal] = useState(CLOSED);
  // What the customer wants to talk to the admin about, passed to the live chat when it opens.
  const [liveIntent, setLiveIntent] = useState(null);
  const showToast = useToast();

  // returnTo: a path to open after a successful login (for example the product the visitor was viewing).
  function requireLogin(mode = "login", message = null, returnTo = null) {
    if (message) showToast(message, "error");
    setAuthModal({ open: true, mode, returnTo });
  }

  function openLiveChat(intent = {}) {
    setLiveIntent({ ...intent, at: Date.now() });
    setChatOpen(true);
  }

  function clearLiveIntent() {
    setLiveIntent(null);
  }

  function closeAuth() {
    setAuthModal(CLOSED);
  }

  function switchAuthMode(mode) {
    setAuthModal((prev) => ({ ...prev, open: true, mode }));
  }

  return (
    <UIContext.Provider
      value={{
        cartOpen, openCart: () => setCartOpen(true), closeCart: () => setCartOpen(false),
        chatOpen, toggleChat: () => setChatOpen((v) => !v),
        liveIntent, openLiveChat, clearLiveIntent,
        authModal, requireLogin, closeAuth, switchAuthMode,
      }}
    >
      {children}
    </UIContext.Provider>
  );
}

export function useUI() {
  return useContext(UIContext);
}
