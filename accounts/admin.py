from django.contrib import admin

from .models import BankAccount, Expense, Invoice, InvoiceItem, Payment, Transfer


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['code', 'client', 'total', 'invoice_date', 'status']
    list_filter = ['status']
    inlines = [InvoiceItemInline]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['invoice', 'client', 'amount', 'payment_date', 'method']


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'amount', 'expense_date']
    list_filter = ['category']
    search_fields = ['title']


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ['bank_name', 'account_name', 'account_number', 'is_active']


@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    list_display = ['from_account', 'to_account', 'amount', 'transfer_date', 'created_by']
    list_filter = ['transfer_date']
    search_fields = ['from_account__account_name', 'to_account__account_name', 'reference']

