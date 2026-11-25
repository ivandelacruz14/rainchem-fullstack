import { useCallback, useEffect, useRef } from "react";
import client from "../api/client";

const CHECK_EVERY_MS = 20000;

/**
 * Keeps the customer's orders current without a page refresh. It loads the list now, again every 20 seconds
 * while the tab is visible, and again when the tab becomes visible. When an order's status changes, onStatusChange
 * is called with the order and its old status. onLoad receives the list, or null if the request failed.
 */
export default function useLiveOrders({ onLoad, onStatusChange } = {}) {
  const seen = useRef(new Map());
  const started = useRef(false);
  const callbacks = useRef({ onLoad, onStatusChange });
  callbacks.current = { onLoad, onStatusChange };

  const reload = useCallback(() => {
    client.get("/api/orders")
      .then((res) => {
        const list = res.data.orders || [];
        if (started.current) {
          list.forEach((o) => {
            const before = seen.current.get(o.id);
            if (before && before !== o.status) callbacks.current.onStatusChange?.(o, before);
          });
        }
        list.forEach((o) => seen.current.set(o.id, o.status));
        started.current = true;
        callbacks.current.onLoad?.(list);
      })
      .catch(() => callbacks.current.onLoad?.(null));
  }, []);

  useEffect(() => {
    reload();
    const timer = setInterval(() => {
      if (document.visibilityState !== "hidden") reload();
    }, CHECK_EVERY_MS);
    const onVisible = () => {
      if (document.visibilityState === "visible") reload();
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [reload]);

  return reload;
}
