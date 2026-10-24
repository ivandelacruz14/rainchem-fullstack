import axios from "axios";

const API_URL = (import.meta.env.VITE_API_URL || "http://localhost:5000").replace(/\/+$/, "");

export const USER_TOKEN_KEY = "rainchem_token";
export const ADMIN_TOKEN_KEY = "rainchem_admin_token";
export const UNAUTHORIZED_EVENT = "rainchem:unauthorized";

const client = axios.create({ baseURL: API_URL });

export function readToken(key) {
  return localStorage.getItem(key) || sessionStorage.getItem(key);
}

function isAdminRequest(config) {
  const path = (config.url || "").replace(API_URL, "");
  return path.startsWith("/api/admin") || window.location.pathname.startsWith("/admin");
}

client.interceptors.request.use((config) => {
  // Customer and admin sessions are kept apart: each only ever sends its own token.
  const token = readToken(isAdminRequest(config) ? ADMIN_TOKEN_KEY : USER_TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

client.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    const url = error.config?.url || "";
    const isLoginAttempt = /\/(login|google|verify-email)$/.test(url);
    if (status === 401 && !isLoginAttempt && !isAdminRequest(error.config || {})) {
      window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
    }
    return Promise.reject(error);
  },
);

export default client;
