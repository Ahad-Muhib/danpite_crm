from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum
from .models import (Task, Project, Schedule, LeadContact, Deal, Client,
                     Department, Designation, Employee, Leave, Attendance,
                     Invoice, Payment, Expense, BankAccount, Order)
from .forms import (TaskForm, ProjectForm, ScheduleForm, LeadContactForm,
                    DealForm, ClientForm, EmployeeForm, LeaveForm,
                    AttendanceForm, InvoiceForm, PaymentForm, ExpenseForm,
                    BankAccountForm, OrderForm)


# ─────────────── DASHBOARD ───────────────
@login_required
def dashboard(request):
    ctx = {
        'task_count':     Task.objects.count(),
        'project_count':  Project.objects.count(),
        'client_count':   Client.objects.count(),
        'lead_count':     LeadContact.objects.filter(is_converted=False).count(),
        'employee_count': Employee.objects.count(),
        'order_count':    Order.objects.count(),
        'recent_tasks':    Task.objects.order_by('-created_at')[:5],
        'recent_projects': Project.objects.order_by('-created_at')[:5],
        'recent_leads':    LeadContact.objects.order_by('-created_at')[:5],
    }
    return render(request, 'dashboard.html', ctx)


# ─────────────── TASKS ───────────────
@login_required
def task_list(request):
    q  = request.GET.get('q','')
    qs = Task.objects.filter(Q(title__icontains=q)) if q else Task.objects.all()
    return render(request, 'crm/tasks.html', {'tasks': qs, 'q': q})

@login_required
def task_create(request):
    form = TaskForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Task created.')
        return redirect('task_list')
    return render(request, 'crm/task_form.html', {'form': form, 'action': 'Create'})

@login_required
def task_edit(request, pk):
    obj  = get_object_or_404(Task, pk=pk)
    form = TaskForm(request.POST or None, instance=obj)
    if form.is_valid():
        form.save()
        messages.success(request, 'Task updated.')
        return redirect('task_list')
    return render(request, 'crm/task_form.html', {'form': form, 'action': 'Edit'})

@login_required
def task_delete(request, pk):
    get_object_or_404(Task, pk=pk).delete()
    messages.success(request, 'Task deleted.')
    return redirect('task_list')


# ─────────────── PROJECTS ───────────────
@login_required
def project_list(request):
    qs = Project.objects.all().order_by('-created_at')
    return render(request, 'crm/projects.html', {'projects': qs})

@login_required
def project_create(request):
    form = ProjectForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Project created.')
        return redirect('project_list')
    return render(request, 'crm/project_form.html', {'form': form, 'action': 'Create'})

@login_required
def project_edit(request, pk):
    obj  = get_object_or_404(Project, pk=pk)
    form = ProjectForm(request.POST or None, instance=obj)
    if form.is_valid():
        form.save()
        messages.success(request, 'Project updated.')
        return redirect('project_list')
    return render(request, 'crm/project_form.html', {'form': form, 'action': 'Edit'})

@login_required
def project_delete(request, pk):
    get_object_or_404(Project, pk=pk).delete()
    messages.success(request, 'Project deleted.')
    return redirect('project_list')


# ─────────────── SCHEDULES ───────────────
@login_required
def schedule_list(request):
    qs = Schedule.objects.all().order_by('-start_datetime')
    return render(request, 'crm/schedules.html', {'schedules': qs})

@login_required
def schedule_create(request):
    form = ScheduleForm(request.POST or None)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.created_by = request.user
        obj.save()
        messages.success(request, 'Schedule created.')
        return redirect('schedule_list')
    return render(request, 'crm/schedule_form.html', {'form': form, 'action': 'Create'})

@login_required
def schedule_edit(request, pk):
    obj  = get_object_or_404(Schedule, pk=pk)
    form = ScheduleForm(request.POST or None, instance=obj)
    if form.is_valid():
        form.save()
        messages.success(request, 'Schedule updated.')
        return redirect('schedule_list')
    return render(request, 'crm/schedule_form.html', {'form': form, 'action': 'Edit'})

@login_required
def schedule_delete(request, pk):
    get_object_or_404(Schedule, pk=pk).delete()
    messages.success(request, 'Schedule deleted.')
    return redirect('schedule_list')


# ─────────────── LEAD CONTACTS ───────────────
@login_required
def lead_list(request):
    q   = request.GET.get('q','')
    src = request.GET.get('source','')
    qs  = LeadContact.objects.all()
    if q:   qs = qs.filter(Q(name__icontains=q)|Q(email__icontains=q)|Q(company__icontains=q))
    if src: qs = qs.filter(lead_source=src)
    return render(request, 'crm/leads.html', {'leads': qs, 'q': q, 'source': src})

@login_required
def lead_create(request):
    form = LeadContactForm(request.POST or None)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.added_by = request.user
        obj.save()
        messages.success(request, 'Lead contact added.')
        return redirect('lead_list')
    return render(request, 'crm/lead_form.html', {'form': form, 'action': 'Add'})

@login_required
def lead_edit(request, pk):
    obj  = get_object_or_404(LeadContact, pk=pk)
    form = LeadContactForm(request.POST or None, instance=obj)
    if form.is_valid():
        form.save()
        messages.success(request, 'Lead updated.')
        return redirect('lead_list')
    return render(request, 'crm/lead_form.html', {'form': form, 'action': 'Edit', 'lead': obj})

@login_required
def lead_detail(request, pk):
    lead  = get_object_or_404(LeadContact, pk=pk)
    deals = lead.deals.all()
    return render(request, 'crm/lead_detail.html', {'lead': lead, 'deals': deals})

@login_required
def lead_delete(request, pk):
    get_object_or_404(LeadContact, pk=pk).delete()
    messages.success(request, 'Lead deleted.')
    return redirect('lead_list')

@login_required
def lead_convert(request, pk):
    lead = get_object_or_404(LeadContact, pk=pk)
    Client.objects.create(
        name=lead.name, email=lead.email, phone=lead.phone,
        company=lead.company, website=lead.website, address=lead.address,
        account_manager=request.user
    )
    lead.is_converted = True
    lead.save()
    messages.success(request, f'{lead.name} converted to client.')
    return redirect('lead_list')


# ─────────────── DEALS ───────────────
@login_required
def deal_list(request):
    qs = Deal.objects.all().order_by('-created_at')
    return render(request, 'crm/deals.html', {'deals': qs})

@login_required
def deal_create(request):
    form = DealForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Deal created.')
        return redirect('deal_list')
    return render(request, 'crm/deal_form.html', {'form': form, 'action': 'Create'})

@login_required
def deal_edit(request, pk):
    obj  = get_object_or_404(Deal, pk=pk)
    form = DealForm(request.POST or None, instance=obj)
    if form.is_valid():
        form.save()
        messages.success(request, 'Deal updated.')
        return redirect('deal_list')
    return render(request, 'crm/deal_form.html', {'form': form, 'action': 'Edit'})

@login_required
def deal_delete(request, pk):
    get_object_or_404(Deal, pk=pk).delete()
    messages.success(request, 'Deal deleted.')
    return redirect('deal_list')


# ─────────────── CLIENTS ───────────────
@login_required
def client_list(request):
    q      = request.GET.get('q','')
    status = request.GET.get('status','')
    qs     = Client.objects.all()
    if q:      qs = qs.filter(Q(name__icontains=q)|Q(email__icontains=q)|Q(company__icontains=q))
    if status: qs = qs.filter(status=status)
    return render(request, 'crm/clients.html', {'clients': qs, 'q': q, 'status': status})

@login_required
def client_create(request):
    form = ClientForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Client added.')
        return redirect('client_list')
    return render(request, 'crm/client_form.html', {'form': form, 'action': 'Add'})

@login_required
def client_edit(request, pk):
    obj  = get_object_or_404(Client, pk=pk)
    form = ClientForm(request.POST or None, instance=obj)
    if form.is_valid():
        form.save()
        messages.success(request, 'Client updated.')
        return redirect('client_list')
    return render(request, 'crm/client_form.html', {'form': form, 'action': 'Edit', 'client': obj})

@login_required
def client_detail(request, pk):
    client   = get_object_or_404(Client, pk=pk)
    invoices = client.invoices.all()[:5]
    orders   = client.orders.all()[:5]
    return render(request, 'crm/client_detail.html', {'client': client, 'invoices': invoices, 'orders': orders})

@login_required
def client_delete(request, pk):
    get_object_or_404(Client, pk=pk).delete()
    messages.success(request, 'Client deleted.')
    return redirect('client_list')


# ─────────────── EMPLOYEES ───────────────
@login_required
def employee_list(request):
    q   = request.GET.get('q','')
    qs  = Employee.objects.all()
    if q: qs = qs.filter(Q(name__icontains=q)|Q(email__icontains=q)|Q(employee_id__icontains=q))
    designations = Designation.objects.all()
    return render(request, 'crm/employees.html', {'employees': qs, 'q': q, 'designations': designations})

@login_required
def employee_create(request):
    form = EmployeeForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Employee added.')
        return redirect('employee_list')
    return render(request, 'crm/employee_form.html', {'form': form, 'action': 'Add'})

@login_required
def employee_edit(request, pk):
    obj  = get_object_or_404(Employee, pk=pk)
    form = EmployeeForm(request.POST or None, request.FILES or None, instance=obj)
    if form.is_valid():
        form.save()
        messages.success(request, 'Employee updated.')
        return redirect('employee_list')
    return render(request, 'crm/employee_form.html', {'form': form, 'action': 'Edit', 'employee': obj})

@login_required
def employee_detail(request, pk):
    emp         = get_object_or_404(Employee, pk=pk)
    leaves      = emp.leaves.all()[:5]
    attendances = emp.attendances.all().order_by('-date')[:10]
    return render(request, 'crm/employee_detail.html', {'employee': emp, 'leaves': leaves, 'attendances': attendances})

@login_required
def employee_delete(request, pk):
    get_object_or_404(Employee, pk=pk).delete()
    messages.success(request, 'Employee deleted.')
    return redirect('employee_list')


# ─────────────── LEAVES ───────────────
@login_required
def leave_list(request):
    qs = Leave.objects.all().order_by('-created_at')
    return render(request, 'crm/leaves.html', {'leaves': qs})

@login_required
def leave_create(request):
    form = LeaveForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Leave application submitted.')
        return redirect('leave_list')
    return render(request, 'crm/leave_form.html', {'form': form})

@login_required
def leave_status(request, pk):
    leave = get_object_or_404(Leave, pk=pk)
    status = request.POST.get('status')
    if status in ['approved','rejected']:
        leave.status = status
        leave.approved_by = request.user
        leave.save()
        messages.success(request, f'Leave {status}.')
    return redirect('leave_list')


# ─────────────── ATTENDANCE ───────────────
@login_required
def attendance_list(request):
    qs = Attendance.objects.all().order_by('-date')
    return render(request, 'crm/attendance.html', {'attendances': qs})

@login_required
def attendance_create(request):
    form = AttendanceForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Attendance recorded.')
        return redirect('attendance_list')
    return render(request, 'crm/attendance_form.html', {'form': form})


# ─────────────── INVOICES ───────────────
@login_required
def invoice_list(request):
    q      = request.GET.get('q','')
    status = request.GET.get('status','')
    qs     = Invoice.objects.all()
    if q:      qs = qs.filter(Q(code__icontains=q))
    if status: qs = qs.filter(status=status)
    return render(request, 'crm/invoices.html', {'invoices': qs, 'q': q, 'status': status})

@login_required
def invoice_create(request):
    form = InvoiceForm(request.POST or None)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.created_by = request.user
        obj.save()
        messages.success(request, 'Invoice created.')
        return redirect('invoice_list')
    return render(request, 'crm/invoice_form.html', {'form': form, 'action': 'Create'})

@login_required
def invoice_edit(request, pk):
    obj  = get_object_or_404(Invoice, pk=pk)
    form = InvoiceForm(request.POST or None, instance=obj)
    if form.is_valid():
        form.save()
        messages.success(request, 'Invoice updated.')
        return redirect('invoice_list')
    return render(request, 'crm/invoice_form.html', {'form': form, 'action': 'Edit'})

@login_required
def invoice_detail(request, pk):
    invoice  = get_object_or_404(Invoice, pk=pk)
    items    = invoice.items.all()
    payments = invoice.payments.all()
    return render(request, 'crm/invoice_detail.html', {'invoice': invoice, 'items': items, 'payments': payments})

@login_required
def invoice_delete(request, pk):
    get_object_or_404(Invoice, pk=pk).delete()
    messages.success(request, 'Invoice deleted.')
    return redirect('invoice_list')


# ─────────────── PAYMENTS ───────────────
@login_required
def payment_list(request):
    qs    = Payment.objects.all().order_by('-payment_date')
    total = qs.aggregate(Sum('amount'))['amount__sum'] or 0
    return render(request, 'crm/payments.html', {'payments': qs, 'total': total})

@login_required
def payment_create(request):
    form = PaymentForm(request.POST or None)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.created_by = request.user
        obj.save()
        messages.success(request, 'Payment recorded.')
        return redirect('payment_list')
    return render(request, 'crm/payment_form.html', {'form': form})

@login_required
def payment_delete(request, pk):
    get_object_or_404(Payment, pk=pk).delete()
    messages.success(request, 'Payment deleted.')
    return redirect('payment_list')


# ─────────────── EXPENSES ───────────────
@login_required
def expense_list(request):
    qs    = Expense.objects.all().order_by('-expense_date')
    total = qs.aggregate(Sum('amount'))['amount__sum'] or 0
    return render(request, 'crm/expenses.html', {'expenses': qs, 'total': total})

@login_required
def expense_create(request):
    form = ExpenseForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.created_by = request.user
        obj.save()
        messages.success(request, 'Expense recorded.')
        return redirect('expense_list')
    return render(request, 'crm/expense_form.html', {'form': form})

@login_required
def expense_delete(request, pk):
    get_object_or_404(Expense, pk=pk).delete()
    messages.success(request, 'Expense deleted.')
    return redirect('expense_list')


# ─────────────── BANK ACCOUNTS ───────────────
@login_required
def bank_account_list(request):
    qs = BankAccount.objects.all()
    return render(request, 'crm/bank_accounts.html', {'accounts': qs})

@login_required
def bank_account_create(request):
    form = BankAccountForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Bank account added.')
        return redirect('bank_account_list')
    return render(request, 'crm/bank_account_form.html', {'form': form})

@login_required
def bank_account_delete(request, pk):
    get_object_or_404(BankAccount, pk=pk).delete()
    messages.success(request, 'Bank account deleted.')
    return redirect('bank_account_list')


# ─────────────── ORDERS ───────────────
@login_required
def order_list(request):
    q      = request.GET.get('q','')
    status = request.GET.get('status','')
    qs     = Order.objects.all()
    if q:      qs = qs.filter(Q(order_number__icontains=q))
    if status: qs = qs.filter(status=status)
    return render(request, 'crm/orders.html', {'orders': qs, 'q': q, 'status': status})

@login_required
def order_create(request):
    form = OrderForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Order created.')
        return redirect('order_list')
    return render(request, 'crm/order_form.html', {'form': form, 'action': 'Create'})

@login_required
def order_edit(request, pk):
    obj  = get_object_or_404(Order, pk=pk)
    form = OrderForm(request.POST or None, instance=obj)
    if form.is_valid():
        form.save()
        messages.success(request, 'Order updated.')
        return redirect('order_list')
    return render(request, 'crm/order_form.html', {'form': form, 'action': 'Edit'})

@login_required
def order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk)
    items = order.items.all()
    return render(request, 'crm/order_detail.html', {'order': order, 'items': items})

@login_required
def order_delete(request, pk):
    get_object_or_404(Order, pk=pk).delete()
    messages.success(request, 'Order deleted.')
    return redirect('order_list')
