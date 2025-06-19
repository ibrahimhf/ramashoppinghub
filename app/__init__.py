from flask import Flask, render_template
from app.extensions import db, migrate  # import from extensions
from app.routes import register_routes
from app.routes.payments import payments_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

    db.init_app(app)
    migrate.init_app(app, db)

    register_routes(app)

    from . import models  # keep this here so models register properly

    @app.route('/')
    def home():
        return render_template('dashboard.html')

    return app
