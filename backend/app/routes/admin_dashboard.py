from flask import Blueprint, request, jsonify

from app.models import Order, OrderItem, User, Product, KnowledgeEntry, ChatLog
from app.services.admin_scope import scope_product_ids
from app.services.sales_analytics import recorded_revenue
from app.utils.auth_decorators import current_admin, require_admin, require_head_admin

admin_dashboard_bp = Blueprint("admin_dashboard", __name__, url_prefix="/api/admin")


@admin_dashboard_bp.get("/overview")
@require_admin
def overview():
    admin = current_admin()
    ids = scope_product_ids(admin)
    revenue, sale_orders = recorded_revenue(ids)

    if not admin.is_head:
        products = Product.query.filter(Product.owner_admin_id == admin.id)
        return jsonify({
            "scope": "limited",
            "stats": {
                "totalRevenue": revenue,
                "orderCount": sale_orders,
                "productCount": products.count(),
                "lowStockCount": products.filter(Product.stock < 20).count(),
            },
            "recentOrders": [],
            "topFaqs": [],
        })

    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    top_faqs = KnowledgeEntry.query.order_by(KnowledgeEntry.hits.desc()).limit(5).all()
    return jsonify({
        "scope": "full",
        "stats": {
            "totalRevenue": revenue,
            "orderCount": Order.query.count(),
            "saleOrderCount": sale_orders,
            "userCount": User.query.count(),
            "verifiedUserCount": User.query.filter_by(verified=True).count(),
            "productCount": Product.query.filter(Product.category != "Services").count(),
            "lowStockCount": Product.query.filter(Product.category != "Services", Product.stock < 20).count(),
            "pendingKnowledgeCount": KnowledgeEntry.query.filter_by(status="pending").count(),
            "chatCount": ChatLog.query.count(),
        },
        "recentOrders": [o.to_dict() for o in recent_orders],
        "topFaqs": [e.to_dict() for e in top_faqs],
    })


@admin_dashboard_bp.get("/chat-monitor")
@require_head_admin
def chat_monitor():
    resolved_filter = request.args.get("resolved")
    query = ChatLog.query
    if resolved_filter == "true":
        query = query.filter_by(resolved=True)
    elif resolved_filter == "false":
        query = query.filter_by(resolved=False)

    logs = query.order_by(ChatLog.created_at.desc()).limit(50).all()
    total = ChatLog.query.count()
    resolved = ChatLog.query.filter_by(resolved=True).count()
    avg_confidence = 0
    if total:
        avg_confidence = round(sum(l.confidence for l in ChatLog.query.all()) / total)

    return jsonify({
        "logs": [l.to_dict() for l in logs],
        "stats": {
            "total": total,
            "resolved": resolved,
            "unresolved": total - resolved,
            "averageConfidence": avg_confidence,
        },
    })
