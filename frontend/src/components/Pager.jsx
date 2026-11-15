/** Previous and Next buttons with the page number and the total. Shows nothing when everything fits on one page. */
export default function Pager({ page, pages, total, onChange }) {
  if (!total || pages <= 1) return null;
  return (
    <nav className="pager" aria-label="Pages">
      <span className="field-hint">Page {page} of {pages} · {total} records</span>
      <div className="row-actions">
        <button type="button" className="btn btn-outline btn-sm" disabled={page <= 1} onClick={() => onChange(page - 1)}>Previous</button>
        <button type="button" className="btn btn-outline btn-sm" disabled={page >= pages} onClick={() => onChange(page + 1)}>Next</button>
      </div>
    </nav>
  );
}
