from app.extensions import db
from datetime import datetime
from sqlalchemy import Boolean, DateTime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(50))
    address = db.Column(db.String(250))
    wallet_balance = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    invoices = db.relationship('Invoice', backref='customer', cascade="all, delete-orphan")

    @property
    def total_invoiced(self):
        return sum(inv.total_amount for inv in self.invoices)

    @property
    def total_paid(self):
        return sum(inv.amount_paid for inv in self.invoices)

    @property
    def balance_due(self):
        return max(self.total_invoiced - self.total_paid, 0)

    @property
    def payment_history(self):
        payments = []
        for invoice in self.invoices:
            payments.extend(invoice.payments)
        return sorted(payments, key=lambda p: p.payment_date, reverse=True)


class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    store_id = db.Column(db.Integer, db.ForeignKey('online_store.id'), nullable=True)
    order_number = db.Column(db.String(100))
    due_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), default="Unpaid")  # Unpaid, Partial, Paid
    delivery_fees = db.Column(db.Float, default=0.0, nullable=True)
    invoice_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)

    items = db.relationship('InvoiceItem', backref='invoice', cascade="all, delete-orphan")
    payments = db.relationship('Payment', back_populates='invoice')

    @property
    def total_amount(self):
        return sum(
        (item.amount) + (item.delivery_fees or 0)
        for item in self.items
    )
        return items_total + (self.delivery_fees or 0)

    @property
    def amount_paid(self):
        return sum(
        payment.amount 
        for payment in self.payments
        if payment.payment_type == 'invoice' and not payment.reversed
    )

    @property
    def balance_due(self):
        return self.total_amount - self.amount_paid

    def update_status(self):
        if self.amount_paid == 0:
            self.status = "Unpaid"
        elif self.amount_paid < self.total_amount:
            self.status = "Partial"
        else:
            self.status = "Paid"

class InvoiceItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    number_of_items = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    delivery_fees = db.Column(db.Float, nullable=True, default=0.0)
    total = db.Column(db.Float, default=0.0)

    def calculate_total(self):
        self.total = self.amount

    
class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    payment_type = db.Column(db.String(50), nullable=False)

    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=True)
    invoice = db.relationship('Invoice', back_populates='payments')

    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    customer = db.relationship('Customer', backref='payments')

    method = db.Column(db.String(50))
    payment_date = db.Column(db.DateTime)
    date_created = db.Column(db.DateTime)
    date = db.Column(db.DateTime, default=datetime.utcnow)

    reversed = db.Column(db.Boolean, default=False)
    reversed_at = db.Column(DateTime, nullable=True)


class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(120), nullable=False)
    order_number = db.Column(db.String(64), nullable=True)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('expense_category.id'))
    category = db.relationship('ExpenseCategory', backref='expenses')
    is_reversed = db.Column(db.Boolean, default=False)  

    def __repr__(self):
        return f"<Expense {self.description} - ${self.amount}>"
class ExpenseCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)

class OnlineStore(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    invoices = db.relationship('Invoice', backref='store', lazy=True)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)    