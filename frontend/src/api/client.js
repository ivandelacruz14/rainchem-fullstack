import axios from "axios";

const API_URL = (import.meta.env.VITE_API_URL || "http://localhost:5000").replace(/\/+$/, "");

export const SESSION_EXPIRED_EVENT = "rainchem:session-expired";

const client = axios.create({ baseURL: API_URL });

// Admin pages, and any call to an /api/admin route, use the admin login.
function isAdminRequest(config) {
  return window.location.pathname.startsWith("/admin") || (config?.url || "").startsWith("/api/admin");
}

function readToken(key) {
  return localStorage.getItem(key) || sessionStorage.getItem(key);
}

// Storefront pages only ever send the customer token, admin pages only the admin token.
client.interceptors.request.use((config) => {
  const token = isAdminRequest(config) ? readToken("rainchem_admin_token") : readToken("rainchem_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// An expired or revoked login should sign the person out instead of leaving broken screens.
client.interceptors.response.use(
  (response) => response,
  (error) => {
    const sentToken = Boolean(error.config?.headers?.Authorization);
    const isLoginCall = /\/login$|\/google$/.test(error.config?.url || "");
    if (error.response?.status === 401 && sentToken && !isLoginCall) {
      window.dispatchEvent(new CustomEvent(SESSION_EXPIRED_EVENT, { detail: { scope: isAdminRequest(error.config) ? "admin" : "user" } }));
    }
    return Promise.reject(error);
  },
);

export default client;
