import { useEffect, useRef } from "react";

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;

/**
 * Renders Google's own "Sign in with Google" button. Requires
 * VITE_GOOGLE_CLIENT_ID to be set to an OAuth Client ID created in the
 * Google Cloud Console. Without it, this component shows a disabled
 * placeholder instead of a broken button.
 */
export default function GoogleSignInButton({ onCredential }) {
  const buttonRef = useRef(null);

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID) return;

    function renderButton() {
      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: (response) => onCredential(response.credential),
      });
      window.google.accounts.id.renderButton(buttonRef.current, {
        theme: "outline", size: "large", width: "100%",
      });
    }

    if (window.google?.accounts?.id) {
      renderButton();
      return;
    }

    const script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.onload = renderButton;
    document.body.appendChild(script);
  }, [onCredential]);

  if (!GOOGLE_CLIENT_ID) {
    return (
      <button className="btn btn-outline btn-block" disabled title="Set VITE_GOOGLE_CLIENT_ID to enable">
        Sign in with Google (not configured)
      </button>
    );
  }

  return <div ref={buttonRef} style={{ display: "flex", justifyContent: "center" }} />;
}
