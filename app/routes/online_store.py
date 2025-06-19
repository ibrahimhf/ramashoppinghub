from flask import Blueprint, render_template, redirect, url_for, request, flash
from app import db
from app.models import OnlineStore, Invoice
from app.forms import OnlineStoreForm
from sqlalchemy import func
from app.models import InvoiceItem

store_bp = Blueprint('store', __name__)

@store_bp.route('/stores', methods=['GET', 'POST'])
def list_stores():
    form = OnlineStoreForm()
    if form.validate_on_submit():
        store = OnlineStore(name=form.name.data)
        db.session.add(store)
        db.session.commit()
        flash('Store added successfully!', 'success')
        return redirect(url_for('store.list_stores'))

    stores = OnlineStore.query.all()
    store_data = []

    for store in stores:
        invoice_count = Invoice.query.filter_by(store_id=store.id).count()
        total_amount = (
    db.session.query(func.sum(InvoiceItem.amount))
    .join(Invoice)
    .filter(Invoice.store_id == store.id)
    .scalar()
    or 0
)
        store_data.append({
            'name': store.name,
            'invoice_count': invoice_count,
            'total_amount': total_amount
        })
        

    return render_template('stores/index.html', form=form, store_data=store_data)
