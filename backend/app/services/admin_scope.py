from app.extensions import db
from app.models import Product


def scope_product_ids(admin):
    """None means "everything" (Head Admin). A distributor only sees their own products."""
    if admin.is_head:
        return None
    return [pid for (pid,) in db.session.query(Product.id).filter(Product.owner_admin_id == admin.id).all()]
