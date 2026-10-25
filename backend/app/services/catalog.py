from sqlalchemy import func

from app.extensions import db
from app.models import Order, Product, ProductReview


def review_stats(product_ids=None):
    """{product_id: (average, count)} computed from real reviews of delivered orders."""
    query = (
        db.session.query(
            ProductReview.product_id,
            func.avg(ProductReview.rating),
            func.count(ProductReview.id),
        )
        .join(Order, Order.id == ProductReview.order_id)
        .filter(Order.status == "delivered")
        .group_by(ProductReview.product_id)
    )
    if product_ids is not None:
        query = query.filter(ProductReview.product_id.in_(list(product_ids)))
    return {pid: (float(avg or 0), int(count)) for pid, avg, count in query.all()}


def serialize_products(products, admin_view=False):
    """Product dicts with the average rating and review count filled in from the reviews table."""
    products = list(products)
    stats = review_stats([p.id for p in products]) if products else {}
    result = []
    for product in products:
        average, count = stats.get(product.id, (0.0, 0))
        result.append(
            product.to_admin_dict(average, count) if admin_view else product.to_dict(average, count)
        )
    return result


def serialize_product(product, admin_view=False):
    return serialize_products([product], admin_view=admin_view)[0]
