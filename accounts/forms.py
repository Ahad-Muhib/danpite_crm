from datetime import date

from django import forms
from django.forms import inlineformset_factory

from clients.models import Client

from .models import (AccountCategory, BankAccount, Expense, ExpenseCategory, Invoice, InvoiceItem, Payment, Transfer, Quotation,
                     CURRENCY_CHOICES, METHOD_CHOICES, CATEGORY_KEY_MAP)


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
                'min': '0', 'step': '0.01', 'readonly': 'readonly',
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
        fields = ['invoice', 'account', 'amount', 'payment_date', 'method', 'reference', 'notes', 'receipt']
        widgets = {
            'invoice': forms.HiddenInput(attrs={'id': 'id_invoice'}),
            'account': forms.HiddenInput(attrs={'id': 'id_account'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'min': '0.01', 'step': '0.01'}),
            'payment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'method': forms.Select(attrs={'class': 'form-select', 'id': 'id_method'}),
            'reference': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Transaction ID / Ref'}),
            'notes': forms.HiddenInput(attrs={'id': 'id_notes'}),
            'receipt': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, method_choices=None, **kwargs):
        instance = kwargs.get('instance')
        super().__init__(*args, **kwargs)
        if instance and instance.client:
            self.fields['client_name'].initial = instance.client.name
        if method_choices is None:
            cats = AccountCategory.objects.filter(is_active=True).values_list('name', flat=True)
            method_choices = [('', '-- Select Method --')] + [(c.lower(), c) for c in cats]
        else:
            method_choices = [('', '-- Select Method --')] + list(method_choices)
        self.fields['method'] = forms.CharField(
            widget=forms.Select(choices=method_choices, attrs={'class': 'form-select', 'id': 'id_method'}),
            required=False,
        )
        if instance and instance.method:
            existing = instance.method.lower()
            if existing not in [c[0] for c in method_choices]:
                method_choices.append((existing, instance.method))
                self.fields['method'].widget.choices = method_choices
            self.fields['method'].initial = existing

    def _get_validation_exclusions(self):
        exclude = super()._get_validation_exclusions()
        exclude.add('method')
        return exclude

    def clean(self):
        cleaned = super().clean()
        method = (cleaned.get('method') or '').strip().lower()
        account = cleaned.get('account')
        amount = cleaned.get('amount')
        invoice = cleaned.get('invoice')
        if amount is None or amount <= 0:
            self.add_error('amount', 'Amount must be greater than 0.')
        if not method:
            self.add_error('method', 'Select a payment method.')
        if method == 'cash':
            cash_acct = BankAccount.objects.filter(is_active=True, account_category__account_type='cash').first()
            if cash_acct:
                cleaned['account'] = cash_acct
                account = cash_acct
        elif not account:
            self.add_error('account', 'Select the account from the bank accounts page for this payment method.')
        if invoice and amount and amount > 0:
            from django.db.models import Sum
            current_paid = invoice.payments.aggregate(s=Sum('amount'))['s'] or 0
            subtract = 0
            if self.instance.pk and self.instance.invoice_id == invoice.pk:
                subtract = self.instance.amount or 0
            if current_paid - subtract + amount > invoice.total:
                self.add_error('amount', f'This payment would exceed the invoice total ({invoice.total}). Please fix the amount.')
        return cleaned


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['title', 'category', 'method', 'amount', 'expense_date', 'bank_account', 'description', 'receipt']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Expense title...'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'method': forms.Select(attrs={'class': 'form-select', 'id': 'id_method'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'min': '0.01', 'step': '0.01'}),
            'expense_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'bank_account': forms.HiddenInput(attrs={'id': 'id_bank_account'}),
            'description': forms.HiddenInput(attrs={'id': 'id_description'}),
            'receipt': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, method_choices=None, **kwargs):
        instance = kwargs.get('instance')
        super().__init__(*args, **kwargs)
        self.fields['expense_date'].initial = date.today()
        self.fields['description'].label = 'Notes'
        cats = ExpenseCategory.objects.filter(is_active=True).order_by('name')
        choices = []
        seen = set()
        for c in cats:
            key = CATEGORY_KEY_MAP.get(c.name.lower(), c.name.lower())
            if key in seen:
                continue
            choices.append((key, c.name))
            seen.add(key)
        if instance and instance.category:
            existing = instance.category
            if existing not in [k for k, _ in choices]:
                choices.append((existing, instance.get_category_display()))
        if not choices:
            choices = list(Expense.CATEGORY)
        self.fields['category'].choices = choices
        if method_choices is None:
            method_choices = list(METHOD_CHOICES)
        method_choices = [('', '-- Select Method --')] + list(method_choices)
        self.fields['method'] = forms.CharField(
            widget=forms.Select(choices=method_choices, attrs={'class': 'form-select', 'id': 'id_method'}),
            required=False,
        )
        if instance and instance.method:
            existing = instance.method.lower()
            if existing not in [c[0] for c in method_choices]:
                method_choices.append((existing, instance.method))
                self.fields['method'].widget.choices = method_choices
            self.fields['method'].initial = existing

    def clean(self):
        cleaned = super().clean()
        amount = cleaned.get('amount')
        account = cleaned.get('bank_account')
        method = (cleaned.get('method') or '').strip().lower()
        if method == 'cash':
            cash_acct = BankAccount.objects.filter(is_active=True, account_category__account_type='cash').first()
            if cash_acct:
                cleaned['bank_account'] = cash_acct
                account = cash_acct
        elif not account:
            self.add_error('bank_account', 'Select the account this expense is paid from.')
        if amount and account:
            balance = account.available_balance
            if self.instance and self.instance.pk:
                balance += float(self.instance.amount or 0)
            if float(amount) > balance:
                raise forms.ValidationError(f'Insufficient balance in {account.display_name}. Available: {balance:.2f}')
        return cleaned


class BankAccountForm(forms.ModelForm):
    class Meta:
        model = BankAccount
        fields = ['account_category', 'bank_name', 'account_name', 'account_number', 'account_type', 'branch', 'routing_number', 'mobile_number', 'holder_name', 'mobile_type', 'card_number', 'card_holder_name', 'contact_number', 'currency', 'opening_balance', 'details', 'is_active']
        widgets = {
            'account_category': forms.Select(attrs={'class': 'form-select', 'id': 'id_account_category'}),
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
            'card_holder_name': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_card_holder_name'}),
            'contact_number': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_contact_number'}),
            'currency': forms.Select(attrs={'class': 'form-select', 'id': 'id_currency'}, choices=CURRENCY_CHOICES),
            'opening_balance': forms.NumberInput(attrs={'class': 'form-control', 'id': 'id_opening_balance'}),
            'details': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Additional details...'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['account_category'].queryset = AccountCategory.objects.filter(is_active=True)
        self.fields['account_category'].label = 'Account Type'
        self.fields['card_holder_name'].label = 'Card Holder Name'
        self.fields['card_number'].label = 'Card Number'
        self.fields['contact_number'].label = 'Contact Number'
        self.fields['currency'].initial = 'BDT'
        self.fields['account_type'].required = False
        self.fields['mobile_type'].required = False

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get('account_type'):
            cleaned['account_type'] = self.instance.account_type if self.instance and self.instance.account_type else 'current'
        if not cleaned.get('mobile_type'):
            cleaned['mobile_type'] = self.instance.mobile_type if self.instance and self.instance.mobile_type else 'personal'
        return cleaned


class TransferForm(forms.ModelForm):
    from_method = forms.ChoiceField(choices=[], required=True, widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_from_method'}))
    from_bank_name = forms.ChoiceField(choices=[], required=False, widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_from_bank_name'}))
    to_method = forms.ChoiceField(choices=[], required=True, widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_to_method'}))
    to_bank_name = forms.ChoiceField(choices=[], required=False, widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_to_bank_name'}))

    class Meta:
        model = Transfer
        fields = ['from_account', 'to_account', 'amount', 'transfer_date', 'reference', 'description', 'receipt']
        widgets = {
            'from_account': forms.HiddenInput(attrs={'id': 'id_from_account'}),
            'to_account': forms.HiddenInput(attrs={'id': 'id_to_account'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
            'transfer_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'reference': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Transaction ID / Ref'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional notes...'}),
            'receipt': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['transfer_date'].initial = date.today()

        cats = AccountCategory.objects.filter(is_active=True)
        cat_choices = [('', '-- Select Type --')] + [(str(c.pk), c.name) for c in cats]
        self.fields['from_method'].choices = cat_choices
        self.fields['to_method'].choices = cat_choices

        bank_cats = AccountCategory.objects.filter(is_active=True, account_type='bank').values_list('pk', flat=True)
        banks = BankAccount.objects.filter(is_active=True, account_category__in=bank_cats) \
            .values_list('bank_name', flat=True).distinct().order_by('bank_name')
        bank_choices = [('', '-- Select Bank --')] + [(b, b) for b in banks]
        self.fields['from_bank_name'].choices = bank_choices
        self.fields['to_bank_name'].choices = bank_choices
        self.fields['from_account'].required = False
        self.fields['to_account'].required = False

    def clean(self):
        cleaned = super().clean()
        for side in ('from_account', 'to_account'):
            pk = self.data.get(side, '').strip()
            if pk:
                try:
                    obj = BankAccount.objects.get(pk=pk)
                    cleaned[side] = obj
                except BankAccount.DoesNotExist:
                    self.add_error(side, f'Invalid {"source" if side == "from_account" else "destination"} account.')
            else:
                self.add_error(side, f'Please select a {"source" if side == "from_account" else "destination"} account.')
        if not self.errors.get('from_account') and not self.errors.get('to_account') and cleaned.get('from_account') == cleaned.get('to_account'):
            self.add_error('to_account', 'Source and destination accounts must be different.')
        from_acct = cleaned.get('from_account')
        amount = cleaned.get('amount')
        if from_acct and amount and not self.errors.get('from_account'):
            balance = from_acct.available_balance
            if amount > balance:
                self.add_error('amount', f'Insufficient balance in source account. Available: {balance}')
        return cleaned


class QuotationForm(forms.ModelForm):
    client_search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'id': 'id_client_search',
            'placeholder': 'Type to search client by name or company...',
            'autocomplete': 'off',
        })
    )

    class Meta:
        model = Quotation
        fields = [
            'quotation_date', 'valid_days', 'client',
            'company_name', 'contact_person', 'designation', 'contact_number', 'email', 'address',
            'subject', 'intro_letter', 'status', 'currency', 'total_amount',
            'payment_terms', 'delivery_terms', 'terms_conditions',
            'warranty', 'not_included', 'why_danpite',
        ]
        widgets = {
            'client': forms.HiddenInput(attrs={'id': 'id_client_pk'}),
            'quotation_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'valid_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'company_name': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_company_name', 'placeholder': 'Company / Organization name'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_contact_person', 'placeholder': 'Contact person name'}),
            'designation': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_designation', 'placeholder': 'Designation'}),
            'contact_number': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_contact_number', 'placeholder': 'Contact phone / mobile'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'id': 'id_email', 'placeholder': 'Email address'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'id': 'id_address', 'rows': 3, 'placeholder': 'Address'}),
            'subject': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Quotation subject'}),
            'intro_letter': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'currency': forms.Select(attrs={'class': 'form-select'}),
            'total_amount': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
            'payment_terms': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'delivery_terms': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'terms_conditions': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'warranty': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'not_included': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'why_danpite': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.client:
            self.fields['client_search'].initial = self.instance.client.name
        if not self.instance.pk:
            self.fields['quotation_date'].initial = date.today()
            self.fields['valid_days'].initial = 15
            self.fields['status'].initial = 'draft'
            self.fields['currency'].initial = 'BDT'
        for f in self.fields:
            self.fields[f].required = False

    def clean(self):
        cleaned = super().clean()
        client = cleaned.get('client')

        if not client:
            self.add_error('client_search', 'A registered client must be selected from the system. Quotations cannot be created for unlisted or non-client names.')
            return cleaned

        # Validate that organization and contact details match the registered client record
        company_name = (cleaned.get('company_name') or '').strip()
        contact_person = (cleaned.get('contact_person') or '').strip()
        contact_number = (cleaned.get('contact_number') or '').strip()
        email = (cleaned.get('email') or '').strip()

        # Check Company / Organization Name
        expected_company = (client.company or client.name).strip()
        if company_name and expected_company and company_name.lower() != expected_company.lower():
            self.add_error(
                'company_name',
                f"Organization name '{company_name}' does not match registered client company '{expected_company}'. Please edit the client profile in the Clients module first."
            )

        # Check Contact Person
        if contact_person and contact_person.lower() != client.name.strip().lower():
            self.add_error(
                'contact_person',
                f"Contact person '{contact_person}' does not match registered client name '{client.name}'. Please edit the client profile in the Clients module first."
            )

        # Check Contact Number
        valid_phones = [p.strip() for p in [client.phone, client.mobile] if p and p.strip()]
        if contact_number and valid_phones:
            if contact_number not in valid_phones:
                self.add_error(
                    'contact_number',
                    f"Contact number '{contact_number}' is not listed in client profile (Registered: {', '.join(valid_phones)}). Please edit the client profile first."
                )
        elif contact_number and not valid_phones:
            self.add_error(
                'contact_number',
                f"Client '{client.name}' has no registered contact number. Please add phone/mobile to the client profile first."
            )

        # Check Email
        if email and client.email:
            if email.lower() != client.email.strip().lower():
                self.add_error(
                    'email',
                    f"Email '{email}' does not match registered client email '{client.email}'. Please edit the client profile first."
                )
        elif email and not client.email:
            self.add_error(
                'email',
                f"Client '{client.name}' has no registered email. Please add email to the client profile first."
            )

        return cleaned

