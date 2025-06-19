from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.extensions import db
from app.models import Expense
from datetime import datetime, date, time
from app.models import ExpenseCategory
from sqlalchemy import func, and_

expenses_bp = Blueprint('expenses', __name__, url_prefix='/expenses')

@expenses_bp.route('/')
def list_expenses():
    q = request.args.get('q', '').strip()

    # Get dates from request or default to today
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    today_str = date.today().strftime('%Y-%m-%d')

    if not start_date:
        start_date = today_str
    if not end_date:
        end_date = today_str

    query = Expense.query.join(ExpenseCategory, isouter=True)

    # Apply search filter if q provided
    if q:
        query = query.filter(
            Expense.description.ilike(f'%{q}%') |
            Expense.order_number.ilike(f'%{q}%') |
            ExpenseCategory.name.ilike(f'%{q}%')
        )

    # Filter by date range (inclusive)
    if start_date and end_date:
        query = query.filter(
            and_(
                Expense.date >= start_date,
                Expense.date <= end_date
            )
        )

    expenses = query.order_by(Expense.date.desc()).all()

    # Calculate total amount for filtered expenses, ignoring reversed if applicable
    total_amount = query.with_entities(func.coalesce(func.sum(Expense.amount), 0)).scalar()

    categories = ExpenseCategory.query.all()

    return render_template(
        'expenses/list.html',
        expenses=expenses,
        categories=categories,
        q=q,
        start_date=start_date,
        end_date=end_date,
        total_amount=total_amount
    )


@expenses_bp.route('/add', methods=['GET', 'POST'])
def add_expense():
    try:
        print("🔵 Received POST data:", request.form)
        amount = float(request.form['amount'])
        description = request.form['description']
        date = datetime.strptime(request.form['date'], "%Y-%m-%d").date()
        category_id = request.form.get('category_id')
        order_number = request.form.get('order_number')  # new field

        expense = Expense(
            amount=amount,
            description=description,
            date=date,
            category_id=int(category_id) if category_id else None,
            order_number=order_number if order_number else None
        )
        db.session.add(expense)
        db.session.commit()
        print(f"✅ Expense saved: {expense}")
        print("🔧 Using DB URI:", db.engine.url)
        flash("Expense added successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error adding expense: {str(e)}", "danger")

    return redirect(url_for('expenses.list_expenses'))


@expenses_bp.route('/reverse/<int:expense_id>', methods=['POST'])
def reverse_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)

    if expense.reversed:
        flash('This expense has already been reversed.', 'warning')
        return redirect(url_for('expenses.list_expenses'))

    expense.reversed = True
    db.session.commit()
    flash('Expense reversed successfully.', 'success')
    return redirect(url_for('expenses.list_expenses'))


@expenses_bp.route('/categories/add', methods=['POST'])
def add_category():
    name = request.form['category_name'].strip()
    if name:
        existing = ExpenseCategory.query.filter_by(name=name).first()
        if not existing:
            new_cat = ExpenseCategory(name=name)
            db.session.add(new_cat)
            db.session.commit()
            flash("Category added.", "success")
        else:
            flash("Category already exists.", "warning")
    return redirect(url_for('expenses.list_expenses'))
