from django.contrib.auth.models import User
from django.db import models

from clients.models import Client


CURRENCY_CHOICES = [
    ('USD', 'USD — $'),
    ('BDT', 'BDT — ৳'),
    ('EUR', 'EUR — €'),
    ('GBP', 'GBP — £'),
    ('INR', 'INR — ₹'),
    ('JPY', 'JPY — ¥'),
    ('CAD', 'CAD — C$'),
    ('AUD', 'AUD — A$'),
    ('AED', 'AED — د.إ'),
    ('SAR', 'SAR — ر.س'),
]

CURRENCY_SYMBOLS = {
    'USD': '$', 'BDT': '৳', 'EUR': '€', 'GBP': '£',
    'INR': '₹', 'JPY': '¥', 'CAD': 'C$', 'AUD': 'A$',
    'AED': 'د.إ', 'SAR': 'ر.س',
}


class Invoice(models.Model):
    STATUS = [('draft', 'Draft'), ('sent', 'Sent'), ('paid', 'Paid'), ('overdue', 'Overdue'), ('cancelled', 'Cancelled')]
    code = models.CharField(max_length=50, unique=True, blank=True)
    logo = models.ImageField(upload_to='invoice_logos/', null=True, blank=True)
    currency = models.CharField(max_length=5, choices=CURRENCY_CHOICES, default='BDT')
    bill_from_company = models.CharField(max_length=200, blank=True)
    bill_from_address = models.TextField(blank=True)
    bill_from_phone = models.CharField(max_length=30, blank=True)
    bill_to_name = models.CharField(max_length=200, blank=True)
    client = models.ForeignKey(Client, null=True, blank=True, on_delete=models.SET_NULL, related_name='invoices')
    phone = models.CharField(max_length=30, blank=True)
    ship_to = models.TextField(blank=True)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    shipping = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    invoice_date = models.DateField(null=True, blank=True)
    delivery_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default='draft')
    received_payment = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    terms = models.TextField(blank=True)
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.code

    def save(self, *args, **kwargs):
        if not self.code:
            last = Invoice.objects.order_by('id').last()
            self.code = f"INV-{(last.id + 1 if last else 1):04d}"
        super().save(*args, **kwargs)

    @property
    def balance_due(self):
        from django.db.models import Sum
        total_paid = self.payments.aggregate(s=Sum('amount'))['s'] or 0
        return self.total - total_paid

    @property
    def is_fully_paid(self):
        return self.balance_due <= 0


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    description = models.CharField(max_length=300)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        self.total = self.quantity * self.unit_price
        super().save(*args, **kwargs)


class BankAccount(models.Model):
    CATEGORY = [
        ('bank', 'Bank Transfer'),
        ('bkash', 'bKash'),
        ('nagad', 'Nagad'),
        ('rocket', 'Rocket'),
        ('card', 'Card'),
    ]
    TYPES = [('savings', 'Savings'), ('current', 'Current'), ('fixed', 'Fixed Deposit'), ('other', 'Other')]
    MOBILE_TYPES = [('personal', 'Personal'), ('agent', 'Agent')]
    CARD_TYPES = [('credit', 'Credit'), ('debit', 'Debit')]

    category = models.CharField(max_length=10, choices=CATEGORY, default='bank')

    # Bank
    bank_name = models.CharField(max_length=200, blank=True)
    account_name = models.CharField(max_length=200, blank=True)
    account_number = models.CharField(max_length=100, blank=True)
    account_type = models.CharField(max_length=20, choices=TYPES, default='current')
    branch = models.CharField(max_length=200, blank=True)
    routing_number = models.CharField(max_length=100, blank=True)

    # Mobile (bkash/nagad/rocket)
    mobile_number = models.CharField(max_length=50, blank=True)
    holder_name = models.CharField(max_length=200, blank=True)
    mobile_type = models.CharField(max_length=10, choices=MOBILE_TYPES, default='personal')

    # Card
    card_number = models.CharField(max_length=50, blank=True)
    card_holder = models.CharField(max_length=200, blank=True)
    card_type = models.CharField(max_length=10, choices=CARD_TYPES, default='debit')
    card_bank = models.CharField(max_length=200, blank=True)

    # Common
    opening_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    details = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def available_balance(self):
        from django.db.models import Sum
        total_payments = self.payments.aggregate(s=Sum('amount'))['s'] or 0
        total_expenses = self.expenses.aggregate(s=Sum('amount'))['s'] or 0
        return self.opening_balance + total_payments - total_expenses

    @property
    def display_name(self):
        if self.category == 'bank':
            parts = [p for p in [self.bank_name, self.account_name, self.account_number] if p]
            return ' - '.join(parts) if parts else 'Bank Account'
        elif self.category in ('bkash', 'nagad', 'rocket'):
            return f"{self.get_category_display()} - {self.mobile_number or '(no number)'}"
        elif self.category == 'card':
            return f"Card - {self.card_number or '(no number)'}"
        return self.get_category_display()

    def __str__(self):
        return self.display_name


class ExpenseCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Expense(models.Model):
    CATEGORY = [('office', 'Office Supplies'), ('travel', 'Travel'), ('marketing', 'Marketing'), ('utilities', 'Utilities'), ('salary', 'Salary'), ('rent', 'Rent'), ('equipment', 'Equipment'), ('other', 'Other')]
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=30, choices=CATEGORY, default='other')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    expense_date = models.DateField()
    bank_account = models.ForeignKey('BankAccount', null=True, blank=True, on_delete=models.SET_NULL, related_name='expenses')
    description = models.TextField(blank=True)
    receipt = models.FileField(upload_to='receipts/', null=True, blank=True)
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Payment(models.Model):
    METHOD = [('cash', 'Cash'), ('bank_transfer', 'Bank Transfer'), ('cheque', 'Cheque'), ('card', 'Card'), ('online', 'Online'), ('bkash', 'bKash'), ('nagad', 'Nagad'), ('rocket', 'Rocket')]
    invoice = models.ForeignKey(Invoice, null=True, blank=True, on_delete=models.SET_NULL, related_name='payments')
    client = models.ForeignKey(Client, null=True, blank=True, on_delete=models.SET_NULL, related_name='payments')
    account = models.ForeignKey('BankAccount', null=True, blank=True, on_delete=models.SET_NULL, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateField()
    method = models.CharField(max_length=20, choices=METHOD, default='cash')
    reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.amount} - {self.payment_date}"
