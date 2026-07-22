from django.urls import path

from . import views

urlpatterns = [
    path('accounts/client-data/', views.client_data_api, name='client_data_api'),
    path('accounts/invoices/', views.invoice_list, name='invoice_list'),
    path('accounts/invoices/new/', views.invoice_create, name='invoice_create'),
    path('accounts/invoices/<int:pk>/', views.invoice_detail, name='invoice_detail'),
    path('accounts/invoices/<int:pk>/edit/', views.invoice_edit, name='invoice_edit'),
    path('accounts/invoices/<int:pk>/delete/', views.invoice_delete, name='invoice_delete'),
    path('accounts/payments/', views.payment_list, name='payment_list'),
    path('accounts/payments/new/', views.payment_create, name='payment_create'),
    path('accounts/payments/<int:pk>/', views.payment_detail, name='payment_detail'),
    path('accounts/payments/<int:pk>/edit/', views.payment_edit, name='payment_edit'),
    path('accounts/payments/<int:pk>/delete/', views.payment_delete, name='payment_delete'),
    path('accounts/expenses/', views.expense_list, name='expense_list'),
    path('accounts/expenses/new/', views.expense_create, name='expense_create'),
    path('accounts/expenses/<int:pk>/', views.expense_detail, name='expense_detail'),
    path('accounts/expenses/<int:pk>/edit/', views.expense_edit, name='expense_edit'),
    path('accounts/expenses/<int:pk>/delete/', views.expense_delete, name='expense_delete'),
    path('accounts/bank/', views.bank_account_list, name='bank_account_list'),
    path('accounts/bank/new/', views.bank_account_create, name='bank_account_create'),
    path('accounts/bank/<int:pk>/', views.bank_account_detail, name='bank_account_detail'),
    path('accounts/bank/<int:pk>/edit/', views.bank_account_edit, name='bank_account_edit'),
    path('accounts/bank/<int:pk>/toggle/', views.bank_account_toggle, name='bank_account_toggle'),
    path('accounts/bank/<int:pk>/delete/', views.bank_account_delete, name='bank_account_delete'),
]

