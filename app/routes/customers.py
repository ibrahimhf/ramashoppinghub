from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.models import Customer, Invoice, Payment
from app.extensions import db
from sqlalchemy.orm import joinedload
from datetime import datetime

customers_bp = Blueprint('customers', __name__, url_prefix='/customers')

@customers_bp.route('/')
def list_customers():
    q = request.args.get('q', '').strip()
    if q:
        customers = customers.filter(
            Customer.name.ilike(f'%{q}%') |
            Customer.email.ilike(f'%{q}%')
        )
    customers = Customer.query.options(
        joinedload(Customer.invoices).joinedload(Invoice.items),
        joinedload(Customer.invoices).joinedload(Invoice.payments)
    ).order_by(Customer.name).all()
    return render_template('customers/list.html', customers=customers)

@customers_bp.route('/<int:id>')
def customer_detail(id):
    customer = Customer.query.get_or_404(id)
    return render_template('customers/detail.html', customer=customer)

@customers_bp.route('/<int:id>/wallet_topup', methods=['POST'])
def wallet_topup(id):
    customer = Customer.query.get_or_404(id)
    try:
        amount = float(request.form.get('amount'))
        if amount <= 0:
            flash('Amount must be positive.', 'error')
            return redirect(url_for('customers.customer_detail', id=id))
    except (TypeError, ValueError):
        flash('Invalid amount.', 'error')
        return redirect(url_for('customers.customer_detail', id=id))

    customer.wallet_balance += amount
    db.session.commit()
    flash(f'Wallet topped up by ${amount:.2f}.', 'success')
    return redirect(url_for('customers.customer_detail', id=id))

# GET route to display the Add Payment form
@customers_bp.route('/<int:id>/add_payment', methods=['GET'])
def add_payment_form(id):
    customer = Customer.query.options(
        joinedload(Customer.invoices).joinedload(Invoice.payments)
    ).get_or_404(id)
    unpaid_invoices = [inv for inv in customer.invoices if inv.balance_due > 0]
    return render_template('customers/add_payment.html', customer=customer, unpaid_invoices=unpaid_invoices)

# POST route to process the payment form
@customers_bp.route('/<int:id>/add_payment', methods=['POST'])
def add_payment(id):
    customer = Customer.query.get_or_404(id)
    invoice_id = request.form.get('invoice_id')
    method = request.form.get('method')
    try:
        amount = float(request.form.get('amount'))
        if amount <= 0:
            return jsonify({'error': 'Amount must be positive.'}), 400
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid amount.'}), 400

    if not method or method.strip() == '':
        return jsonify({'error': 'Payment method is required.'}), 400

    if invoice_id:
        invoice = Invoice.query.filter_by(id=invoice_id, customer_id=customer.id).first()
        if not invoice:
            return jsonify({'error': 'Invoice not found.'}), 404
        if amount > invoice.balance_due:
            return jsonify({'error': f'Amount exceeds invoice balance of ${invoice.balance_due:.2f}.'}), 400

        payment = Payment(
            invoice_id=invoice.id,
            amount=amount,
            method=method.strip(),
            payment_date=datetime.utcnow()
        )
        db.session.add(payment)

        invoice.update_status()
        message = f'Payment of ${amount:.2f} applied to Invoice #{invoice.id}.'

    else:
        customer.wallet_balance += amount
        message = f'Added ${amount:.2f} to customer wallet.'

    db.session.commit()
    return jsonify({'message': message}), 200

@customers_bp.route('/new', methods=['GET', 'POST'])
def add_customer():
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        address = request.form.get('address')

        if not name or not address:
            flash('Name and Address are required!', 'error')
            return redirect(url_for('customers.add_customer'))

        new_customer = Customer(name=name, phone=phone, address=address)
        db.session.add(new_customer)
        db.session.commit()
        flash('Customer added successfully!', 'success')
        return redirect(url_for('customers.list_customers'))

    return render_template('customers/add.html')

@customers_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_customer(id):
    customer = Customer.query.get_or_404(id)

    if request.method == 'POST':
        customer.name = request.form.get('name')
        customer.phone = request.form.get('phone')
        customer.address = request.form.get('address')

        if not customer.name:
            flash('Name is required!', 'error')
            return redirect(url_for('customers.edit_customer', id=id))

        db.session.commit()
        flash('Customer updated successfully!', 'success')
        return redirect(url_for('customers.list_customers'))

    return render_template('customers/edit.html', customer=customer)

@customers_bp.route('/delete/<int:id>', methods=['POST'])
def delete_customer(id):
    customer = Customer.query.get_or_404(id)
    db.session.delete(customer)
    db.session.commit()
    flash('Customer deleted.', 'success')
    return redirect(url_for('customers.list_customers'))
