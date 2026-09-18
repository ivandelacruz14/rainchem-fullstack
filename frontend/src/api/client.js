import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:5000";

const client = axios.create({ baseURL: API_URL });

client.interceptors.request.use((config) => {
  const userToken = localStorage.getItem("rainchem_token");
  const adminToken = localStorage.getItem("rainchem_admin_token");
  const token = config.url?.startsWith("/api/admin") ? adminToken : userToken;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default client;
