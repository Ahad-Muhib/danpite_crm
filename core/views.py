from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from clients.models import Client
from hr.models import Employee
from leads.models import LeadContact
from orders.models import Order

from .forms import ProjectForm, ScheduleForm, TaskForm
from .models import Project, Schedule, Task


@login_required
def dashboard(request):
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
    }
    return render(request, 'core/dashboard.html', ctx)


@login_required
def task_list(request):
    q = request.GET.get('q', '')
    qs = Task.objects.filter(Q(title__icontains=q)) if q else Task.objects.all()
    return render(request, 'core/tasks.html', {'tasks': qs, 'q': q})


@login_required
def task_create(request):
    form = TaskForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Task created.')
        return redirect('task_list')
    return render(request, 'core/task_form.html', {'form': form, 'action': 'Create'})


@login_required
def task_edit(request, pk):
    obj = get_object_or_404(Task, pk=pk)
    form = TaskForm(request.POST or None, instance=obj)
    if form.is_valid():
        form.save()
        messages.success(request, 'Task updated.')
        return redirect('task_list')
    return render(request, 'core/task_form.html', {'form': form, 'action': 'Edit'})


@login_required
def task_delete(request, pk):
    get_object_or_404(Task, pk=pk).delete()
    messages.success(request, 'Task deleted.')
    return redirect('task_list')


@login_required
def project_list(request):
    qs = Project.objects.all().order_by('-created_at')
    return render(request, 'core/projects.html', {'projects': qs})


@login_required
def project_create(request):
    form = ProjectForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Project created.')
        return redirect('project_list')
    return render(request, 'core/project_form.html', {'form': form, 'action': 'Create'})


@login_required
def project_edit(request, pk):
    obj = get_object_or_404(Project, pk=pk)
    form = ProjectForm(request.POST or None, instance=obj)
    if form.is_valid():
        form.save()
        messages.success(request, 'Project updated.')
        return redirect('project_list')
    return render(request, 'core/project_form.html', {'form': form, 'action': 'Edit'})


@login_required
def project_delete(request, pk):
    get_object_or_404(Project, pk=pk).delete()
    messages.success(request, 'Project deleted.')
    return redirect('project_list')


@login_required
def schedule_list(request):
    qs = Schedule.objects.all().order_by('-start_datetime')
    return render(request, 'core/schedules.html', {'schedules': qs})


@login_required
def schedule_create(request):
    form = ScheduleForm(request.POST or None)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.created_by = request.user
        obj.save()
        messages.success(request, 'Schedule created.')
        return redirect('schedule_list')
    return render(request, 'core/schedule_form.html', {'form': form, 'action': 'Create'})


@login_required
def schedule_edit(request, pk):
    obj = get_object_or_404(Schedule, pk=pk)
    form = ScheduleForm(request.POST or None, instance=obj)
    if form.is_valid():
        form.save()
        messages.success(request, 'Schedule updated.')
        return redirect('schedule_list')
    return render(request, 'core/schedule_form.html', {'form': form, 'action': 'Edit'})


@login_required
def schedule_delete(request, pk):
    get_object_or_404(Schedule, pk=pk).delete()
    messages.success(request, 'Schedule deleted.')
    return redirect('schedule_list')
