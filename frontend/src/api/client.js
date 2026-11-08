import axios from "axios";

const API_URL = (import.meta.env.VITE_API_URL || "http://localhost:5000").replace(/\/+$/, "");

export const SESSION_EXPIRED_EVENT = "rainchem:session-expired";
export const ADMIN_TOKEN_KEY = "rainchem_admin_token";

const client = axios.create({ baseURL: API_URL });

// Admin pages, and any call to an /api/admin route, use the admin login.
function isAdminRequest(config) {
  return window.location.pathname.startsWith("/admin") || (config?.url || "").startsWith("/api/admin");
}

function customerToken() {
  return localStorage.getItem("rainchem_token") || sessionStorage.getItem("rainchem_token");
}

// The admin login lives in sessionStorage only: closing the tab or the browser removes it.
client.interceptors.request.use((config) => {
  const token = isAdminRequest(config) ? sessionStorage.getItem(ADMIN_TOKEN_KEY) : customerToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// An expired, idle or revoked login signs the person out, and the server's reason is passed along.
client.interceptors.response.use(
  (response) => response,
  (error) => {
    const sentToken = Boolean(error.config?.headers?.Authorization);
    const url = error.config?.url || "";
    const isLoginCall = /\/login(\/verify)?$|\/google$/.test(url);
    if (error.response?.status === 401 && sentToken && !isLoginCall) {
      window.dispatchEvent(new CustomEvent(SESSION_EXPIRED_EVENT, {
        detail: { scope: isAdminRequest(error.config) ? "admin" : "user", message: error.response?.data?.error || "" },
      }));
    }
    return Promise.reject(error);
  },
);

export default client;
