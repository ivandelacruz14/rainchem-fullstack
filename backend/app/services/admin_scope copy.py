from app.extensions import db
from app.models import Product


def scope_product_ids(admin):
    """None means "everything". Only a distributor is limited to their own products."""
    if not admin.is_scoped:
        return None
    return [pid for (pid,) in db.session.query(Product.id).filter(Product.owner_admin_id == admin.id).all()]
