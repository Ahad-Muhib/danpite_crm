from django.urls import path

from . import views

urlpatterns = [
    path('hr/employees/', views.employee_list, name='employee_list'),
    path('hr/employees/new/', views.employee_create, name='employee_create'),
    path('hr/employees/<int:pk>/', views.employee_detail, name='employee_detail'),
    path('hr/employees/<int:pk>/edit/', views.employee_edit, name='employee_edit'),
    path('hr/employees/<int:pk>/delete/', views.employee_delete, name='employee_delete'),
    path('hr/leaves/', views.leave_list, name='leave_list'),
    path('hr/leaves/new/', views.leave_create, name='leave_create'),
    path('hr/leaves/<int:pk>/status/', views.leave_status, name='leave_status'),
    path('hr/attendance/', views.attendance_list, name='attendance_list'),
    path('hr/attendance/new/', views.attendance_create, name='attendance_create'),
]

