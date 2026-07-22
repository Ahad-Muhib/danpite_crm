from django.urls import path

from . import views

urlpatterns = [
    path('leads/', views.lead_list, name='lead_list'),
    path('leads/new/', views.lead_create, name='lead_create'),
    path('leads/import/', views.lead_import, name='lead_import'),
    path('leads/export/', views.lead_export, name='lead_export'),
    path('leads/<int:pk>/', views.lead_detail, name='lead_detail'),
    path('leads/<int:pk>/edit/', views.lead_edit, name='lead_edit'),
    path('leads/<int:pk>/delete/', views.lead_delete, name='lead_delete'),
    path('leads/<int:pk>/toggle/', views.lead_toggle_active, name='lead_toggle_active'),
    path('leads/<int:pk>/convert/', views.lead_convert, name='lead_convert'),
    path('leads/<int:pk>/assign/', views.lead_assign, name='lead_assign'),
    path('leads/<int:pk>/comment/', views.comment_add, name='comment_add'),
    path('leads/<int:pk>/comment/<int:comment_pk>/delete/', views.comment_delete, name='comment_delete'),
    path('leads/<int:pk>/activity/', views.activity_quick_log, name='activity_quick_log'),
    path('followups/', views.followup_list, name='followup_list'),
    path('followups/new/', views.followup_create, name='followup_create'),
    path('followups/<int:pk>/complete/', views.followup_complete, name='followup_complete'),
    path('followups/<int:pk>/delete/', views.followup_delete, name='followup_delete'),
    path('deals/', views.deal_list, name='deal_list'),
    path('deals/kanban/', views.deal_kanban, name='deal_kanban'),
    path('deals/kanban/<int:pk>/stage/', views.deal_update_stage, name='deal_update_stage'),
    path('deals/new/', views.deal_create, name='deal_create'),
    path('deals/<int:pk>/edit/', views.deal_edit, name='deal_edit'),
    path('deals/<int:pk>/delete/', views.deal_delete, name='deal_delete'),
]
