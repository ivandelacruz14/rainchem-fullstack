import { createContext, useContext, useState, useEffect } from "react";
import client from "../api/client";

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
      .catch(() => localStorage.removeItem("rainchem_admin_token"))
      .finally(() => setLoading(false));
  }, []);

  function loginWithToken(token, adminData) {
    localStorage.setItem("rainchem_admin_token", token);
    setAdmin(adminData);
  }

  function logout() {
    localStorage.removeItem("rainchem_admin_token");
    setAdmin(null);
  }

  return (
    <AdminAuthContext.Provider value={{ admin, loading, loginWithToken, logout }}>
      {children}
    </AdminAuthContext.Provider>
  );
}

export function useAdminAuth() {
  return useContext(AdminAuthContext);
}
