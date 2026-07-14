from django.contrib import admin

from .models import Project, Schedule, Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'priority', 'status', 'assigned_to', 'due_date']
    list_filter = ['priority', 'status']
    search_fields = ['title']


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'status', 'manager', 'start_date', 'end_date']
    list_filter = ['status']


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ['title', 'start_datetime', 'end_datetime', 'location']

