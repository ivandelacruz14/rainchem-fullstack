import { useCallback, useEffect, useRef, useState } from "react";
import client from "../api/client";

export const LIVE_POLL_MS = 3000;

function merge(current, incoming) {
  const byId = new Map(current.map((m) => [m.id, m]));
  incoming.forEach((m) => byId.set(m.id, m));
  return [...byId.values()].sort((a, b) => a.id - b.id);
}

/**
 * The customer's side of the live chat. While `active` it asks the server every few seconds for
 * messages that are new or changed (status ticks, deletions), so no WebSocket server is needed.
 */
export default function useLiveChat(active) {
  const [state, setState] = useState({ loading: true, error: "", conversation: null, messages: [], topics: [], maxUploadMb: 3 });
  const cursor = useRef(null);
  const busy = useRef(false);

  const apply = useCallback((data, replace) => {
    const newest = data.messages.reduce((max, m) => (!max || m.updatedAt > max ? m.updatedAt : max), cursor.current);
    cursor.current = newest;
    setState((prev) => ({
      loading: false, error: "",
      conversation: data.conversation || prev.conversation,
      topics: data.topics?.length ? data.topics : prev.topics,
      maxUploadMb: data.maxUploadMb || prev.maxUploadMb,
      messages: replace ? data.messages : merge(prev.messages, data.messages),
    }));
  }, []);

  const poll = useCallback(async (initial = false) => {
    if (busy.current) return;
    busy.current = true;
    try {
      const res = await client.get("/api/live-chat", { params: initial || !cursor.current ? {} : { since: cursor.current } });
      apply(res.data, initial || !cursor.current);
    } catch (err) {
      if (initial) setState((prev) => ({ ...prev, loading: false, error: err.response?.data?.error || "Live chat could not be loaded." }));
    } finally {
      busy.current = false;
    }
  }, [apply]);

  useEffect(() => {
    if (!active) return undefined;
    poll(true);
    const timer = setInterval(() => {
      if (document.visibilityState !== "hidden") poll(false);
    }, LIVE_POLL_MS);
    return () => clearInterval(timer);
  }, [active, poll]);

  const send = useCallback(async (body, extra = {}, file = null) => {
    let payload = { body, ...extra };
    if (file) {
      payload = new FormData();
      payload.append("image", file);
      if (body) payload.append("body", body);
      Object.entries(extra).forEach(([key, value]) => { if (value !== undefined && value !== null && value !== "") payload.append(key, value); });
    }
    const res = await client.post("/api/live-chat/messages", payload);
    setState((prev) => ({ ...prev, conversation: res.data.conversation, messages: merge(prev.messages, [res.data.message]) }));
    return res.data;
  }, []);

  const remove = useCallback(async (message) => {
    const res = await client.delete(`/api/live-chat/messages/${message.id}`);
    setState((prev) => ({ ...prev, messages: merge(prev.messages, [res.data.message]) }));
  }, []);

  const markRead = useCallback(async () => {
    try {
      await client.post("/api/live-chat/read");
    } catch { /* read marks are retried on the next poll */ }
  }, []);

  const add = useCallback((message, conversation) => {
    setState((prev) => ({ ...prev, conversation: conversation || prev.conversation, messages: merge(prev.messages, [message]) }));
  }, []);

  return { ...state, send, remove, markRead, add, refresh: () => poll(false) };
}
