from flask import Flask, render_template
from extensions import db, login_manager, csrf
from auth.routes import auth_bp
from manager.routes import manager_bp
from chef.routes import chef_bp
from packer.routes import packer_bp
from quality.routes import quality_bp
import os


def create_app():
    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.environ.get(
        "SECRET_KEY",
        "kitchenflow-secret-2026"
    )

    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///kitchenflow.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["WTF_CSRF_TIME_LIMIT"] = None

    db.init_app(app)

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    csrf.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(manager_bp, url_prefix="/manager")
    app.register_blueprint(chef_bp, url_prefix="/chef")
    app.register_blueprint(packer_bp, url_prefix="/packer")
    app.register_blueprint(quality_bp, url_prefix="/quality")

    # Error Pages
    @app.errorhandler(403)
    def err_403(e):
        return render_template(
            "errors/error.html",
            code=403,
            title="Access denied",
            message="You don't have permission to view that page."
        ), 403

    @app.errorhandler(404)
    def err_404(e):
        return render_template(
            "errors/error.html",
            code=404,
            title="Not found",
            message="The page you requested could not be located."
        ), 404

    @app.errorhandler(500)
    def err_500(e):
        return render_template(
            "errors/error.html",
            code=500,
            title="Something went wrong",
            message="An unexpected error occurred. Please try again."
        ), 500

    with app.app_context():
        db.create_all()

        from seed import seed_data
        seed_data()

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)