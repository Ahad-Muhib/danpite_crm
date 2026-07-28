from django import forms
from django.forms import inlineformset_factory

from clients.models import Client

from .models import BankAccount, Expense, Invoice, InvoiceItem, Payment, CURRENCY_CHOICES


class InvoiceForm(forms.ModelForm):
    client = forms.ModelChoiceField(
        queryset=Client.objects.all().order_by('name'),
        required=False,
        empty_label='— Select Client —',
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_client_select'}),
        label='Client',
    )
    client_name = forms.CharField(
        max_length=200, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'id_client_name', 'placeholder': 'Type client name... (for new clients)'}),
        label='New Client Name',
    )

    class Meta:
        model = Invoice
        fields = [
            'logo', 'currency', 'bill_from', 'phone', 'ship_to',
            'project', 'total', 'tax', 'discount', 'shipping',
            'invoice_date', 'due_date', 'payment_terms', 'po_number',
            'status', 'notes', 'received_payment',
        ]
        widgets = {
            'logo': forms.FileInput(attrs={'class': 'form-control', 'id': 'id_logo', 'accept': 'image/png,image/jpeg,image/webp,image/svg+xml'}),
            'currency': forms.Select(attrs={'class': 'form-select', 'id': 'id_currency'}),
            'bill_from': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Your company\u200b\nAddress\u200b\nEmail / Phone', 'id': 'id_bill_from'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_phone', 'placeholder': 'Phone number'}),
            'ship_to': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Optional shipping address'}),
            'project': forms.TextInput(attrs={'class': 'form-control'}),
            'total': forms.HiddenInput(attrs={'id': 'id_total'}),
            'tax': forms.NumberInput(attrs={'class': 'form-control', 'id': 'id_tax', 'min': '0', 'step': '0.01', 'value': '0'}),
            'discount': forms.NumberInput(attrs={'class': 'form-control', 'id': 'id_discount', 'min': '0', 'step': '0.01', 'value': '0'}),
            'shipping': forms.NumberInput(attrs={'class': 'form-control', 'id': 'id_shipping', 'min': '0', 'step': '0.01', 'value': '0'}),
            'invoice_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'payment_terms': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'NET 30'}),
            'po_number': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Any relevant information not already covered'}),
            'received_payment': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')
        super().__init__(*args, **kwargs)
        if instance and instance.client:
            self.fields['client'].initial = instance.client
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
        for f in ('tax', 'discount', 'shipping', 'total', 'status', 'currency',
                   'phone', 'ship_to', 'project', 'payment_terms', 'po_number', 'notes'):
            self.fields[f].required = False
        self.fields['tax'].initial = 0
        self.fields['discount'].initial = 0
        self.fields['shipping'].initial = 0
        self.fields['total'].initial = 0
        self.fields['status'].initial = 'draft'
        self.fields['currency'].initial = 'USD'
        self.fields['invoice_date'].required = True
        self.fields['bill_from'].required = True


class BaseInvoiceItemFormSet(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()
        for form in self.forms:
            if not form.instance.pk:
                desc = (form.cleaned_data.get('description') or '').strip() if form.cleaned_data else ''
                qty = form.cleaned_data.get('quantity') if form.cleaned_data else None
                rate = form.cleaned_data.get('unit_price') if form.cleaned_data else None
                is_empty = not desc and (qty in (None, 0, 0.0, 1, 1.0)) and (rate in (None, 0, 0.0))
                if is_empty:
                    form._errors = {}


InvoiceItemFormSet = inlineformset_factory(
    Invoice, InvoiceItem,
    formset=BaseInvoiceItemFormSet,
    fields=['description', 'quantity', 'unit_price'],
    extra=3,
    can_delete=True,
    widgets={
        'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Description of item/service...'}),
        'quantity': forms.NumberInput(attrs={'class': 'form-control item-qty', 'min': '0', 'step': 'any'}),
        'unit_price': forms.NumberInput(attrs={'class': 'form-control item-rate', 'min': '0', 'step': '0.01'}),
    }
)


class PaymentForm(forms.ModelForm):
    client_name = forms.CharField(max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Type client name...'}), label='Client')

    class Meta:
        model = Payment
        fields = ['invoice', 'amount', 'payment_date', 'method', 'reference', 'notes']
        widgets = {
            'invoice': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'payment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'method': forms.Select(attrs={'class': 'form-select'}),
            'reference': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')
        super().__init__(*args, **kwargs)
        if instance and instance.client:
            self.fields['client_name'].initial = instance.client.name


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['title', 'category', 'amount', 'expense_date', 'description', 'receipt']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'expense_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'receipt': forms.FileInput(attrs={'class': 'form-control'}),
        }


class BankAccountForm(forms.ModelForm):
    class Meta:
        model = BankAccount
        fields = ['bank_name', 'account_name', 'account_number', 'account_type', 'branch', 'routing_number', 'opening_balance', 'is_active']
        widgets = {
            'bank_name': forms.TextInput(attrs={'class': 'form-control'}),
            'account_name': forms.TextInput(attrs={'class': 'form-control'}),
            'account_number': forms.TextInput(attrs={'class': 'form-control'}),
            'account_type': forms.Select(attrs={'class': 'form-select'}),
            'branch': forms.TextInput(attrs={'class': 'form-control'}),
            'routing_number': forms.TextInput(attrs={'class': 'form-control'}),
            'opening_balance': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
