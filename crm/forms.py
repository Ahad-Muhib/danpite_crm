from django import forms
from .models import (Task, Project, Schedule, LeadContact, Deal, Client,
                     Department, Designation, Employee, Leave, Attendance,
                     Invoice, InvoiceItem, Payment, Expense, BankAccount,
                     Order, OrderItem)

class TaskForm(forms.ModelForm):
    class Meta:
        model  = Task
        fields = ['title','description','priority','status','assigned_to','due_date']
        widgets = {
            'title':       forms.TextInput(attrs={'class':'form-control'}),
            'description': forms.Textarea(attrs={'class':'form-control','rows':3}),
            'priority':    forms.Select(attrs={'class':'form-select'}),
            'status':      forms.Select(attrs={'class':'form-select'}),
            'assigned_to': forms.Select(attrs={'class':'form-select'}),
            'due_date':    forms.DateInput(attrs={'class':'form-control','type':'date'}),
        }

class ProjectForm(forms.ModelForm):
    class Meta:
        model  = Project
        fields = ['name','description','status','start_date','end_date','manager']
        widgets = {
            'name':        forms.TextInput(attrs={'class':'form-control'}),
            'description': forms.Textarea(attrs={'class':'form-control','rows':3}),
            'status':      forms.Select(attrs={'class':'form-select'}),
            'start_date':  forms.DateInput(attrs={'class':'form-control','type':'date'}),
            'end_date':    forms.DateInput(attrs={'class':'form-control','type':'date'}),
            'manager':     forms.Select(attrs={'class':'form-select'}),
        }

class ScheduleForm(forms.ModelForm):
    class Meta:
        model  = Schedule
        fields = ['title','description','start_datetime','end_datetime','location']
        widgets = {
            'title':          forms.TextInput(attrs={'class':'form-control'}),
            'description':    forms.Textarea(attrs={'class':'form-control','rows':3}),
            'start_datetime': forms.DateTimeInput(attrs={'class':'form-control','type':'datetime-local'}),
            'end_datetime':   forms.DateTimeInput(attrs={'class':'form-control','type':'datetime-local'}),
            'location':       forms.TextInput(attrs={'class':'form-control'}),
        }

class LeadContactForm(forms.ModelForm):
    class Meta:
        model  = LeadContact
        fields = ['salutation','name','email','phone','company','website','address','lead_source','lead_owner','notes']
        widgets = {
            'salutation':  forms.Select(attrs={'class':'form-select'}, choices=[('','--'),('Mr.','Mr.'),('Ms.','Ms.'),('Mrs.','Mrs.'),('Dr.','Dr.')]),
            'name':        forms.TextInput(attrs={'class':'form-control'}),
            'email':       forms.EmailInput(attrs={'class':'form-control'}),
            'phone':       forms.TextInput(attrs={'class':'form-control'}),
            'company':     forms.TextInput(attrs={'class':'form-control'}),
            'website':     forms.URLInput(attrs={'class':'form-control'}),
            'address':     forms.Textarea(attrs={'class':'form-control','rows':2}),
            'lead_source': forms.Select(attrs={'class':'form-select'}),
            'lead_owner':  forms.Select(attrs={'class':'form-select'}),
            'notes':       forms.Textarea(attrs={'class':'form-control','rows':3}),
        }

class DealForm(forms.ModelForm):
    class Meta:
        model  = Deal
        fields = ['deal_name','lead_contact','pipeline','stage','value','currency','close_date','deal_agent','description']
        widgets = {
            'deal_name':    forms.TextInput(attrs={'class':'form-control'}),
            'lead_contact': forms.Select(attrs={'class':'form-select'}),
            'pipeline':     forms.Select(attrs={'class':'form-select'}),
            'stage':        forms.Select(attrs={'class':'form-select'}),
            'value':        forms.NumberInput(attrs={'class':'form-control'}),
            'currency':     forms.TextInput(attrs={'class':'form-control'}),
            'close_date':   forms.DateInput(attrs={'class':'form-control','type':'date'}),
            'deal_agent':   forms.Select(attrs={'class':'form-select'}),
            'description':  forms.Textarea(attrs={'class':'form-control','rows':3}),
        }

class ClientForm(forms.ModelForm):
    class Meta:
        model  = Client
        fields = ['name','email','phone','mobile','company','website','address','category','sub_category','status','account_manager','notes']
        widgets = {
            'name':            forms.TextInput(attrs={'class':'form-control'}),
            'email':           forms.EmailInput(attrs={'class':'form-control'}),
            'phone':           forms.TextInput(attrs={'class':'form-control'}),
            'mobile':          forms.TextInput(attrs={'class':'form-control'}),
            'company':         forms.TextInput(attrs={'class':'form-control'}),
            'website':         forms.URLInput(attrs={'class':'form-control'}),
            'address':         forms.Textarea(attrs={'class':'form-control','rows':2}),
            'category':        forms.Select(attrs={'class':'form-select'}),
            'sub_category':    forms.TextInput(attrs={'class':'form-control'}),
            'status':          forms.Select(attrs={'class':'form-select'}),
            'account_manager': forms.Select(attrs={'class':'form-select'}),
            'notes':           forms.Textarea(attrs={'class':'form-control','rows':3}),
        }

class EmployeeForm(forms.ModelForm):
    class Meta:
        model  = Employee
        fields = ['name','email','phone','role','designation','department','reporting_to','status','joining_date','salary','address','avatar','is_new_hire']
        widgets = {
            'name':         forms.TextInput(attrs={'class':'form-control'}),
            'email':        forms.EmailInput(attrs={'class':'form-control'}),
            'phone':        forms.TextInput(attrs={'class':'form-control'}),
            'role':         forms.Select(attrs={'class':'form-select'}),
            'designation':  forms.Select(attrs={'class':'form-select'}),
            'department':   forms.Select(attrs={'class':'form-select'}),
            'reporting_to': forms.Select(attrs={'class':'form-select'}),
            'status':       forms.Select(attrs={'class':'form-select'}),
            'joining_date': forms.DateInput(attrs={'class':'form-control','type':'date'}),
            'salary':       forms.NumberInput(attrs={'class':'form-control'}),
            'address':      forms.Textarea(attrs={'class':'form-control','rows':2}),
            'avatar':       forms.FileInput(attrs={'class':'form-control'}),
            'is_new_hire':  forms.CheckboxInput(attrs={'class':'form-check-input'}),
        }

class LeaveForm(forms.ModelForm):
    class Meta:
        model  = Leave
        fields = ['employee','leave_type','start_date','end_date','reason']
        widgets = {
            'employee':   forms.Select(attrs={'class':'form-select'}),
            'leave_type': forms.Select(attrs={'class':'form-select'}),
            'start_date': forms.DateInput(attrs={'class':'form-control','type':'date'}),
            'end_date':   forms.DateInput(attrs={'class':'form-control','type':'date'}),
            'reason':     forms.Textarea(attrs={'class':'form-control','rows':3}),
        }

class AttendanceForm(forms.ModelForm):
    class Meta:
        model  = Attendance
        fields = ['employee','date','check_in','check_out','status','notes']
        widgets = {
            'employee':  forms.Select(attrs={'class':'form-select'}),
            'date':      forms.DateInput(attrs={'class':'form-control','type':'date'}),
            'check_in':  forms.TimeInput(attrs={'class':'form-control','type':'time'}),
            'check_out': forms.TimeInput(attrs={'class':'form-control','type':'time'}),
            'status':    forms.Select(attrs={'class':'form-select'}),
            'notes':     forms.Textarea(attrs={'class':'form-control','rows':2}),
        }

class InvoiceForm(forms.ModelForm):
    class Meta:
        model  = Invoice
        fields = ['client','project','total','tax','discount','invoice_date','due_date','status','notes']
        widgets = {
            'client':       forms.Select(attrs={'class':'form-select'}),
            'project':      forms.TextInput(attrs={'class':'form-control'}),
            'total':        forms.NumberInput(attrs={'class':'form-control'}),
            'tax':          forms.NumberInput(attrs={'class':'form-control'}),
            'discount':     forms.NumberInput(attrs={'class':'form-control'}),
            'invoice_date': forms.DateInput(attrs={'class':'form-control','type':'date'}),
            'due_date':     forms.DateInput(attrs={'class':'form-control','type':'date'}),
            'status':       forms.Select(attrs={'class':'form-select'}),
            'notes':        forms.Textarea(attrs={'class':'form-control','rows':3}),
        }

class PaymentForm(forms.ModelForm):
    class Meta:
        model  = Payment
        fields = ['invoice','client','amount','payment_date','method','reference','notes']
        widgets = {
            'invoice':      forms.Select(attrs={'class':'form-select'}),
            'client':       forms.Select(attrs={'class':'form-select'}),
            'amount':       forms.NumberInput(attrs={'class':'form-control'}),
            'payment_date': forms.DateInput(attrs={'class':'form-control','type':'date'}),
            'method':       forms.Select(attrs={'class':'form-select'}),
            'reference':    forms.TextInput(attrs={'class':'form-control'}),
            'notes':        forms.Textarea(attrs={'class':'form-control','rows':3}),
        }

class ExpenseForm(forms.ModelForm):
    class Meta:
        model  = Expense
        fields = ['title','category','amount','expense_date','description','receipt']
        widgets = {
            'title':        forms.TextInput(attrs={'class':'form-control'}),
            'category':     forms.Select(attrs={'class':'form-select'}),
            'amount':       forms.NumberInput(attrs={'class':'form-control'}),
            'expense_date': forms.DateInput(attrs={'class':'form-control','type':'date'}),
            'description':  forms.Textarea(attrs={'class':'form-control','rows':3}),
            'receipt':      forms.FileInput(attrs={'class':'form-control'}),
        }

class BankAccountForm(forms.ModelForm):
    class Meta:
        model  = BankAccount
        fields = ['bank_name','account_name','account_number','account_type','branch','routing_number','opening_balance','is_active']
        widgets = {
            'bank_name':       forms.TextInput(attrs={'class':'form-control'}),
            'account_name':    forms.TextInput(attrs={'class':'form-control'}),
            'account_number':  forms.TextInput(attrs={'class':'form-control'}),
            'account_type':    forms.Select(attrs={'class':'form-select'}),
            'branch':          forms.TextInput(attrs={'class':'form-control'}),
            'routing_number':  forms.TextInput(attrs={'class':'form-control'}),
            'opening_balance': forms.NumberInput(attrs={'class':'form-control'}),
            'is_active':       forms.CheckboxInput(attrs={'class':'form-check-input'}),
        }

class OrderForm(forms.ModelForm):
    class Meta:
        model  = Order
        fields = ['client','status','total','delivery_date','notes']
        widgets = {
            'client':        forms.Select(attrs={'class':'form-select'}),
            'status':        forms.Select(attrs={'class':'form-select'}),
            'total':         forms.NumberInput(attrs={'class':'form-control'}),
            'delivery_date': forms.DateInput(attrs={'class':'form-control','type':'date'}),
            'notes':         forms.Textarea(attrs={'class':'form-control','rows':3}),
        }
