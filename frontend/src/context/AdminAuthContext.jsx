import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import client, { SESSION_EXPIRED_EVENT } from "../api/client";

const AdminAuthContext = createContext(null);
export const ADMIN_NOTICE_KEY = "rainchem_admin_notice";
export const ADMIN_TOKEN_KEY = "rainchem_admin_token";
const DEFAULT_IDLE_MINUTES = 10;
const WARNING_SECONDS = 60;
const ACTIVITY_EVENTS = ["mousemove", "mousedown", "keydown", "pointerdown", "touchstart", "scroll"];
const HEARTBEAT_MS = 60 * 1000;

/**
 * Admin sign-in state, the idle timeout, and the warning shown before it happens.
 * The server is the authority: it ends a session that is idle too long. This screen mirrors that so the
 * person is warned and taken to the login page without waiting for a failed request.
 */
export function AdminAuthProvider({ children }) {
  const [admin, setAdmin] = useState(null);
  const [loading, setLoading] = useState(true);
  const [idleMinutes, setIdleMinutes] = useState(DEFAULT_IDLE_MINUTES);
  const [warningSeconds, setWarningSeconds] = useState(null);
  const extendRef = useRef(null);

  const clearSession = useCallback((notice) => {
    sessionStorage.removeItem(ADMIN_TOKEN_KEY);
    localStorage.removeItem(ADMIN_TOKEN_KEY); // older versions kept the admin login here
    if (notice) sessionStorage.setItem(ADMIN_NOTICE_KEY, notice);
    setWarningSeconds(null);
    setAdmin(null);
  }, []);

  useEffect(() => {
    const token = sessionStorage.getItem(ADMIN_TOKEN_KEY);
    localStorage.removeItem(ADMIN_TOKEN_KEY);
    if (!token) {
      setLoading(false);
      return;
    }
    client.get("/api/admin/auth/me")
      .then((res) => {
        setAdmin(res.data.admin);
        if (res.data.idleMinutes) setIdleMinutes(res.data.idleMinutes);
      })
      .catch((err) => {
        if (err.response?.status === 401 || err.response?.status === 403) {
          clearSession(err.response?.data?.error || "");
        }
      })
      .finally(() => setLoading(false));
  }, [clearSession]);

  // Sign out on purpose: tell the server, then clear this browser.
  const signOut = useCallback(async () => {
    try {
      await client.post("/api/admin/auth/logout");
    } catch {
      /* the token may already be gone; clearing this browser is what matters */
    }
    clearSession();
  }, [clearSession]);

  useEffect(() => {
    function onExpired(event) {
      if (event.detail?.scope === "admin") clearSession(event.detail.message);
    }
    window.addEventListener(SESSION_EXPIRED_EVENT, onExpired);
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, onExpired);
  }, [clearSession]);

  // Idle timer: counts from the last activity in this tab, shows a warning in the last minute, then signs out.
  useEffect(() => {
    if (!admin) return undefined;
    const idleMs = idleMinutes * 60 * 1000;
    let lastActivity = Date.now();
    let activeSinceHeartbeat = false;

    const heartbeat = () => {
      activeSinceHeartbeat = false;
      client.post("/api/admin/auth/heartbeat").catch(() => {});
    };
    const onActivity = () => {
      lastActivity = Date.now();
      activeSinceHeartbeat = true;
    };
    const tick = setInterval(() => {
      const idle = Date.now() - lastActivity;
      if (idle >= idleMs) {
        clearSession(`You were signed out because there was no activity for ${idleMinutes} minutes. Please sign in again.`);
        return;
      }
      const left = Math.ceil((idleMs - idle) / 1000);
      setWarningSeconds(left <= WARNING_SECONDS ? left : null);
    }, 1000);
    const keepAlive = setInterval(() => { if (activeSinceHeartbeat) heartbeat(); }, HEARTBEAT_MS);

    ACTIVITY_EVENTS.forEach((name) => window.addEventListener(name, onActivity, { passive: true }));
    extendRef.current = () => {
      lastActivity = Date.now();
      heartbeat();
      setWarningSeconds(null);
    };
    return () => {
      clearInterval(tick);
      clearInterval(keepAlive);
      ACTIVITY_EVENTS.forEach((name) => window.removeEventListener(name, onActivity));
      extendRef.current = null;
    };
  }, [admin, idleMinutes, clearSession]);

  function loginWithToken(token, adminData, minutes) {
    sessionStorage.setItem(ADMIN_TOKEN_KEY, token);
    sessionStorage.removeItem(ADMIN_NOTICE_KEY);
    if (minutes) setIdleMinutes(minutes);
    setAdmin(adminData);
  }

  function can(permission) {
    return Boolean(admin && (admin.isHead || admin.permissions?.includes(permission)));
  }

  return (
    <AdminAuthContext.Provider
      value={{
        admin, setAdmin, loading, loginWithToken, logout: signOut, can,
        warningSeconds, extendSession: () => extendRef.current?.(), idleMinutes,
      }}
    >
      {children}
    </AdminAuthContext.Provider>
  );
}

export function useAdminAuth() {
  return useContext(AdminAuthContext);
}
