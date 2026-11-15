import { useEffect } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useAdminAuth } from "../context/AdminAuthContext";
import { useUI } from "../context/UIContext";

export function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  const { requireLogin } = useUI();
  const location = useLocation();
  const blocked = !loading && !user;

  useEffect(() => {
    if (blocked) requireLogin("login", "Please log in to continue", location.pathname + location.search);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [blocked]);

  if (loading) return null;
  if (!user) return <Navigate to="/" replace />;
  return children;
}

export function AdminProtectedRoute({ children }) {
  const { admin, loading } = useAdminAuth();
  if (loading) return null;
  if (!admin) return <Navigate to="/admin/login" replace />;
  return children;
}

export function PermissionRoute({ permission, headOnly = false, children }) {
  const { admin, can } = useAdminAuth();
  const allowed = headOnly ? admin?.isHead : can(permission);
  if (allowed) return children;
  return (
    <div className="admin-panel">
      <h3>No access</h3>
      <p style={{ color: "var(--soft)" }}>Your account does not have permission to open this page. Ask the Head Admin if you need it.</p>
    </div>
  );
}
