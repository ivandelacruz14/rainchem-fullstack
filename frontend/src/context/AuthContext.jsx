import { createContext, useContext, useState, useEffect, useCallback } from "react";
import client, { SESSION_EXPIRED_EVENT } from "../api/client";
import { useToast } from "./ToastContext";

const AuthContext = createContext(null);

function clearStoredToken() {
  localStorage.removeItem("rainchem_token");
  sessionStorage.removeItem("rainchem_token");
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const showToast = useToast();

  useEffect(() => {
    const token = localStorage.getItem("rainchem_token") || sessionStorage.getItem("rainchem_token");
    if (!token) {
      setLoading(false);
      return;
    }
    client
      .get("/api/auth/me")
      .then((res) => setUser(res.data.user))
      .catch((err) => {
        // Only drop the login when the server says it is invalid, not on a network blip.
        if (err.response?.status === 401 || err.response?.status === 403) clearStoredToken();
      })
      .finally(() => setLoading(false));
  }, []);

  const logout = useCallback(() => {
    clearStoredToken();
    setUser(null);
  }, []);

  useEffect(() => {
    function onExpired(event) {
      if (event.detail?.scope !== "user") return;
      clearStoredToken();
      setUser((current) => {
        if (current) showToast("Your session has ended. Please log in again.", "error");
        return null;
      });
    }
    window.addEventListener(SESSION_EXPIRED_EVENT, onExpired);
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, onExpired);
  }, [showToast]);

  function loginWithToken(token, userData, remember = true) {
    if (remember) {
      localStorage.setItem("rainchem_token", token);
      sessionStorage.removeItem("rainchem_token");
    } else {
      sessionStorage.setItem("rainchem_token", token);
      localStorage.removeItem("rainchem_token");
    }
    setUser(userData);
  }

  return (
    <AuthContext.Provider value={{ user, setUser, loading, loginWithToken, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
