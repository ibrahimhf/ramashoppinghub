from flask import Blueprint, render_template, request
from app.models import Invoice, Payment, Customer, Expense, InvoiceItem
from datetime import datetime, timedelta, date
from app.extensions import db
from sqlalchemy import func, literal_column
from sqlalchemy.orm import aliased

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    start_date = end_date = None
    if start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        except ValueError:
            start_date = end_date = None

    # Filter invoices by date
    invoice_query = Invoice.query
    if start_date and end_date:
        invoice_query = invoice_query.filter(Invoice.date_created.between(start_date, end_date))
    invoices = invoice_query.all()

    # Expenses excluding reversed, filtered by date if provided
    total_expenses_query = db.session.query(func.coalesce(func.sum(Expense.amount), 0)).filter(Expense.is_reversed == False)
    if start_date and end_date:
        total_expenses_query = total_expenses_query.filter(Expense.date.between(start_date, end_date))
    total_expenses = total_expenses_query.scalar() or 0

    # Subquery: sum invoice items amount per invoice
    invoice_items_sum = (
    db.session.query(
        InvoiceItem.invoice_id.label('inv_id'),
        func.coalesce(
            func.sum(
                (InvoiceItem.amount) +
                func.coalesce(InvoiceItem.delivery_fees, 0)
            ), 0
        ).label('total_amount')
    )
    .group_by(InvoiceItem.invoice_id)
    .subquery()
)

    # Subquery: sum payments amount per invoice (only non-reversed invoice payments)
    invoice_payments_sum = (
        db.session.query(
            Payment.invoice_id.label('inv_id'),
            func.coalesce(func.sum(Payment.amount), 0).label('amount_paid')
        )
        .filter(Payment.payment_type == 'invoice', Payment.reversed == False)
        .group_by(Payment.invoice_id)
        .subquery()
    )

    items_alias = aliased(invoice_items_sum)
    payments_alias = aliased(invoice_payments_sum)

    # Total invoice amount (original invoice values)
    total_invoice_amount_query = db.session.query(
    func.coalesce(
        func.sum(
            (InvoiceItem.amount) +
            func.coalesce(InvoiceItem.delivery_fees, 0)
        ), 0
    )
).join(Invoice)

    if start_date and end_date:
        total_invoice_amount_query = total_invoice_amount_query.filter(
        Invoice.date_created.between(start_date, end_date)
    )

    total_invoice_amount = total_invoice_amount_query.scalar() or 0

    # Total payments: all non-reversed payments, filtered by date if applicable
    total_payments_query = db.session.query(func.coalesce(func.sum(Payment.amount), 0)).filter(Payment.reversed == False)
    if start_date and end_date:
        total_payments_query = total_payments_query.filter(Payment.payment_date.between(start_date, end_date))
    total_payments = total_payments_query.scalar() or 0

    # Total revenue = invoice amount - expenses
    total_revenue = total_invoice_amount - total_expenses

    # Pending payments
    pending_payments_query = db.session.query(
        func.coalesce(func.sum(
            func.coalesce(items_alias.c.total_amount, 0) - func.coalesce(payments_alias.c.amount_paid, 0)
        ), 0)
    ).select_from(Invoice)\
    .outerjoin(items_alias, Invoice.id == items_alias.c.inv_id)\
    .outerjoin(payments_alias, Invoice.id == payments_alias.c.inv_id)

    if start_date and end_date:
        pending_payments_query = pending_payments_query.filter(Invoice.date_created.between(start_date, end_date))

    pending_payments_query = pending_payments_query.filter(
        (func.coalesce(items_alias.c.total_amount, 0) - func.coalesce(payments_alias.c.amount_paid, 0)) > 0
    )

    pending_payments = pending_payments_query.scalar() or 0

    total_clients = Customer.query.count()

    return render_template(
        'dashboard.html',
        total_invoices=len(invoices),
        pending_payments=pending_payments,
        total_revenue=total_revenue,
        total_expenses=total_expenses,
        total_clients=total_clients,
        total_invoices_amount=total_invoice_amount,
        total_payments=total_payments,
        start_date=start_date_str,
        end_date=end_date_str
    )
