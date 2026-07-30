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
    if request.method == 'POST' and 'bulk_action' in request.POST:
        selected_ids = request.POST.getlist('selected_leaves')
        if not selected_ids:
            messages.error(request, 'Select at least one leave first.')
            return redirect('leave_list')
        if not request.user.is_superuser:
            messages.error(request, 'Only superusers can delete leaves.')
            return redirect('leave_list')
        for obj in Leave.objects.filter(pk__in=selected_ids):
            log_action(request, 'delete', 'Leave', obj)
            obj.delete()
        messages.success(request, f'{len(selected_ids)} leave(s) deleted.')
        return redirect('leave_list')
    q = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    leave_type = request.GET.get('leave_type', '')
    sort = request.GET.get('sort', 'date')
    dir = request.GET.get('dir', 'desc')
    sort_map = {'id': 'id', 'employee': 'employee__name', 'leave_type': 'leave_type', 'start': 'start_date', 'end': 'end_date', 'status': 'status', 'created': 'created_at'}
    order = sort_map.get(sort, 'created_at')
    if dir == 'desc':
        order = '-' + order
    qs = Leave.objects.select_related('employee', 'approved_by').all().order_by(order)
    if q:
        qs = qs.filter(Q(employee__name__icontains=q) | Q(reason__icontains=q))
    if status_filter:
        qs = qs.filter(status=status_filter)
    if leave_type:
        qs = qs.filter(leave_type=leave_type)
    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'hr/leaves.html', {
        'leaves': page, 'q': q, 'status_filter': status_filter,
        'leave_type': leave_type, 'sort': sort, 'dir': dir,
    })


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
    if request.method == 'POST' and 'bulk_action' in request.POST:
        selected_ids = request.POST.getlist('selected_attendances')
        if not selected_ids:
            messages.error(request, 'Select at least one attendance record first.')
            return redirect('attendance_list')
        if not request.user.is_superuser:
            messages.error(request, 'Only superusers can delete attendance records.')
            return redirect('attendance_list')
        for obj in Attendance.objects.filter(pk__in=selected_ids):
            log_action(request, 'delete', 'Attendance', obj)
            obj.delete()
        messages.success(request, f'{len(selected_ids)} attendance record(s) deleted.')
        return redirect('attendance_list')
    q = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    sort = request.GET.get('sort', 'date')
    dir = request.GET.get('dir', 'desc')
    sort_map = {'id': 'id', 'employee': 'employee__name', 'date': 'date', 'check_in': 'check_in', 'check_out': 'check_out', 'status': 'status'}
    order = sort_map.get(sort, 'date')
    if dir == 'desc':
        order = '-' + order
    qs = Attendance.objects.select_related('employee').all().order_by(order)
    if q:
        qs = qs.filter(employee__name__icontains=q)
    if status_filter:
        qs = qs.filter(status=status_filter)
    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'hr/attendance.html', {
        'attendances': page, 'q': q,
        'status_filter': status_filter, 'sort': sort, 'dir': dir,
    })


@login_required
def attendance_create(request):
    form = AttendanceForm(request.POST or None)
    if form.is_valid():
        obj = form.save()
        log_action(request, 'create', 'Attendance', obj)
        messages.success(request, 'Attendance recorded.')
        return redirect('attendance_list')
    return render(request, 'hr/attendance_form.html', {'form': form, 'action': 'Record'})


@login_required
def attendance_edit(request, pk):
    if not request.user.is_superuser:
        messages.error(request, 'Only superusers can edit attendance records.')
        return redirect('attendance_list')
    obj = get_object_or_404(Attendance, pk=pk)
    form = AttendanceForm(request.POST or None, instance=obj)
    if form.is_valid():
        obj = form.save()
        log_action(request, 'update', 'Attendance', obj)
        messages.success(request, 'Attendance updated.')
        return redirect('attendance_list')
    return render(request, 'hr/attendance_form.html', {'form': form, 'action': 'Edit', 'attendance': obj})


@login_required
def attendance_detail(request, pk):
    obj = get_object_or_404(Attendance, pk=pk)
    return render(request, 'hr/attendance_detail.html', {'attendance': obj})


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
