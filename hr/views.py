from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import AttendanceForm, EmployeeForm, LeaveForm
from .models import Attendance, Designation, Employee, Leave


@login_required
def employee_list(request):
    q = request.GET.get('q', '')
    qs = Employee.objects.all()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(email__icontains=q) | Q(employee_id__icontains=q))
    designations = Designation.objects.all()
    return render(request, 'hr/employees.html', {'employees': qs, 'q': q, 'designations': designations})


@login_required
def employee_create(request):
    form = EmployeeForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Employee added.')
        return redirect('employee_list')
    return render(request, 'hr/employee_form.html', {'form': form, 'action': 'Add'})


@login_required
def employee_edit(request, pk):
    obj = get_object_or_404(Employee, pk=pk)
    form = EmployeeForm(request.POST or None, request.FILES or None, instance=obj)
    if form.is_valid():
        form.save()
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
    get_object_or_404(Employee, pk=pk).delete()
    messages.success(request, 'Employee deleted.')
    return redirect('employee_list')


@login_required
def leave_list(request):
    qs = Leave.objects.all().order_by('-created_at')
    return render(request, 'hr/leaves.html', {'leaves': qs})


@login_required
def leave_create(request):
    form = LeaveForm(request.POST or None)
    if form.is_valid():
        form.save()
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
        messages.success(request, f'Leave {status}.')
    return redirect('leave_list')


@login_required
def attendance_list(request):
    qs = Attendance.objects.all().order_by('-date')
    return render(request, 'hr/attendance.html', {'attendances': qs})


@login_required
def attendance_create(request):
    form = AttendanceForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Attendance recorded.')
        return redirect('attendance_list')
    return render(request, 'hr/attendance_form.html', {'form': form})
