import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";

const SITE_KEY = import.meta.env.VITE_TURNSTILE_SITE_KEY || "";
const SCRIPT_URL = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";
let scriptPromise = null;

export function captchaEnabled() {
  return Boolean(SITE_KEY);
}

function loadScript() {
  if (window.turnstile) return Promise.resolve();
  if (!scriptPromise) {
    scriptPromise = new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = SCRIPT_URL;
      script.async = true;
      script.onload = () => resolve();
      script.onerror = () => {
        scriptPromise = null;
        reject(new Error("The security check could not load."));
      };
      document.head.appendChild(script);
    });
  }
  return scriptPromise;
}

/** Cloudflare Turnstile ("I'm not a robot"). It gives a one-time token that the server verifies. */
const Turnstile = forwardRef(function Turnstile({ onToken }, ref) {
  const box = useRef(null);
  const widgetId = useRef(null);
  const callback = useRef(onToken);
  callback.current = onToken;

  useEffect(() => {
    if (!SITE_KEY) return undefined;
    let cancelled = false;
    loadScript()
      .then(() => {
        if (cancelled || !box.current || !window.turnstile) return;
        widgetId.current = window.turnstile.render(box.current, {
          sitekey: SITE_KEY,
          callback: (token) => callback.current?.(token),
          "expired-callback": () => callback.current?.(""),
          "error-callback": () => callback.current?.(""),
        });
      })
      .catch(() => callback.current?.(""));
    return () => {
      cancelled = true;
      if (widgetId.current !== null && window.turnstile) window.turnstile.remove(widgetId.current);
      widgetId.current = null;
    };
  }, []);

  useImperativeHandle(ref, () => ({
    reset() {
      // A token works only once, so after every failed attempt the widget starts a new check.
      if (widgetId.current !== null && window.turnstile) window.turnstile.reset(widgetId.current);
      callback.current?.("");
    },
  }), []);

  if (!SITE_KEY) return null;
  return <div ref={box} className="turnstile-box" />;
});

export default Turnstile;
