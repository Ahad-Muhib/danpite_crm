from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('tasks/', views.task_list, name='task_list'),
    path('tasks/new/', views.task_create, name='task_create'),
    path('tasks/<int:pk>/edit/', views.task_edit, name='task_edit'),
    path('tasks/<int:pk>/delete/', views.task_delete, name='task_delete'),
    path('projects/', views.project_list, name='project_list'),
    path('projects/new/', views.project_create, name='project_create'),
    path('projects/<int:pk>/edit/', views.project_edit, name='project_edit'),
    path('projects/<int:pk>/delete/', views.project_delete, name='project_delete'),
    path('schedules/', views.schedule_list, name='schedule_list'),
    path('schedules/new/', views.schedule_create, name='schedule_create'),
    path('schedules/<int:pk>/edit/', views.schedule_edit, name='schedule_edit'),
    path('schedules/<int:pk>/delete/', views.schedule_delete, name='schedule_delete'),
]

