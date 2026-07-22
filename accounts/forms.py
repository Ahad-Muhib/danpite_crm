from django import forms
from django.forms import inlineformset_factory

from clients.models import Client

from .models import BankAccount, Expense, Invoice, InvoiceItem, Payment


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
        fields = ['phone', 'project', 'total', 'tax', 'discount', 'invoice_date', 'due_date', 'status', 'notes', 'received_payment']
        widgets = {
            'phone': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_phone', 'placeholder': 'Phone number'}),
            'project': forms.TextInput(attrs={'class': 'form-control'}),
            'total': forms.NumberInput(attrs={'class': 'form-control'}),
            'tax': forms.NumberInput(attrs={'class': 'form-control'}),
            'discount': forms.NumberInput(attrs={'class': 'form-control'}),
            'invoice_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'received_payment': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')
        super().__init__(*args, **kwargs)
        if instance and instance.client:
            self.fields['client'].initial = instance.client


InvoiceItemFormSet = inlineformset_factory(
    Invoice, InvoiceItem,
    fields=['description', 'quantity', 'unit_price', 'total'],
    extra=1,
    can_delete=True,
    widgets={
        'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Item description'}),
        'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
        'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
        'total': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
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
