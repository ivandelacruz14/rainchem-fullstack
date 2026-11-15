import { useEffect, useState } from "react";
import client from "../../api/client";

const cache = new Map(); // address -> object URL, so a polled thread does not download an image again

/** An image that lives behind a login. It is fetched with the person's own token and shown from memory,
 *  because a plain <img src> cannot send the token (and the image is never at a public address). */
export default function AuthImage({ src, alt, className, onOpen }) {
  const [state, setState] = useState({ url: cache.get(src) || null, error: false });

  useEffect(() => {
    if (cache.has(src)) {
      setState({ url: cache.get(src), error: false });
      return undefined;
    }
    let cancelled = false;
    setState({ url: null, error: false });
    client.get(src, { responseType: "blob" })
      .then((res) => {
        const url = URL.createObjectURL(res.data);
        cache.set(src, url);
        if (!cancelled) setState({ url, error: false });
      })
      .catch(() => { if (!cancelled) setState({ url: null, error: true }); });
    return () => { cancelled = true; };
  }, [src]);

  if (state.error) return <span className="img-missing">Image unavailable</span>;
  if (!state.url) return <span className="img-loading" role="status" aria-label="Loading image" />;
  return (
    <img
      src={state.url} alt={alt} className={className} onClick={onOpen ? () => onOpen(state.url) : undefined}
      style={onOpen ? { cursor: "zoom-in" } : undefined}
    />
  );
}
