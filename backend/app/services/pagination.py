"""Server-side paging: the database returns only one page, never the whole table.
Paging is opt-in (a page number must be asked for), so screens that load everything keep working."""
from flask import request

DEFAULT_PER_PAGE = 10
MAX_PER_PAGE = 100


def wants_page():
    return request.args.get("page") is not None


def page_args():
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (TypeError, ValueError):
        page = 1
    try:
        per_page = int(request.args.get("perPage", DEFAULT_PER_PAGE))
    except (TypeError, ValueError):
        per_page = DEFAULT_PER_PAGE
    return page, min(max(1, per_page), MAX_PER_PAGE)


def page_slice(query, page, per_page):
    total = query.order_by(None).count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    pages = max(1, -(-total // per_page))
    return items, {"page": page, "perPage": per_page, "total": total, "pages": pages}
