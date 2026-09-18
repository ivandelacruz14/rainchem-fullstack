import { createContext, useContext, useState } from "react";
import { useToast } from "./ToastContext";

const UIContext = createContext(null);

export function UIProvider({ children }) {
  const [cartOpen, setCartOpen] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [authModal, setAuthModal] = useState({ open: false, mode: "login" });
  const showToast = useToast();

  function requireLogin(mode = "login", message = null) {
    if (message) showToast(message, "error");
    setAuthModal({ open: true, mode });
  }

  function closeAuth() {
    setAuthModal({ open: false, mode: "login" });
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
