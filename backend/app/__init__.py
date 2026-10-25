from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from config import Config
from app.extensions import db, jwt, cors


def frontend_origins(raw):
    """FRONTEND_URL may hold several origins; trailing slashes would break CORS matching."""
    return [part.strip().rstrip("/") for part in (raw or "").split(",") if part.strip()]


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    jwt.init_app(app)
    origins = frontend_origins(app.config["FRONTEND_URL"])
    app.config["FRONTEND_ORIGINS"] = origins
    app.config["FRONTEND_BASE_URL"] = origins[0] if origins else "http://localhost:5173"
    cors.init_app(app, resources={r"/api/*": {"origins": origins}})

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

    @app.errorhandler(Exception)
    def unexpected_error(error):
        if isinstance(error, HTTPException):
            return error
        app.logger.exception("Unhandled error on %s", error.__class__.__name__)
        db.session.rollback()
        return jsonify({"error": "The server ran into a problem. Please try again in a moment."}), 500

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    return app
