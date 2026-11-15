import { useRef, useState } from "react";

/**
 * Runs an async action once at a time. A second click while the first request is still running is ignored,
 * so a double tap cannot place the same order, pay twice, or send the same code twice.
 */
export default function useAction() {
  const [busy, setBusy] = useState(false);
  const running = useRef(false);

  async function run(action) {
    if (running.current) return undefined;
    running.current = true;
    setBusy(true);
    try {
      return await action();
    } finally {
      running.current = false;
      setBusy(false);
    }
  }

  return { busy, run };
}
