from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count, Avg
from django.db.models.functions import TruncMonth
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from functools import wraps

from clients.models import Client
from hr.models import Employee
from leads.models import Deal, LeadContact
from orders.models import Order

from .forms import CurrencySettingsForm, ProjectForm, ScheduleForm, TaskForm
from .models import CurrencySettings, Log, Project, Schedule, SiteSettings, Task, log_action


# ── Role helpers ───────────────────────────────────────────────
# Roles: admin, manager, hr, employee  (from Employee.role choices)
# A User without an Employee record is treated as 'staff' (full access
# for backwards-compatibility with superusers created via createsuperuser).

def get_user_role(user):
    if not user.is_authenticated:
        return None
    if user.is_superuser or user.is_staff:
        return 'admin'
    try:
        return user.employee_profile.role
    except Employee.DoesNotExist:
        return 'staff'


def role_required(*allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped(request, *args, **kwargs):
            role = get_user_role(request.user)
            if role not in allowed_roles:
                return HttpResponseForbidden('You do not have permission to access this page.')
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


def is_admin(user):
    return get_user_role(user) == 'admin'


def is_manager_or_above(user):
    return get_user_role(user) in ('admin', 'manager')


def is_hr_or_above(user):
    return get_user_role(user) in ('admin', 'manager', 'hr')





def superuser_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_superuser:
            messages.error(request, 'Only superusers can perform this action.')
            return redirect(request.META.get('HTTP_REFERER', '/'))
        return view_func(request, *args, **kwargs)
    return _wrapped


@login_required
def dashboard(request):
    # Pipeline stats
    active_deals = Deal.objects.exclude(stage__in=['won', 'lost'])
    pipeline_value = active_deals.aggregate(total=Sum('value'))['total'] or 0
    active_deal_count = active_deals.count()
    total_deals = Deal.objects.count()
    won_deals = Deal.objects.filter(stage='won').count()
    win_rate = round((won_deals / total_deals * 100) if total_deals > 0 else 0, 1)
    avg_deal_value = Deal.objects.aggregate(avg=Avg('value'))['avg'] or 0

    # Pipeline by stage
    pipeline_stages = []
    max_count = 0
    for stage_key, stage_label in Deal.STAGE:
        count = Deal.objects.filter(stage=stage_key).count()
        value = Deal.objects.filter(stage=stage_key).aggregate(v=Sum('value'))['v'] or 0
        pipeline_stages.append((stage_key, stage_label, count, value))
        if count > max_count:
            max_count = count

    # Lead source analytics
    source_stats = []
    total_leads = LeadContact.objects.count() or 1
    source_data = (LeadContact.objects.exclude(lead_source='none')
                   .values('lead_source')
                   .annotate(cnt=Count('id'))
                   .order_by('-cnt'))
    for item in source_data:
        label = LeadContact.SOURCE_LABELS.get(item['lead_source'], item['lead_source'])
        pct = round(item['cnt'] / total_leads * 100, 1)
        source_stats.append((label, item['cnt'], pct))

    ctx = {
        'task_count': Task.objects.count(),
        'project_count': Project.objects.count(),
        'client_count': Client.objects.count(),
        'lead_count': LeadContact.objects.filter(is_converted=False).count(),
        'employee_count': Employee.objects.count(),
        'order_count': Order.objects.count(),
        'recent_tasks': Task.objects.order_by('-created_at')[:5],
        'recent_projects': Project.objects.order_by('-created_at')[:5],
        'recent_leads': LeadContact.objects.order_by('-created_at')[:5],
        'pipeline_value': pipeline_value,
        'active_deal_count': active_deal_count,
        'win_rate': win_rate,
        'avg_deal_value': avg_deal_value,
        'pipeline_stages': pipeline_stages,
        'pipeline_max_count': max_count,
        'source_stats': source_stats,
        'monthly_points': [],
        'latest_payments': [],
        'latest_invoices': [],
        'user_role': get_user_role(request.user),
    }

    # Financial summary
    try:
        from accounts.models import Invoice, Payment, Expense, BankAccount, Transfer
        total_revenue = Payment.objects.aggregate(s=Sum('amount'))['s'] or 0
        total_expenses = Expense.objects.aggregate(s=Sum('amount'))['s'] or 0
        net_balance = total_revenue - total_expenses
        payment_count = Payment.objects.count()

        monthly_payment_rows = (
            Payment.objects.filter(payment_date__isnull=False)
            .annotate(month=TruncMonth('payment_date'))
            .values('month')
            .annotate(total=Sum('amount'))
            .order_by('month')
        )
        monthly_expense_rows = (
            Expense.objects.filter(expense_date__isnull=False)
            .annotate(month=TruncMonth('expense_date'))
            .values('month')
            .annotate(total=Sum('amount'))
            .order_by('month')
        )

        month_map = {}
        for row in monthly_payment_rows:
            month_map[row['month'].date().replace(day=1)] = {
                'revenue': float(row['total'] or 0),
                'expense': 0.0,
            }
        for row in monthly_expense_rows:
            key = row['month'].date().replace(day=1)
            month_map.setdefault(key, {'revenue': 0.0, 'expense': 0.0})
            month_map[key]['expense'] = float(row['total'] or 0)

        monthly_points = []
        for month_key in sorted(month_map.keys())[-12:]:
            monthly_points.append({
                'label': month_key.strftime('%b %Y'),
                'revenue': month_map[month_key]['revenue'],
                'expense': month_map[month_key]['expense'],
            })

        latest_payments = Payment.objects.select_related('client', 'invoice', 'account').order_by('-created_at')[:5]
        latest_invoices = Invoice.objects.select_related('client').order_by('-created_at')[:5]

        ctx.update({
            'total_revenue': total_revenue,
            'total_expenses': total_expenses,
            'net_balance': net_balance,
            'payment_count': payment_count,
            'monthly_points': monthly_points,
            'latest_payments': latest_payments,
            'latest_invoices': latest_invoices,
        })
    except Exception:
        pass

    return render(request, 'dashboard.html', ctx)


# ── Global Search ──────────────────────────────────────────────

@login_required
def global_search(request):
    q = request.GET.get('q', '').strip()
    if not q:
        return redirect('dashboard')

    results = {
        'leads': LeadContact.objects.filter(
            Q(name__icontains=q) | Q(email__icontains=q) | Q(phone__icontains=q) | Q(company__icontains=q)
        )[:10],
        'clients': Client.objects.filter(
            Q(name__icontains=q) | Q(email__icontains=q) | Q(company__icontains=q) | Q(phone__icontains=q)
        )[:10],
        'employees': Employee.objects.filter(
            Q(name__icontains=q) | Q(email__icontains=q) | Q(employee_id__icontains=q) | Q(phone__icontains=q)
        )[:10],
        'tasks': Task.objects.filter(
            Q(title__icontains=q) | Q(description__icontains=q)
        )[:10],
    }

    try:
        from accounts.models import Invoice, Payment, Order
        results['invoices'] = Invoice.objects.filter(
            Q(code__icontains=q) | Q(client_name__icontains=q) | Q(phone__icontains=q)
        )[:10]
        results['payments'] = Payment.objects.filter(
            Q(reference__icontains=q)
        )[:10]
        results['orders'] = Order.objects.filter(
            Q(order_number__icontains=q) | Q(client__name__icontains=q)
        )[:10]
    except Exception:
        pass

    total = sum(len(v) for v in results.values())

    return render(request, 'core/search_results.html', {
        'results': results,
        'q': q,
        'total': total,
    })


# ── User Management (Admin Only) ──────────────────────────────

@login_required
def user_list(request):
    if not is_admin(request.user):
        return HttpResponseForbidden('Only administrators can manage users.')
    from django.contrib.auth.models import User
    users = User.objects.select_related('employee_profile').all().order_by('-date_joined')
    return render(request, 'core/user_list.html', {'users': users})


@login_required
def user_create(request):
    if not is_admin(request.user):
        return HttpResponseForbidden('Only administrators can create users.')
    from django.contrib.auth.models import User
    from django.contrib.auth.forms import UserCreationForm
    from django import forms

    class ExtendedUserCreationForm(UserCreationForm):
        email = forms.EmailField(required=True)
        first_name = forms.CharField(max_length=30, required=False)
        last_name = forms.CharField(max_length=30, required=False)

        class Meta(UserCreationForm.Meta):
            model = User
            fields = ('username', 'email', 'first_name', 'last_name')

    if request.method == 'POST':
        form = ExtendedUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            log_action(request, 'create', 'User', user)
            messages.success(request, f'User "{user.username}" created successfully.')
            return redirect('user_list')
    else:
        form = ExtendedUserCreationForm()
    return render(request, 'core/user_form.html', {'form': form, 'action': 'Create User'})


@login_required
def user_delete(request, pk):
    if not is_admin(request.user):
        return HttpResponseForbidden('Only administrators can delete users.')
    from django.contrib.auth.models import User
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.error(request, 'You cannot delete your own account.')
        return redirect('user_list')
    log_action(request, 'delete', 'User', user)
    user.delete()
    messages.success(request, f'User "{user.username}" deleted.')
    return redirect('user_list')


# ── Password Reset ────────────────────────────────────────────
# Uses Django's built-in views, configured in urls.py.
# Templates are in templates/registration/


@login_required
def task_list(request):
    if request.method == 'POST' and 'bulk_action' in request.POST:
        selected_ids = request.POST.getlist('selected_tasks')
        if not selected_ids:
            messages.error(request, 'Select at least one task first.')
            return redirect('task_list')
        if not request.user.is_superuser:
            messages.error(request, 'Only superusers can delete tasks.')
            return redirect('task_list')
        for t in Task.objects.filter(pk__in=selected_ids):
            log_action(request, 'delete', 'Task', t, description=t.title)
            t.delete()
        messages.success(request, f'{len(selected_ids)} task(s) deleted.')
        return redirect('task_list')
    q = request.GET.get('q', '')
    qs = Task.objects.filter(Q(title__icontains=q)).order_by('-created_at') if q else Task.objects.all().order_by('-created_at')
    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'core/tasks.html', {'tasks': page, 'q': q})


@login_required
def task_detail(request, pk):
    task = get_object_or_404(Task, pk=pk)
    return render(request, 'core/task_detail.html', {'task': task})


@login_required
def task_create(request):
    form = TaskForm(request.POST or None)
    if form.is_valid():
        obj = form.save()
        log_action(request, 'create', 'Task', obj)
        messages.success(request, 'Task created.')
        return redirect('task_list')
    return render(request, 'core/task_form.html', {'form': form, 'action': 'Create'})


@login_required
def task_edit(request, pk):
    obj = get_object_or_404(Task, pk=pk)
    form = TaskForm(request.POST or None, instance=obj)
    if form.is_valid():
        form.save()
        log_action(request, 'update', 'Task', obj)
        messages.success(request, 'Task updated.')
        return redirect('task_list')
    return render(request, 'core/task_form.html', {'form': form, 'action': 'Edit'})


@login_required
def task_delete(request, pk):
    if not request.user.is_superuser:
        messages.error(request, 'Only superusers can delete tasks.')
        return redirect('task_list')
    obj = get_object_or_404(Task, pk=pk)
    log_action(request, 'delete', 'Task', obj)
    obj.delete()
    messages.success(request, 'Task deleted.')
    return redirect('task_list')


@login_required
def project_list(request):
    if request.method == 'POST' and 'bulk_action' in request.POST:
        selected_ids = request.POST.getlist('selected_projects')
        if not selected_ids:
            messages.error(request, 'Select at least one project first.')
            return redirect('project_list')
        if not request.user.is_superuser:
            messages.error(request, 'Only superusers can delete projects.')
            return redirect('project_list')
        for p in Project.objects.filter(pk__in=selected_ids):
            log_action(request, 'delete', 'Project', p, description=p.name)
            p.delete()
        messages.success(request, f'{len(selected_ids)} project(s) deleted.')
        return redirect('project_list')
    q = request.GET.get('q', '')
    status = request.GET.get('status', '')
    qs = Project.objects.all().order_by('-created_at')
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))
    if status:
        qs = qs.filter(status=status)
    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'core/projects.html', {'projects': page, 'q': q, 'status': status})


@login_required
def project_create(request):
    form = ProjectForm(request.POST or None)
    if form.is_valid():
        obj = form.save()
        log_action(request, 'create', 'Project', obj)
        messages.success(request, 'Project created.')
        return redirect('project_list')
    return render(request, 'core/project_form.html', {'form': form, 'action': 'Create'})


@login_required
def project_edit(request, pk):
    obj = get_object_or_404(Project, pk=pk)
    form = ProjectForm(request.POST or None, instance=obj)
    if form.is_valid():
        form.save()
        log_action(request, 'update', 'Project', obj)
        messages.success(request, 'Project updated.')
        return redirect('project_list')
    return render(request, 'core/project_form.html', {'form': form, 'action': 'Edit'})


@login_required
def project_detail(request, pk):
    obj = get_object_or_404(Project, pk=pk)
    return render(request, 'core/project_detail.html', {'project': obj})


@login_required
def project_delete(request, pk):
    if not request.user.is_superuser:
        messages.error(request, 'Only superusers can delete projects.')
        return redirect('project_list')
    obj = get_object_or_404(Project, pk=pk)
    log_action(request, 'delete', 'Project', obj)
    obj.delete()
    messages.success(request, 'Project deleted.')
    return redirect('project_list')


@login_required
@login_required
def schedule_detail(request, pk):
    obj = get_object_or_404(Schedule, pk=pk)
    return render(request, 'core/schedule_detail.html', {'schedule': obj})


@login_required
def schedule_list(request):
    if request.method == 'POST' and 'bulk_action' in request.POST:
        selected_ids = request.POST.getlist('selected_schedules')
        if not selected_ids:
            messages.error(request, 'Select at least one schedule first.')
            return redirect('schedule_list')
        if not request.user.is_superuser:
            messages.error(request, 'Only superusers can delete schedules.')
            return redirect('schedule_list')
        for s in Schedule.objects.filter(pk__in=selected_ids):
            log_action(request, 'delete', 'Schedule', s, description=s.title)
            s.delete()
        messages.success(request, f'{len(selected_ids)} schedule(s) deleted.')
        return redirect('schedule_list')
    qs = Schedule.objects.all().order_by('-start_datetime')
    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'core/schedules.html', {'schedules': page})


@login_required
def schedule_create(request):
    form = ScheduleForm(request.POST or None)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.created_by = request.user
        obj.save()
        log_action(request, 'create', 'Schedule', obj)
        messages.success(request, 'Schedule created.')
        return redirect('schedule_list')
    return render(request, 'core/schedule_form.html', {'form': form, 'action': 'Create'})


@login_required
def schedule_edit(request, pk):
    obj = get_object_or_404(Schedule, pk=pk)
    form = ScheduleForm(request.POST or None, instance=obj)
    if form.is_valid():
        form.save()
        log_action(request, 'update', 'Schedule', obj)
        messages.success(request, 'Schedule updated.')
        return redirect('schedule_list')
    return render(request, 'core/schedule_form.html', {'form': form, 'action': 'Edit'})


@login_required
def schedule_delete(request, pk):
    if not request.user.is_superuser:
        messages.error(request, 'Only superusers can delete schedules.')
        return redirect('schedule_list')
    obj = get_object_or_404(Schedule, pk=pk)
    log_action(request, 'delete', 'Schedule', obj)
    obj.delete()
    messages.success(request, 'Schedule deleted.')
    return redirect('schedule_list')


@login_required
def currency_settings(request):
    obj = CurrencySettings.load()
    form = CurrencySettingsForm(request.POST or None, instance=obj)
    if form.is_valid():
        form.save()
        messages.success(request, 'Currency settings updated.')
        return redirect('currency_settings')
    return render(request, 'core/currency_settings.html', {'form': form})


@login_required
def activity_logs(request):
    if not request.user.is_superuser:
        messages.error(request, 'Only superusers can view activity logs.')
        return redirect('dashboard')
    q = request.GET.get('q', '')
    action = request.GET.get('action', '')
    qs = Log.objects.select_related('user').all()
    if q:
        qs = qs.filter(Q(model_name__icontains=q) | Q(object_repr__icontains=q) | Q(description__icontains=q))
    if action:
        qs = qs.filter(action=action)
    paginator = Paginator(qs, 50)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'core/activity_logs.html', {'logs': page, 'q': q, 'action': action})


@login_required
def update_site_settings(request):
    if not request.user.is_superuser:
        messages.error(request, 'Only superusers can change site settings.')
        return redirect('dashboard')
    settings = SiteSettings.load()
    if request.method == 'POST' and request.FILES.get('logo_image'):
        settings.logo_image = request.FILES['logo_image']
        settings.save()
        messages.success(request, 'Logo updated.')
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))


@login_required
def profile(request):
    employee = getattr(request.user, 'employee_profile', None)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        if name and email:
            request.user.first_name = name.split()[0] if name else ''
            request.user.last_name = ' '.join(name.split()[1:]) if len(name.split()) > 1 else ''
            request.user.email = email
            request.user.save()
            if employee:
                employee.name = name
                employee.email = email
                if phone:
                    employee.phone = phone
                employee.save()
            messages.success(request, 'Profile updated.')
        else:
            messages.error(request, 'Name and email are required.')
        return redirect('profile')
    staff = None
    if request.user.is_superuser:
        from hr.models import Employee as HrEmployee
        staff = HrEmployee.objects.select_related('user', 'department', 'designation').all().order_by('name')
    return render(request, 'core/profile.html', {
        'employee': employee,
        'staff': staff,
    })
