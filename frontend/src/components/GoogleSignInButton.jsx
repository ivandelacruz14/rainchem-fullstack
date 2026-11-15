import { useEffect, useRef } from "react";

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;

// Google's script is loaded one time for the whole site.
let scriptPromise = null;
function loadGoogleScript() {
  if (window.google?.accounts?.id) return Promise.resolve();
  if (!scriptPromise) {
    scriptPromise = new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = "https://accounts.google.com/gsi/client";
      script.async = true;
      script.onload = resolve;
      script.onerror = () => {
        scriptPromise = null;
        reject(new Error("Could not load Google sign-in"));
      };
      document.body.appendChild(script);
    });
  }
  return scriptPromise;
}

/**
 * Renders Google's own "Sign in with Google" button. Requires
 * VITE_GOOGLE_CLIENT_ID to be set to an OAuth Client ID created in the
 * Google Cloud Console. Without it, this component shows a disabled
 * placeholder instead of a broken button.
 */
export default function GoogleSignInButton({ onCredential }) {
  const buttonRef = useRef(null);
  const callbackRef = useRef(onCredential);

  // The form around this button re-renders on every key press. Keeping the
  // latest callback in a ref lets the button be drawn only once.
  useEffect(() => {
    callbackRef.current = onCredential;
  });

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID) return undefined;
    let cancelled = false;

    loadGoogleScript()
      .then(() => {
        if (cancelled || !buttonRef.current) return;
        window.google.accounts.id.initialize({
          client_id: GOOGLE_CLIENT_ID,
          callback: (response) => callbackRef.current(response.credential),
        });
        // Google needs the width in pixels (200 to 400), not "100%".
        const width = Math.min(Math.max(buttonRef.current.offsetWidth || 320, 200), 400);
        window.google.accounts.id.renderButton(buttonRef.current, { theme: "outline", size: "large", width });
      })
      .catch(() => {});

    return () => { cancelled = true; };
  }, []);

  if (!GOOGLE_CLIENT_ID) {
    return (
      <button className="btn btn-outline btn-block" disabled title="Set VITE_GOOGLE_CLIENT_ID to enable">
        Sign in with Google (not configured)
      </button>
    );
  }

  return <div ref={buttonRef} style={{ display: "flex", justifyContent: "center" }} />;
}
