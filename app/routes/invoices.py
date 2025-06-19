from flask import Blueprint, render_template, make_response, redirect, url_for, request, flash
from app.extensions import db
from ..models import Invoice, InvoiceItem, Customer, Payment
from ..forms import PaymentForm
from weasyprint import HTML
from app.forms import InvoiceForm
from app.models import OnlineStore
from sqlalchemy import or_, func
from datetime import datetime, date, time

invoices_bp = Blueprint('invoices', __name__, url_prefix='/invoices')

@invoices_bp.route('/')
def index():
    customer_id = request.args.get('customer_id', type=int)
    store_id = request.args.get('store_id', type=int)
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    q = request.args.get('q', '').strip()

    # Default to today if not provided
    today_str = date.today().strftime('%Y-%m-%d')
    if not start_date_str:
        start_date_str = today_str
    if not end_date_str:
        end_date_str = today_str

    query = Invoice.query.join(Customer).outerjoin(OnlineStore)

    if customer_id:
        query = query.filter(Invoice.customer_id == customer_id)
    if store_id:
        query = query.filter(Invoice.store_id == store_id)

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        query = query.filter(Invoice.date_created >= start_date)
    except ValueError:
        pass

    try:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        end_date = datetime.combine(end_date.date(), time.max)
        query = query.filter(Invoice.date_created <= end_date)
    except ValueError:
        pass

    if q:
        query = query.filter(or_(
            Customer.name.ilike(f"%{q}%"),
            Invoice.order_number.ilike(f"%{q}%")
        ))

    invoices = query.order_by(Invoice.date_created.desc()).all()
    total_amount = sum(inv.total_amount for inv in invoices)

    customers = Customer.query.order_by(Customer.name).all()
    stores = OnlineStore.query.order_by(OnlineStore.name).all()

    return render_template('invoices/index.html',
                           invoices=invoices,
                           customers=customers,
                           stores=stores,
                           total_amount=total_amount,
                           customer_id=customer_id,
                           store_id=store_id,
                           start_date=start_date_str,
                           end_date=end_date_str,
                           q=q)


@invoices_bp.route('/new', methods=['GET', 'POST'])


@invoices_bp.route('/new', methods=['GET', 'POST'])
def new_invoice():
    print("🚨 new_invoice route hit")

    customer_choices = [(c.id, c.name) for c in Customer.query.all()]
    form = InvoiceForm(request.form)
    form.store.choices = [(store.id, store.name) for store in OnlineStore.query.all()]
    form.customer_id.choices = customer_choices

    if request.method == 'POST':
        print("📥 POST request received")
        if form.validate():
            print("✅ Form validated successfully")

            invoice = Invoice(
                customer_id=form.customer_id.data,
                delivery_fees=form.delivery_fees.data or 0,
                due_date=form.due_date.data,
                invoice_date=form.invoice_date.data,
                order_number=form.order_number.data,
                store_id=form.store.data
            )
            for item_form in form.items.entries:
                item = InvoiceItem(
        number_of_items=item_form.form.number_of_items.data,
        amount=item_form.form.amount.data,
        delivery_fees=item_form.form.delivery_fees.data or 0.0
    )
                item.calculate_total()
                invoice.items.append(item)

            db.session.add(invoice)
            db.session.commit()

            invoice.update_status()
            db.session.commit()

            flash('Invoice created successfully', 'success')
            return redirect(url_for('invoices.view_invoice', invoice_id=invoice.id))
        else:
            print("❌ Form validation failed")
            print("Form errors:", form.errors)
    else:
        if len(form.items) == 0:
            form.items.append_entry()

    return render_template('invoices/new_invoice.html', form=form)

@invoices_bp.route('/<int:invoice_id>', methods=['GET', 'POST'])
def view_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    payment_form = PaymentForm()

    if payment_form.validate_on_submit():
        try:
            amount = float(payment_form.amount.data)
            use_wallet = request.form.get('use_wallet') == 'on'  # checkbox named 'use_wallet'

            customer = invoice.customer
            total_available = invoice.balance_due
            if use_wallet:
                total_available += customer.wallet_balance

            if amount > total_available:
                flash('Payment amount exceeds balance due plus wallet balance', 'danger')
            else:
                remaining_amount = amount

                if use_wallet and customer.wallet_balance > 0:
                    wallet_use = min(customer.wallet_balance, remaining_amount)
                    customer.wallet_balance -= wallet_use

                    wallet_payment = Payment(
                        customer_id=customer.id,
                        amount=wallet_use,
                        method='wallet',
                        payment_type='wallet',
                        payment_date=datetime.utcnow(),
                        date_created=datetime.utcnow()
                    )
                    db.session.add(wallet_payment)
                    remaining_amount -= wallet_use

                if remaining_amount > 0:
                    invoice_payment = Payment(
                        invoice_id=invoice.id,
                        customer_id=customer.id,
                        amount=remaining_amount,
                        method=payment_form.method.data,
                        payment_type='invoice',
                        payment_date=datetime.utcnow(),
                        date_created=datetime.utcnow()
                    )
                    db.session.add(invoice_payment)

                db.session.commit()

                invoice.update_status()
                db.session.commit()

                flash('Payment recorded successfully', 'success')
                return redirect(url_for('invoices.view_invoice', invoice_id=invoice.id))

        except Exception as e:
            db.session.rollback()
            flash(f"Error processing payment: {str(e)}", "danger")

    return render_template('invoices/view_invoice.html', invoice=invoice, payment_form=payment_form)

@invoices_bp.route('/<int:invoice_id>/pdf')
def invoice_pdf(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    rendered = render_template('invoices/invoice_pdf.html', invoice=invoice)
    pdf = HTML(string=rendered).write_pdf()

    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=invoice_{invoice_id}.pdf'
    return response

@invoices_bp.route('/<int:invoice_id>/items/add', methods=['POST'])
def add_invoice_item(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)

    number_of_items = int(request.form['number_of_items'])
    amount = int(request.form['amount'])
    item = InvoiceItem(invoice=invoice,
                   number_of_items=number_of_items,
                   amount=amount,
                   unit_price=1.0)
    item.calculate_total()
    db.session.add(item)
    db.session.commit()

    invoice.update_status()
    db.session.commit()

    return redirect(url_for('invoices.view_invoice', invoice_id=invoice_id))
