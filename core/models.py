from django.contrib.auth.models import User
from django.db import models


class Task(models.Model):
    PRIORITY = [('low', 'Low'), ('medium', 'Medium'), ('high', 'High')]
    STATUS = [('pending', 'Pending'), ('in_progress', 'In Progress'), ('completed', 'Completed')]
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    priority = models.CharField(max_length=20, choices=PRIORITY, default='medium')
    status = models.CharField(max_length=20, choices=STATUS, default='pending')
    assigned_to = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='tasks')
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class Project(models.Model):
    STATUS = [('not_started', 'Not Started'), ('in_progress', 'In Progress'), ('completed', 'Completed'), ('on_hold', 'On Hold')]
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default='not_started')
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    manager = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='projects')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Schedule(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    location = models.CharField(max_length=200, blank=True)
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='schedules')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

