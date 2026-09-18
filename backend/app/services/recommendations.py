from app.models import Product

COMPLEMENT_CATEGORIES = {
    "Oils & Fluids": ["Filters", "Services"],
    "Coolant": ["Services", "Accessories"],
    "Filters": ["Oils & Fluids"],
    "Brakes": ["Oils & Fluids"],
    "Accessories": ["Oils & Fluids"],
    "Services": ["Oils & Fluids", "Coolant"],
}


def get_recommendations(order, limit=4):
    purchased_ids = [item.product_id for item in order.items if item.product_id]
    purchased_products = Product.query.filter(Product.id.in_(purchased_ids)).all()
    purchased_categories = {p.category for p in purchased_products}

    pool = Product.query.filter(Product.stock > 0, ~Product.id.in_(purchased_ids)).all()

    recommendations = []
    for category in purchased_categories:
        for complement in COMPLEMENT_CATEGORIES.get(category, []):
            for product in pool:
                if product.category == complement and product not in recommendations:
                    recommendations.append(product)

    if len(recommendations) < limit:
        for product in pool:
            if product.category in purchased_categories and product not in recommendations:
                recommendations.append(product)

    if len(recommendations) < limit:
        for product in pool:
            if product not in recommendations:
                recommendations.append(product)

    return recommendations[:limit]
