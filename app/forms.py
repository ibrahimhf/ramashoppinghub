from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, DecimalField, FieldList, FormField, DateField, SubmitField, SelectField, FloatField
from wtforms.validators import DataRequired, NumberRange, Optional
from wtforms import Form

class InvoiceItemForm(FlaskForm):
    number_of_items = IntegerField('Number of Items', validators=[DataRequired(), NumberRange(min=1)])
    amount = DecimalField('Amount', validators=[DataRequired(), NumberRange(min=0)])
    delivery_fees = DecimalField('Delivery Fees', validators=[Optional(), NumberRange(min=0)])
    
    class Meta:
        csrf = False

class InvoiceForm(FlaskForm):
    customer_id = SelectField('Customer', coerce=int, validators=[DataRequired()])
    store = SelectField('Online Store', coerce=int, validators=[DataRequired()])
    order_number = StringField('Order Number')
    due_date = DateField('Due Date', format='%Y-%m-%d', validators=[DataRequired()])
    invoice_date = DateField('Invoice Date', format='%Y-%m-%d', validators=[DataRequired()])
    delivery_fees = DecimalField('Delivery Fees', validators=[Optional(), NumberRange(min=0)])
    items = FieldList(FormField(InvoiceItemForm), min_entries=1)
    submit = SubmitField('Create Invoice')
    

class PaymentForm(FlaskForm):
    amount = DecimalField('Payment Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    method = SelectField('Payment Method', choices=[('Cash', 'Cash'), ('Card', 'Card'), ('Transfer', 'Transfer')], validators=[DataRequired()])
    submit = SubmitField('Add Payment')

class OnlineStoreForm(FlaskForm):
    name = StringField("Store Name", validators=[DataRequired()])
    submit = SubmitField("Add Store")    
