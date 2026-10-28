export default function ConfirmDialog({ title, message, confirmLabel = "Delete", danger = true, busy = false, onConfirm, onCancel }) {
  return (
    <div className="overlay" onClick={onCancel} role="presentation">
      <div className="modal confirm-dialog" role="alertdialog" aria-modal="true" aria-label={title} onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h3 style={{ margin: 0, fontSize: 18 }}>{title}</h3>
        </div>
        <div className="modal-body">
          <p style={{ marginTop: 0 }}>{message}</p>
          <div className="form-actions">
            <button type="button" className="btn btn-outline" onClick={onCancel} disabled={busy}>Cancel</button>
            <button type="button" className={`btn ${danger ? "btn-danger" : "btn-primary"}`} onClick={onConfirm} disabled={busy}>
              {busy ? "Please wait..." : confirmLabel}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
