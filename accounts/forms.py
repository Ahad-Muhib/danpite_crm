from datetime import date

from django import forms
from django.forms import inlineformset_factory

from clients.models import Client

from .models import BankAccount, Expense, ExpenseCategory, Invoice, InvoiceItem, Payment, CURRENCY_CHOICES


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = [
            'currency', 'bill_to_name', 'phone', 'ship_to',
            'total', 'tax', 'discount', 'shipping',
            'invoice_date', 'delivery_date',
            'status', 'notes', 'terms', 'received_payment',
        ]
        widgets = {
            'currency': forms.Select(attrs={'class': 'form-select', 'id': 'id_currency'}),
            'bill_to_name': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_bill_to_name', 'placeholder': 'Type client name...'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_phone', 'placeholder': 'Phone number'}),
            'ship_to': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Optional shipping address'}),
            'total': forms.HiddenInput(attrs={'id': 'id_total'}),
            'tax': forms.NumberInput(attrs={'class': 'form-control', 'id': 'id_tax', 'min': '0', 'step': '0.01', 'value': '0'}),
            'discount': forms.NumberInput(attrs={'class': 'form-control', 'id': 'id_discount', 'min': '0', 'step': '0.01', 'value': '0'}),
            'shipping': forms.NumberInput(attrs={'class': 'form-control', 'id': 'id_shipping', 'min': '0', 'step': '0.01', 'value': '0'}),
            'invoice_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'id': 'id_invoice_date'}),
            'delivery_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'id': 'id_delivery_date'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.HiddenInput(attrs={'id': 'id_notes'}),
            'terms': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_terms', 'placeholder': 'Terms and conditions...', 'list': 'terms-list', 'style': 'border:1px solid #d1d5db;border-radius:4px;padding:7px 8px;font:inherit;font-size:13px;width:100%;'}),
            'received_payment': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')
        super().__init__(*args, **kwargs)
        self.fields['amount_paid'] = forms.DecimalField(
            max_digits=12, decimal_places=2, required=False, initial=0,
            widget=forms.NumberInput(attrs={
                'class': 'form-control', 'id': 'id_amount_paid',
                'min': '0', 'step': '0.01', 'style': 'text-align:right',
            }),
            label='Amount Paid',
        )
        if instance:
            from django.db.models import Sum
            paid = instance.payments.aggregate(s=Sum('amount'))['s'] or 0
            self.fields['amount_paid'].initial = paid
        for f in self.fields:
            self.fields[f].required = False
        self.fields['tax'].initial = 0
        self.fields['discount'].initial = 0
        self.fields['shipping'].initial = 0
        self.fields['total'].initial = 0
        self.fields['status'].initial = 'draft'
        self.fields['currency'].initial = 'BDT'
        self.fields['invoice_date'].initial = date.today()
        self.fields['terms'].initial = 'Each payment are non refundable at any circumstance'


class BaseInvoiceItemForm(forms.ModelForm):
    class Meta:
        model = InvoiceItem
        fields = ['description', 'quantity', 'unit_price']
        widgets = {
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Description of item/service...'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control item-qty', 'min': '0', 'step': 'any'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control item-rate', 'min': '0', 'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields:
            self.fields[f].required = False


class BaseInvoiceItemFormSet(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()
        for form in self.forms:
            if not form.instance or not form.instance.pk:
                desc = (form.cleaned_data.get('description') or '').strip() if form.cleaned_data else ''
                qty = form.cleaned_data.get('quantity') if form.cleaned_data else None
                rate = form.cleaned_data.get('unit_price') if form.cleaned_data else None
                is_empty = not desc and (qty in (None, 0, 0.0, 1, 1.0)) and (rate in (None, 0, 0.0))
                if is_empty:
                    form._errors = {}


InvoiceItemFormSet = inlineformset_factory(
    Invoice, InvoiceItem,
    formset=BaseInvoiceItemFormSet,
    form=BaseInvoiceItemForm,
    fields=['description', 'quantity', 'unit_price'],
    extra=1,
    can_delete=True,
)


class PaymentForm(forms.ModelForm):
    client_name = forms.CharField(max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'id_client_name', 'placeholder': 'Type client name...', 'autocomplete': 'off'}), label='Client')

    class Meta:
        model = Payment
        fields = ['invoice', 'account', 'amount', 'payment_date', 'method', 'reference', 'notes']
        widgets = {
            'invoice': forms.HiddenInput(attrs={'id': 'id_invoice'}),
            'account': forms.HiddenInput(attrs={'id': 'id_account'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01', 'style': 'text-align:right'}),
            'payment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'method': forms.Select(attrs={'class': 'form-select', 'id': 'id_method'}),
            'reference': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Transaction ID / Ref'}),
            'notes': forms.HiddenInput(attrs={'id': 'id_notes'}),
        }

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')
        super().__init__(*args, **kwargs)
        if instance and instance.client:
            self.fields['client_name'].initial = instance.client.name
        self.fields['payment_date'].initial = date.today()


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['title', 'category', 'amount', 'expense_date', 'bank_account', 'description', 'receipt']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Expense title...'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01', 'style': 'text-align:right'}),
            'expense_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'bank_account': forms.HiddenInput(attrs={'id': 'id_bank_account'}),
            'description': forms.HiddenInput(attrs={'id': 'id_description'}),
            'receipt': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['expense_date'].initial = date.today()
        self.fields['description'].label = 'Notes'
        cats = ExpenseCategory.objects.all()
        if cats:
            self.fields['category'].choices = [(c.name, c.name) for c in cats]


class BankAccountForm(forms.ModelForm):
    class Meta:
        model = BankAccount
        fields = ['category', 'bank_name', 'account_name', 'account_number', 'account_type', 'branch', 'routing_number', 'mobile_number', 'holder_name', 'mobile_type', 'card_number', 'card_holder', 'card_type', 'card_bank', 'opening_balance', 'details', 'is_active']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select', 'id': 'id_category'}),
            'bank_name': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_bank_name'}),
            'account_name': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_account_name'}),
            'account_number': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_account_number'}),
            'account_type': forms.Select(attrs={'class': 'form-select', 'id': 'id_account_type'}),
            'branch': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_branch'}),
            'routing_number': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_routing_number'}),
            'mobile_number': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_mobile_number'}),
            'holder_name': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_holder_name'}),
            'mobile_type': forms.Select(attrs={'class': 'form-select', 'id': 'id_mobile_type'}),
            'card_number': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_card_number'}),
            'card_holder': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_card_holder'}),
            'card_type': forms.Select(attrs={'class': 'form-select', 'id': 'id_card_type'}),
            'card_bank': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_card_bank'}),
            'opening_balance': forms.NumberInput(attrs={'class': 'form-control', 'id': 'id_opening_balance'}),
            'details': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Additional details...'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
