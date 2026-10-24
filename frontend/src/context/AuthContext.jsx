import { createContext, useContext, useState, useEffect, useCallback } from "react";
import client, { USER_TOKEN_KEY, UNAUTHORIZED_EVENT, readToken } from "../api/client";

const AuthContext = createContext(null);

function clearStoredToken() {
  localStorage.removeItem(USER_TOKEN_KEY);
  sessionStorage.removeItem(USER_TOKEN_KEY);
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!readToken(USER_TOKEN_KEY)) {
      setLoading(false);
      return;
    }
    client
      .get("/api/auth/me")
      .then((res) => setUser(res.data.user))
      .catch(clearStoredToken)
      .finally(() => setLoading(false));
  }, []);

  const logout = useCallback(() => {
    clearStoredToken();
    setUser(null);
  }, []);

  // An expired or revoked token reported by the backend ends the session here too.
  useEffect(() => {
    window.addEventListener(UNAUTHORIZED_EVENT, logout);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, logout);
  }, [logout]);

  function loginWithToken(token, userData, remember = true) {
    clearStoredToken();
    (remember ? localStorage : sessionStorage).setItem(USER_TOKEN_KEY, token);
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
