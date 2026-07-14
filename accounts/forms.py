from django import forms

from .models import BankAccount, Expense, Invoice, Payment


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ['client', 'project', 'total', 'tax', 'discount', 'invoice_date', 'due_date', 'status', 'notes']
        widgets = {
            'client': forms.Select(attrs={'class': 'form-select'}),
            'project': forms.TextInput(attrs={'class': 'form-control'}),
            'total': forms.NumberInput(attrs={'class': 'form-control'}),
            'tax': forms.NumberInput(attrs={'class': 'form-control'}),
            'discount': forms.NumberInput(attrs={'class': 'form-control'}),
            'invoice_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['invoice', 'client', 'amount', 'payment_date', 'method', 'reference', 'notes']
        widgets = {
            'invoice': forms.Select(attrs={'class': 'form-select'}),
            'client': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'payment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'method': forms.Select(attrs={'class': 'form-select'}),
            'reference': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


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

