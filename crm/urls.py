from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("staff/", views.staff_list, name="staff-list"),
    path("staff/new/", views.staff_create, name="staff-create"),
    path("clients/", views.client_list, name="client-list"),
    path("clients/new/", views.client_create, name="client-create"),
    path("invoices/", views.invoice_list, name="invoice-list"),
    path("invoices/new/", views.invoice_create, name="invoice-create"),
    path("payments/", views.payment_list, name="payment-list"),
    path("payments/new/", views.payment_create, name="payment-create"),
    path("expenses/", views.expense_list, name="expense-list"),
    path("expenses/new/", views.expense_create, name="expense-create"),
    path("accounts/", views.account_list, name="account-list"),
    path("accounts/new/", views.account_create, name="account-create"),
]
