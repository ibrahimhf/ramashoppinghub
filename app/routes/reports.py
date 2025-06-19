from flask import Blueprint, render_template, request
from datetime import datetime, timedelta, date
from app.models import Payment, Expense
from sqlalchemy import func, or_

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/bank-report')
def bank_report():
    q = request.args.get('q', '').strip()
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    # Handle date parsing with fallback to today
    if not start_date_str or not end_date_str:
        today = date.today()
        start_date = end_date = today
        start_date_str = end_date_str = today.strftime('%Y-%m-%d')
    else:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            today = date.today()
            start_date = end_date = today
            start_date_str = end_date_str = today.strftime('%Y-%m-%d')

    # Build payments query
    payment_query = Payment.query.filter(
        Payment.reversed == False,
        Payment.payment_date >= datetime.combine(start_date, datetime.min.time()),
        Payment.payment_date <= datetime.combine(end_date, datetime.max.time())
    )

    if q:
        payment_query = payment_query.join(Payment.customer).filter(
            func.lower(Payment.customer.name).like(f'%{q.lower()}%')
        )

    payments = payment_query.order_by(Payment.payment_date.desc()).limit(10).all()
    total_payments = sum(p.amount for p in payments)

    # Build expenses query
    expense_query = Expense.query.filter(
        Expense.is_reversed == False,
        Expense.date.between(start_date, end_date)
    )

    if q:
        expense_query = expense_query.filter(
            func.lower(Expense.description).like(f'%{q.lower()}%')
        )

    expenses = expense_query.order_by(Expense.date.desc()).limit(10).all()
    total_expenses = sum(e.amount for e in expenses)

    # Render the template with all required variables
    return render_template(
        'reports/bank_report.html',
        payments=payments,
        expenses=expenses,
        total_payments=total_payments,
        total_expenses=total_expenses,
        q=q,
        start_date=start_date_str,
        end_date=end_date_str
    )