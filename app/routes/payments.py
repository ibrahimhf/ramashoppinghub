from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.extensions import db
from app.models import Payment, Invoice, Customer
from datetime import datetime, date, time
from flask import jsonify
import traceback
import logging
from sqlalchemy import func

payments_bp = Blueprint('payments', __name__, url_prefix='/payments')

@payments_bp.route('/add', methods=['GET', 'POST'])
def add_payment():
    if request.method == 'GET':
        customer_id = request.args.get('customer_id', type=int)
        
        # Get all customers for dropdown
        customers = Customer.query.order_by(Customer.name).all()
        
        unpaid_invoices = []
        if customer_id:
            # Load unpaid invoices for selected customer
            all_invoices = Invoice.query.filter_by(customer_id=customer_id).all()
            unpaid_invoices = [inv for inv in all_invoices if inv.balance_due > 0]

        return render_template(
            'payments/add.html',
            customers=customers,
            selected_customer_id=customer_id,
            unpaid_invoices=unpaid_invoices
        )

    # POST: handle form submission to add payment
    try:
        # Validate required fields
        if 'amount' not in request.form or not request.form['amount'].strip():
            raise ValueError("Amount is required.")
        if 'method' not in request.form or not request.form['method'].strip():
            raise ValueError("Payment method is required.")
        payment_type = request.form.get('payment_type')
        if payment_type not in ('invoice', 'wallet'):
            raise ValueError("Invalid or missing payment type.")

        amount = float(request.form['amount'])
        method = request.form['method']

        def get_customer_by_invoice(invoice_id):
            invoice = Invoice.query.get(invoice_id)
            if not invoice:
                raise ValueError("Invoice not found.")
            if not invoice.customer:
                raise ValueError("Invoice has no associated customer.")
            return invoice, invoice.customer

        def get_customer_by_id(customer_id):
            customer = Customer.query.get(customer_id)
            if not customer:
                raise ValueError("Customer not found.")
            return customer

        if payment_type == 'invoice':
            invoice_id = request.form.get('invoice_id')
            if not invoice_id:
                raise ValueError("Invoice ID is required for invoice payment.")

            invoice, customer = get_customer_by_invoice(int(invoice_id))

            use_wallet = request.form.get('use_wallet') == 'true'

            remaining_amount = amount
            if use_wallet and customer.wallet_balance <= 0:
                raise ValueError("Customer wallet balance is insufficient to use wallet.")
            # Use wallet first if requested
            if use_wallet and customer.wallet_balance > 0:
                wallet_use = min(customer.wallet_balance, remaining_amount)
                # Deduct from wallet
                customer.wallet_balance -= wallet_use

                # Record wallet deduction payment
                wallet_payment = Payment(
                    invoice_id=invoice.id,
                    customer_id=customer.id,
                    amount=wallet_use,
                    method='wallet',
                    payment_type='invoice',
                    payment_date=datetime.utcnow(),
                    date_created=datetime.utcnow()
                )
                db.session.add(wallet_payment)

                remaining_amount -= wallet_use

            # If remaining amount to pay on invoice, create invoice payment
            if remaining_amount > 0:
                invoice_payment = Payment(
                    invoice_id=invoice.id,
                    customer_id=customer.id,
                    amount=remaining_amount,
                    method=method,
                    payment_type='invoice',
                    payment_date=datetime.utcnow(),
                    date_created=datetime.utcnow()
                )
                db.session.add(invoice_payment)

            db.session.commit()

            invoice.update_status()
            db.session.commit()

        elif payment_type == 'wallet':
            customer_id = request.form.get('customer_id')
            if not customer_id:
                raise ValueError("Customer ID is required for wallet payment.")

            customer = get_customer_by_id(int(customer_id))

            wallet_topup = Payment(
                customer_id=customer.id,
                amount=amount,
                method=method,
                payment_type='wallet',
                payment_date=datetime.utcnow(),
                date_created=datetime.utcnow()
            )
            db.session.add(wallet_topup)
            customer.wallet_balance += amount
            db.session.commit()

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify(success=True, message="Payment added successfully!")

        flash("Payment added successfully!", "success")
        return redirect(url_for('payments.list_payments'))

    except Exception as e:
        db.session.rollback()
        logging.error("Exception in add_payment:\n" + traceback.format_exc())
        error_msg = str(e)
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify(success=False, error=error_msg), 500
        flash(f"Error adding payment: {error_msg}", "danger")
        # Preserve customer_id in redirect if possible
        customer_id = request.form.get('customer_id')
        return redirect(url_for('payments.add_payment', customer_id=customer_id))

@payments_bp.route('/reverse/<int:payment_id>', methods=['POST'])
def reverse_payment(payment_id):
    try:
        payment = Payment.query.get_or_404(payment_id)
        customer = payment.customer

        if payment.reversed:
            flash("Payment is already reversed.", "warning")
            return redirect(url_for('payments.list_payments'))

        # Mark payment as reversed with timestamp
        payment.reversed = True
        payment.reversed_at = datetime.utcnow()
        db.session.add(payment)

        if payment.payment_type == 'invoice':
            invoice = payment.invoice
            if invoice:
                # Update invoice status to reflect reversal
                invoice.update_status()
                db.session.add(invoice)

        elif payment.payment_type == 'wallet':
            # Deduct the reversed amount from the customer's wallet balance
            customer.wallet_balance -= payment.amount
            db.session.add(customer)

        db.session.commit()
        flash("Payment reversed successfully.", "success")

    except Exception as e:
        db.session.rollback()
        import traceback, logging
        logging.error("Reverse payment error:\n" + traceback.format_exc())
        flash(f"Error reversing payment: {e}", "danger")

    return redirect(url_for('payments.list_payments'))

@payments_bp.route('/')
def list_payments():
    q = request.args.get('q', '').strip()
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    # Default dates to today if missing or invalid
    try:
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        else:
            start_date = date.today()
            start_date_str = start_date.strftime('%Y-%m-%d')
    except ValueError:
        start_date = date.today()
        start_date_str = start_date.strftime('%Y-%m-%d')

    try:
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        else:
            end_date = date.today()
            end_date_str = end_date.strftime('%Y-%m-%d')
    except ValueError:
        end_date = date.today()
        end_date_str = end_date.strftime('%Y-%m-%d')

    # Base query: include all payments, reversed or not
    payments_query = Payment.query.join(Customer)

    # Filter by search query if provided
    if q:
        payments_query = payments_query.filter(
            (Customer.name.ilike(f'%{q}%')) |
            (Payment.method.ilike(f'%{q}%'))
        )

    # Filter by date range, inclusive
    payments_query = payments_query.filter(
        Payment.payment_date >= datetime.combine(start_date, time.min),
        Payment.payment_date <= datetime.combine(end_date, time.max)
    )

    payments = payments_query.order_by(Payment.payment_date.desc()).all()

    # Calculate total only for active (not reversed) payments in the same date range & filters
    total_amount = payments_query.filter(Payment.reversed == False)\
                                 .with_entities(func.coalesce(func.sum(Payment.amount), 0))\
                                 .scalar()

    return render_template(
        'payments/list.html',
        payments=payments,
        q=q,
        start_date=start_date_str,
        end_date=end_date_str,
        total_amount=total_amount,
        now=datetime.utcnow  # so you can call now() in Jinja if needed
    )

@payments_bp.route('/api/unpaid_invoices/<int:customer_id>')
def get_unpaid_invoices(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    all_invoices = Invoice.query.filter_by(customer_id=customer.id).all()
    unpaid_invoices = [
        {
            "id": inv.id,
            "display": f"Invoice #{inv.id} - ${inv.balance_due:.2f}"
        }
        for inv in all_invoices if inv.balance_due > 0
    ]
    return jsonify(unpaid_invoices)
