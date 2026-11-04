import { useRef } from "react";

/** The paperclip button. It opens the file picker (the camera on a phone) and hands the chosen file up. */
export function AttachButton({ onPick, disabled }) {
  const input = useRef(null);
  return (
    <>
      <button
        type="button" className="chat-attach" disabled={disabled} aria-label="Attach a photo" title="Attach a photo"
        onClick={() => input.current?.click()}
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="m21.4 11.1-9.2 9.2a6 6 0 0 1-8.5-8.5l9.2-9.2a4 4 0 0 1 5.7 5.7l-9.2 9.2a2 2 0 0 1-2.8-2.8l8.5-8.5" />
        </svg>
      </button>
      <input
        ref={input} type="file" accept="image/*" hidden data-testid="chat-photo-input" aria-label="Choose a photo"
        onChange={(e) => {
          const file = e.target.files?.[0];
          e.target.value = ""; // so choosing the same photo again still fires
          if (file) onPick(file);
        }}
      />
    </>
  );
}

/** The photo that is about to be sent, with a way to remove it. */
export function PhotoPreview({ photo, onRemove, disabled }) {
  if (!photo) return null;
  return (
    <div className="chat-photo-preview">
      <img src={photo} alt="Photo to send" />
      <button type="button" onClick={onRemove} disabled={disabled} aria-label="Remove photo" title="Remove photo">&times;</button>
    </div>
  );
}
