from django.urls import path
from . import views

urlpatterns = [
    # dashboard
    path('', views.dashboard, name='dashboard'),

    # tasks
    path('tasks/',                views.task_list,   name='task_list'),
    path('tasks/new/',            views.task_create, name='task_create'),
    path('tasks/<int:pk>/edit/',  views.task_edit,   name='task_edit'),
    path('tasks/<int:pk>/delete/',views.task_delete, name='task_delete'),

    # projects
    path('projects/',                views.project_list,   name='project_list'),
    path('projects/new/',            views.project_create, name='project_create'),
    path('projects/<int:pk>/edit/',  views.project_edit,   name='project_edit'),
    path('projects/<int:pk>/delete/',views.project_delete, name='project_delete'),

    # schedules
    path('schedules/',                views.schedule_list,   name='schedule_list'),
    path('schedules/new/',            views.schedule_create, name='schedule_create'),
    path('schedules/<int:pk>/edit/',  views.schedule_edit,   name='schedule_edit'),
    path('schedules/<int:pk>/delete/',views.schedule_delete, name='schedule_delete'),

    # leads
    path('leads/',                     views.lead_list,    name='lead_list'),
    path('leads/new/',                 views.lead_create,  name='lead_create'),
    path('leads/<int:pk>/',            views.lead_detail,  name='lead_detail'),
    path('leads/<int:pk>/edit/',       views.lead_edit,    name='lead_edit'),
    path('leads/<int:pk>/delete/',     views.lead_delete,  name='lead_delete'),
    path('leads/<int:pk>/convert/',    views.lead_convert, name='lead_convert'),

    # deals
    path('deals/',                views.deal_list,   name='deal_list'),
    path('deals/new/',            views.deal_create, name='deal_create'),
    path('deals/<int:pk>/edit/',  views.deal_edit,   name='deal_edit'),
    path('deals/<int:pk>/delete/',views.deal_delete, name='deal_delete'),

    # clients
    path('clients/',                views.client_list,   name='client_list'),
    path('clients/new/',            views.client_create, name='client_create'),
    path('clients/<int:pk>/',       views.client_detail, name='client_detail'),
    path('clients/<int:pk>/edit/',  views.client_edit,   name='client_edit'),
    path('clients/<int:pk>/delete/',views.client_delete, name='client_delete'),

    # employees
    path('hr/employees/',                views.employee_list,   name='employee_list'),
    path('hr/employees/new/',            views.employee_create, name='employee_create'),
    path('hr/employees/<int:pk>/',       views.employee_detail, name='employee_detail'),
    path('hr/employees/<int:pk>/edit/',  views.employee_edit,   name='employee_edit'),
    path('hr/employees/<int:pk>/delete/',views.employee_delete, name='employee_delete'),

    # leaves
    path('hr/leaves/',                       views.leave_list,   name='leave_list'),
    path('hr/leaves/new/',                   views.leave_create, name='leave_create'),
    path('hr/leaves/<int:pk>/status/',       views.leave_status, name='leave_status'),

    # attendance
    path('hr/attendance/',      views.attendance_list,   name='attendance_list'),
    path('hr/attendance/new/',  views.attendance_create, name='attendance_create'),

    # invoices
    path('accounts/invoices/',                views.invoice_list,   name='invoice_list'),
    path('accounts/invoices/new/',            views.invoice_create, name='invoice_create'),
    path('accounts/invoices/<int:pk>/',       views.invoice_detail, name='invoice_detail'),
    path('accounts/invoices/<int:pk>/edit/',  views.invoice_edit,   name='invoice_edit'),
    path('accounts/invoices/<int:pk>/delete/',views.invoice_delete, name='invoice_delete'),

    # payments
    path('accounts/payments/',                views.payment_list,   name='payment_list'),
    path('accounts/payments/new/',            views.payment_create, name='payment_create'),
    path('accounts/payments/<int:pk>/delete/',views.payment_delete, name='payment_delete'),

    # expenses
    path('accounts/expenses/',                views.expense_list,   name='expense_list'),
    path('accounts/expenses/new/',            views.expense_create, name='expense_create'),
    path('accounts/expenses/<int:pk>/delete/',views.expense_delete, name='expense_delete'),

    # bank accounts
    path('accounts/bank/',                views.bank_account_list,   name='bank_account_list'),
    path('accounts/bank/new/',            views.bank_account_create, name='bank_account_create'),
    path('accounts/bank/<int:pk>/delete/',views.bank_account_delete, name='bank_account_delete'),

    # orders
    path('orders/',                views.order_list,   name='order_list'),
    path('orders/new/',            views.order_create, name='order_create'),
    path('orders/<int:pk>/',       views.order_detail, name='order_detail'),
    path('orders/<int:pk>/edit/',  views.order_edit,   name='order_edit'),
    path('orders/<int:pk>/delete/',views.order_delete, name='order_delete'),
]
