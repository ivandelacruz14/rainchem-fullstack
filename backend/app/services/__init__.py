from flask import Flask, jsonify

from config import Config
from app.extensions import db, jwt, cors


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": app.config["FRONTEND_URL"]}})

    from app.routes import register_routes
    register_routes(app)

    if not app.config.get("TESTING"):
        from app.services.schema_updates import ensure_schema
        with app.app_context():
            try:
                ensure_schema(db, app.logger)
            except Exception as error:
                app.logger.error("Schema check failed: %s", error)

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Not found"}), 404

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    return app