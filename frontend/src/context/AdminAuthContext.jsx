import { createContext, useContext, useState, useEffect } from "react";
import client, { ADMIN_TOKEN_KEY } from "../api/client";

const AdminAuthContext = createContext(null);

export function AdminAuthProvider({ children }) {
  const [admin, setAdmin] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!localStorage.getItem(ADMIN_TOKEN_KEY)) {
      setLoading(false);
      return;
    }
    client
      .get("/api/admin/auth/me")
      .then((res) => setAdmin(res.data.admin))
      .catch(() => localStorage.removeItem(ADMIN_TOKEN_KEY))
      .finally(() => setLoading(false));
  }, []);

  function loginWithToken(token, adminData) {
    localStorage.setItem(ADMIN_TOKEN_KEY, token);
    setAdmin(adminData);
  }

  function logout() {
    localStorage.removeItem(ADMIN_TOKEN_KEY);
    setAdmin(null);
  }

  // Mirrors the backend rule; the backend still enforces it on every request.
  function can(permission) {
    if (!admin) return false;
    return admin.isHead || (admin.permissions || []).includes(permission);
  }

  return (
    <AdminAuthContext.Provider value={{ admin, loading, loginWithToken, logout, can }}>
      {children}
    </AdminAuthContext.Provider>
  );
}

export function useAdminAuth() {
  return useContext(AdminAuthContext);
}
