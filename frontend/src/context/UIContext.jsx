import { createContext, useContext, useState } from "react";
import { useToast } from "./ToastContext";

const UIContext = createContext(null);

const CLOSED = { open: false, mode: "login", returnTo: null };

export function UIProvider({ children }) {
  const [cartOpen, setCartOpen] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [authModal, setAuthModal] = useState(CLOSED);
  const showToast = useToast();

  // returnTo: a path to open after a successful login (for example the product the visitor was viewing).
  function requireLogin(mode = "login", message = null, returnTo = null) {
    if (message) showToast(message, "error");
    setAuthModal({ open: true, mode, returnTo });
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
