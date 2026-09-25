from app.routes.auth import auth_bp
from app.routes.admin_auth import admin_auth_bp
from app.routes.products import products_bp
from app.routes.orders import orders_bp
from app.routes.admin_orders import admin_orders_bp
from app.routes.admin_users import admin_users_bp
from app.routes.knowledge import knowledge_bp
from app.routes.chat import chat_bp
from app.routes.admin_dashboard import admin_dashboard_bp
from app.routes.admin_analytics import admin_analytics_bp


def register_routes(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_auth_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(admin_orders_bp)
    app.register_blueprint(admin_users_bp)
    app.register_blueprint(knowledge_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(admin_dashboard_bp)
    app.register_blueprint(admin_analytics_bp)