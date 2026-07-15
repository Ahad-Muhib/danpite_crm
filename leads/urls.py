from django.urls import path

from . import views

urlpatterns = [
    path('leads/', views.lead_list, name='lead_list'),
    path('leads/new/', views.lead_create, name='lead_create'),
    path('leads/<int:pk>/', views.lead_detail, name='lead_detail'),
    path('leads/<int:pk>/edit/', views.lead_edit, name='lead_edit'),
    path('leads/<int:pk>/delete/', views.lead_delete, name='lead_delete'),
    path('leads/<int:pk>/toggle/', views.lead_toggle_active, name='lead_toggle_active'),
    path('leads/<int:pk>/convert/', views.lead_convert, name='lead_convert'),
    path('deals/', views.deal_list, name='deal_list'),
    path('deals/new/', views.deal_create, name='deal_create'),
    path('deals/<int:pk>/edit/', views.deal_edit, name='deal_edit'),
    path('deals/<int:pk>/delete/', views.deal_delete, name='deal_delete'),
]

