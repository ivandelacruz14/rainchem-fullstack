import { useEffect, useState } from "react";
import client from "../../api/client";

export function isoDay(date) {
  const offset = date.getTimezoneOffset() * 60000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 10);
}

export function presetRange(key) {
  const end = new Date();
  const start = new Date();
  if (key === "7d") start.setDate(end.getDate() - 6);
  else if (key === "30d") start.setDate(end.getDate() - 29);
  else if (key === "month") start.setDate(1);
  else if (key === "90d") start.setDate(end.getDate() - 89);
  return { start: isoDay(start), end: isoDay(end) };
}

export default function useSalesReport(filters) {
  const [state, setState] = useState({ loading: true, error: "", data: null });

  useEffect(() => {
    let cancelled = false;
    setState((prev) => ({ ...prev, loading: true, error: "" }));
    client.get("/api/admin/analytics/report", { params: filters })
      .then((res) => { if (!cancelled) setState({ loading: false, error: "", data: res.data }); })
      .catch((err) => {
        if (!cancelled) setState({ loading: false, error: err.response?.data?.error || "The report could not be loaded.", data: null });
      });
    return () => { cancelled = true; };
  }, [filters.start, filters.end, filters.granularity]);

  return state;
}
