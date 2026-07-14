from django.contrib.auth.models import User
from django.db import models

from clients.models import Client


class Invoice(models.Model):
    STATUS = [('draft', 'Draft'), ('sent', 'Sent'), ('paid', 'Paid'), ('overdue', 'Overdue'), ('cancelled', 'Cancelled')]
    code = models.CharField(max_length=50, unique=True, blank=True)
    client = models.ForeignKey(Client, null=True, blank=True, on_delete=models.SET_NULL, related_name='invoices')
    project = models.CharField(max_length=200, blank=True)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    invoice_date = models.DateField()
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default='draft')
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.code

    def save(self, *args, **kwargs):
        if not self.code:
            last = Invoice.objects.order_by('id').last()
            self.code = f"INV-{(last.id + 1 if last else 1):04d}"
        super().save(*args, **kwargs)


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    description = models.CharField(max_length=300)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        self.total = self.quantity * self.unit_price
        super().save(*args, **kwargs)


class Payment(models.Model):
    METHOD = [('cash', 'Cash'), ('bank_transfer', 'Bank Transfer'), ('cheque', 'Cheque'), ('card', 'Card'), ('online', 'Online')]
    invoice = models.ForeignKey(Invoice, null=True, blank=True, on_delete=models.SET_NULL, related_name='payments')
    client = models.ForeignKey(Client, null=True, blank=True, on_delete=models.SET_NULL, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateField()
    method = models.CharField(max_length=20, choices=METHOD, default='cash')
    reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.amount} - {self.payment_date}"


class Expense(models.Model):
    CATEGORY = [('office', 'Office Supplies'), ('travel', 'Travel'), ('marketing', 'Marketing'), ('utilities', 'Utilities'), ('salary', 'Salary'), ('rent', 'Rent'), ('equipment', 'Equipment'), ('other', 'Other')]
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=30, choices=CATEGORY, default='other')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    expense_date = models.DateField()
    description = models.TextField(blank=True)
    receipt = models.FileField(upload_to='receipts/', null=True, blank=True)
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class BankAccount(models.Model):
    TYPES = [('savings', 'Savings'), ('current', 'Current'), ('fixed', 'Fixed Deposit'), ('other', 'Other')]
    bank_name = models.CharField(max_length=200)
    account_name = models.CharField(max_length=200)
    account_number = models.CharField(max_length=100)
    account_type = models.CharField(max_length=20, choices=TYPES, default='current')
    branch = models.CharField(max_length=200, blank=True)
    routing_number = models.CharField(max_length=100, blank=True)
    opening_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.bank_name} - {self.account_number}"
