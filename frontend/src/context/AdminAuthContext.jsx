import { createContext, useContext, useState, useEffect, useCallback } from "react";
import client, { SESSION_EXPIRED_EVENT } from "../api/client";

const AdminAuthContext = createContext(null);

export function AdminAuthProvider({ children }) {
  const [admin, setAdmin] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("rainchem_admin_token");
    if (!token) {
      setLoading(false);
      return;
    }
    client
      .get("/api/admin/auth/me")
      .then((res) => setAdmin(res.data.admin))
      .catch((err) => {
        if (err.response?.status === 401 || err.response?.status === 403) {
          localStorage.removeItem("rainchem_admin_token");
        }
      })
      .finally(() => setLoading(false));
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("rainchem_admin_token");
    setAdmin(null);
  }, []);

  useEffect(() => {
    function onExpired(event) {
      if (event.detail?.scope === "admin") logout();
    }
    window.addEventListener(SESSION_EXPIRED_EVENT, onExpired);
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, onExpired);
  }, [logout]);

  function loginWithToken(token, adminData) {
    localStorage.setItem("rainchem_admin_token", token);
    setAdmin(adminData);
  }

  function can(permission) {
    return Boolean(admin && (admin.isHead || admin.permissions?.includes(permission)));
  }

  return (
    <AdminAuthContext.Provider value={{ admin, setAdmin, loading, loginWithToken, logout, can }}>
      {children}
    </AdminAuthContext.Provider>
  );
}

export function useAdminAuth() {
  return useContext(AdminAuthContext);
}
