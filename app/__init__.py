from flask import Flask, render_template
from app.extensions import db, migrate
from app.routes import register_routes
from flask_login import LoginManager
from flask_login import login_required

login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

    db.init_app(app)
    migrate.init_app(app, db)

    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    from app.models import User  # Ensure model imported

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    register_routes(app)

    @app.route('/')
    @login_required
    def home():
        return render_template('dashboard.html')

    return app
