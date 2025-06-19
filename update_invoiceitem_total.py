from app import create_app, db
from app.models import InvoiceItem

app = create_app()
app.app_context().push()

def update_totals():
    items = InvoiceItem.query.all()
    for item in InvoiceItem.query.all():
        number_of_items = item.number_of_items or 0
        amount = item.amount or 0
        item.total = number_of_items * amount
    db.session.commit()
    print(f"Updated total for {len(items)} invoice items.")

if __name__ == '__main__':
    update_totals()
