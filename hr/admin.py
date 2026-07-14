from django.contrib import admin

from .models import Attendance, Department, Designation, Employee, Leave


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name']


@admin.register(Designation)
class DesignationAdmin(admin.ModelAdmin):
    list_display = ['title', 'department']


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['employee_id', 'name', 'email', 'role', 'designation', 'status']
    list_filter = ['role', 'status']
    search_fields = ['name', 'email', 'employee_id']


@admin.register(Leave)
class LeaveAdmin(admin.ModelAdmin):
    list_display = ['employee', 'leave_type', 'start_date', 'end_date', 'status']
    list_filter = ['leave_type', 'status']


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['employee', 'date', 'check_in', 'check_out', 'status']
    list_filter = ['status']

