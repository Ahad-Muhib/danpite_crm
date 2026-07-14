from django.contrib import admin
from .models import (Task, Project, Schedule, LeadContact, Deal, Client,
                     Department, Designation, Employee, Leave, Attendance,
                     Invoice, InvoiceItem, Payment, Expense, BankAccount,
                     Order, OrderItem)

class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'priority', 'status', 'assigned_to', 'due_date']
    list_filter  = ['priority', 'status']
    search_fields = ['title']

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'status', 'manager', 'start_date', 'end_date']
    list_filter  = ['status']

@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ['title', 'start_datetime', 'end_datetime', 'location']

@admin.register(LeadContact)
class LeadContactAdmin(admin.ModelAdmin):
    list_display  = ['name', 'email', 'company', 'lead_source', 'is_converted']
    list_filter   = ['lead_source', 'is_converted']
    search_fields = ['name', 'email', 'company']

@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    list_display = ['deal_name', 'lead_contact', 'stage', 'value', 'close_date']
    list_filter  = ['pipeline', 'stage']

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display  = ['name', 'email', 'mobile', 'category', 'status']
    list_filter   = ['category', 'status']
    search_fields = ['name', 'email', 'company']

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name']

@admin.register(Designation)
class DesignationAdmin(admin.ModelAdmin):
    list_display = ['title', 'department']

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display  = ['employee_id', 'name', 'email', 'role', 'designation', 'status']
    list_filter   = ['role', 'status']
    search_fields = ['name', 'email', 'employee_id']

@admin.register(Leave)
class LeaveAdmin(admin.ModelAdmin):
    list_display = ['employee', 'leave_type', 'start_date', 'end_date', 'status']
    list_filter  = ['leave_type', 'status']

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['employee', 'date', 'check_in', 'check_out', 'status']
    list_filter  = ['status']

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['code', 'client', 'total', 'invoice_date', 'status']
    list_filter  = ['status']
    inlines      = [InvoiceItemInline]

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['invoice', 'client', 'amount', 'payment_date', 'method']

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display  = ['title', 'category', 'amount', 'expense_date']
    list_filter   = ['category']
    search_fields = ['title']

@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ['bank_name', 'account_name', 'account_number', 'is_active']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'client', 'total', 'status', 'order_date']
    list_filter  = ['status']
    inlines      = [OrderItemInline]
