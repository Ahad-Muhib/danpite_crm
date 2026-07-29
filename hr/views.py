from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.models import log_action
from .forms import AttendanceForm, EmployeeForm, LeaveForm
from .models import Attendance, Designation, Employee, EmployeeRole, Leave


@login_required
def employee_list(request):
    if request.method == 'POST' and 'bulk_action' in request.POST:
        selected_ids = request.POST.getlist('selected_employees')
        if not selected_ids:
            messages.error(request, 'Select at least one employee first.')
            return redirect('employee_list')
        if not request.user.is_superuser:
            messages.error(request, 'Only superusers can delete employees.')
            return redirect('employee_list')
        for emp in Employee.objects.filter(pk__in=selected_ids):
            log_action(request, 'delete', 'Employee', emp)
            emp.delete()
        messages.success(request, f'{len(selected_ids)} employee(s) deleted.')
        return redirect('employee_list')
    q = request.GET.get('q', '')
    qs = Employee.objects.select_related('user').all().order_by('-id')
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(email__icontains=q) | Q(employee_id__icontains=q))
    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'hr/employees.html', {'employees': page, 'q': q})


@login_required
def employee_create(request):
    if not request.user.is_superuser:
        messages.error(request, 'Only superusers can add employees.')
        return redirect('employee_list')
    form = EmployeeForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        emp = form.save()
        log_action(request, 'create', 'Employee', emp)
        raw_password = getattr(emp, '_raw_password', None)
        if raw_password:
            messages.success(request, f'Employee added. Login credentials — Username: {emp.user.username} | Password: {raw_password}')
        else:
            messages.success(request, 'Employee added.')
        return redirect('employee_list')
    return render(request, 'hr/employee_form.html', {'form': form, 'action': 'Add'})


@login_required
def employee_edit(request, pk):
    if not request.user.is_superuser:
        messages.error(request, 'Only superusers can edit employees.')
        return redirect('employee_list')
    obj = get_object_or_404(Employee, pk=pk)
    form = EmployeeForm(request.POST or None, request.FILES or None, instance=obj, request_user=request.user)
    if form.is_valid():
        obj = form.save()
        log_action(request, 'update', 'Employee', obj)
        messages.success(request, 'Employee updated.')
        return redirect('employee_list')
    return render(request, 'hr/employee_form.html', {'form': form, 'action': 'Edit', 'employee': obj})


@login_required
def employee_detail(request, pk):
    emp = get_object_or_404(Employee, pk=pk)
    leaves = emp.leaves.all()[:5]
    attendances = emp.attendances.all().order_by('-date')[:10]
    return render(request, 'hr/employee_detail.html', {'employee': emp, 'leaves': leaves, 'attendances': attendances})


@login_required
def employee_delete(request, pk):
    if not request.user.is_superuser:
        messages.error(request, 'Only superusers can delete employees.')
        return redirect('employee_list')
    obj = get_object_or_404(Employee, pk=pk)
    log_action(request, 'delete', 'Employee', obj)
    obj.delete()
    messages.success(request, 'Employee deleted.')
    return redirect('employee_list')


@login_required
def leave_list(request):
    qs = Leave.objects.all().order_by('-created_at')
    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'hr/leaves.html', {'leaves': page})


@login_required
def leave_create(request):
    form = LeaveForm(request.POST or None)
    if form.is_valid():
        obj = form.save()
        log_action(request, 'create', 'Leave', obj)
        messages.success(request, 'Leave application submitted.')
        return redirect('leave_list')
    return render(request, 'hr/leave_form.html', {'form': form})


@login_required
def leave_status(request, pk):
    leave = get_object_or_404(Leave, pk=pk)
    status = request.POST.get('status')
    if status in ['approved', 'rejected']:
        leave.status = status
        leave.approved_by = request.user
        leave.save()
        log_action(request, 'update', 'Leave', leave, description=f'Leave {status}')
        messages.success(request, f'Leave {status}.')
    return redirect('leave_list')


@login_required
def attendance_list(request):
    qs = Attendance.objects.all().order_by('-date')
    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'hr/attendance.html', {'attendances': page})


@login_required
def attendance_create(request):
    form = AttendanceForm(request.POST or None)
    if form.is_valid():
        obj = form.save()
        log_action(request, 'create', 'Attendance', obj)
        messages.success(request, 'Attendance recorded.')
        return redirect('attendance_list')
    return render(request, 'hr/attendance_form.html', {'form': form})


@login_required
@require_POST
def add_employee_role(request):
    name = request.POST.get('name', '').strip()
    if not name:
        return JsonResponse({'ok': False, 'error': 'Role name is required.'})
    role, created = EmployeeRole.objects.get_or_create(name=name)
    if not created:
        return JsonResponse({'ok': False, 'error': 'Role already exists.'})
    return JsonResponse({'ok': True, 'name': role.name})
