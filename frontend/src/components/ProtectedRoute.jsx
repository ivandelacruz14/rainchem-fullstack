import { useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useAdminAuth } from "../context/AdminAuthContext";
import { Navigate } from "react-router-dom";
import { useUI } from "../context/UIContext";

export function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  const { requireLogin } = useUI();
  const { pathname, search } = useLocation();
  if (loading) return null;
  if (!user) {
    return (
      <div className="container narrow-page">
        <div className="panel login-required">
          <h2>Please log in</h2>
          <p>You need an account to view this page.</p>
          <button type="button" className="btn btn-primary btn-block" onClick={() => requireLogin("login", null, pathname + search)}>Log In</button>
          <button type="button" className="btn btn-outline btn-block" onClick={() => requireLogin("register", null, pathname + search)}>Create Account</button>
        </div>
      </div>
    );
  }
  return children;
}

export function AdminProtectedRoute({ children }) {
  const { admin, loading } = useAdminAuth();
  if (loading) return null;
  if (!admin) return <Navigate to="/admin/login" replace />;
  return children;
}

export function AdminPermissionRoute({ permission, headOnly = false, children }) {
  const { admin, can } = useAdminAuth();
  const allowed = headOnly ? admin?.isHead : can(permission);
  if (!allowed) {
    return (
      <div className="alert alert-error">You do not have access to this section. Ask a Head Admin if you need it.</div>
    );
  }
  return children;
}
