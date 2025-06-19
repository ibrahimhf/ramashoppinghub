from app.routes.invoices import invoices_bp
from app.routes.dashboard import main_bp
from app.routes.customers import customers_bp
from app.routes.expenses import expenses_bp
from app.routes.payments import payments_bp
from app.routes.reports import reports_bp
from app.routes.online_store import store_bp
from app.routes.auth import auth_bp

def register_routes(app):
    app.register_blueprint(invoices_bp)
    app.register_blueprint(customers_bp)
    app.register_blueprint(expenses_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(store_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
