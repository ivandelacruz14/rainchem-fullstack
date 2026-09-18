import { createContext, useContext, useState, useEffect } from "react";
import client from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("rainchem_token");
    if (!token) {
      setLoading(false);
      return;
    }
    client
      .get("/api/auth/me")
      .then((res) => setUser(res.data.user))
      .catch(() => localStorage.removeItem("rainchem_token"))
      .finally(() => setLoading(false));
  }, []);

  function loginWithToken(token, userData) {
    localStorage.setItem("rainchem_token", token);
    setUser(userData);
  }

  function logout() {
    localStorage.removeItem("rainchem_token");
    setUser(null);
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
