import { useEffect, useRef, useState } from "react";

const TYPES = ["image/jpeg", "image/png", "image/webp"];

/**
 * The message box shared by the customer and the admin screens: text, an image button, a preview with a
 * cancel option, and a clear busy state. `onSend({ body, file })` must throw to report an error.
 */
export default function Composer({ onSend, inputLabel, sendLabel = "Send", placeholder, maxMb = 3, multiline = false, disabled = false, error: outerError = "" }) {
  const [draft, setDraft] = useState("");
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);
  const picker = useRef(null);

  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);

  function choose(e) {
    const picked = e.target.files?.[0];
    e.target.value = "";
    if (!picked) return;
    if (!TYPES.includes(picked.type)) {
      setError("Choose a JPG, PNG or WEBP image.");
      return;
    }
    if (picked.size > maxMb * 1024 * 1024) {
      setError(`The image is too large. The limit is ${maxMb} MB.`);
      return;
    }
    setError("");
    setFile(picked);
    setPreview(URL.createObjectURL(picked));
  }

  function removeImage() {
    setFile(null);
    setPreview(null);
  }

  async function submit(e) {
    e?.preventDefault();
    const body = draft.trim();
    if ((!body && !file) || sending || disabled) return;
    setSending(true);
    setError("");
    try {
      await onSend({ body, file });
      setDraft("");
      removeImage();
    } catch (err) {
      setError(err.response?.data?.error || err.message || "Your message could not be sent. Please try again.");
    } finally {
      setSending(false);
    }
  }

  const shown = error || outerError;
  const Field = multiline ? "textarea" : "input";
  const fieldProps = multiline
    ? { rows: 2, onKeyDown: (e) => { if (e.key === "Enter" && !e.shiftKey) submit(e); } }
    : {};

  return (
    <form className="composer" onSubmit={submit}>
      {preview && (
        <div className="composer-preview">
          <img src={preview} alt="Image to send" />
          <button type="button" className="composer-remove" onClick={removeImage} aria-label="Remove image">&times;</button>
        </div>
      )}
      {shown && <div className="live-error" role="alert">{shown}</div>}
      {sending && file && <div className="composer-busy" role="status"><span className="spinner" /> Uploading image...</div>}
      <div className="composer-row">
        <input ref={picker} type="file" accept="image/jpeg,image/png,image/webp" hidden onChange={choose} aria-label="Choose an image" />
        <button type="button" className="composer-attach" aria-label="Attach image" title="Attach image" disabled={sending || disabled} onClick={() => picker.current?.click()}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="4" width="18" height="16" rx="2" /><circle cx="9" cy="10" r="1.6" /><path d="M21 16l-5-5-8 8" /></svg>
        </button>
        <Field
          value={draft} maxLength={2000} onChange={(e) => setDraft(e.target.value)} aria-label={inputLabel}
          placeholder={file ? "Add a caption (optional)" : placeholder} disabled={disabled} {...fieldProps}
        />
        <button type="submit" className="composer-send" disabled={sending || disabled || (!draft.trim() && !file)} aria-label={sendLabel}>
          {multiline ? (sending ? "Sending..." : sendLabel) : (
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.4"><path d="M22 2 11 13M22 2l-7 20-4-9-9-4 20-7z" /></svg>
          )}
        </button>
      </div>
    </form>
  );
}
