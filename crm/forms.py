from django import forms

from .models import AccountEntry, Client, Expense, Invoice, Payment, StaffProfile


class StaffProfileForm(forms.ModelForm):
    username = forms.CharField(max_length=150)
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField(required=False)
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = StaffProfile
        fields = ["username", "first_name", "last_name", "email", "password", "phone", "job_title", "is_active"]


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ["name", "company", "email", "phone", "address"]


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ["client", "invoice_number", "issue_date", "due_date", "status", "subtotal", "tax", "notes"]
        widgets = {
            "issue_date": forms.DateInput(attrs={"type": "date"}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
        }


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ["invoice", "amount", "paid_on", "method", "reference"]
        widgets = {"paid_on": forms.DateInput(attrs={"type": "date"})}


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ["date", "title", "category", "amount", "notes"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}


class AccountEntryForm(forms.ModelForm):
    class Meta:
        model = AccountEntry
        fields = ["date", "entry_type", "title", "amount", "description"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}
