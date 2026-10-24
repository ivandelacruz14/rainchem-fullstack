import { createContext, useContext, useState } from "react";
import { useToast } from "./ToastContext";

const UIContext = createContext(null);

const CLOSED_AUTH = { open: false, mode: "login", returnTo: null };

export function UIProvider({ children }) {
  const [cartOpen, setCartOpen] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [authModal, setAuthModal] = useState(CLOSED_AUTH);
  const showToast = useToast();

  // returnTo is a path (with query) to come back to after a successful login.
  function requireLogin(mode = "login", message = null, returnTo = null) {
    if (message) showToast(message, "error");
    setAuthModal({ open: true, mode, returnTo });
  }

  function closeAuth() {
    setAuthModal(CLOSED_AUTH);
  }

  return (
    <UIContext.Provider
      value={{
        cartOpen, openCart: () => setCartOpen(true), closeCart: () => setCartOpen(false),
        chatOpen, toggleChat: () => setChatOpen((v) => !v),
        authModal, requireLogin, closeAuth, setAuthModal,
      }}
    >
      {children}
    </UIContext.Provider>
  );
}

export function useUI() {
  return useContext(UIContext);
}
