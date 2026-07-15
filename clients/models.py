from django.contrib.auth.models import User
from django.db import models


class Client(models.Model):
    CATEGORY = [('food_restaurant', 'Food & Restaurant'), ('health_medical', 'Health & Medical'), ('technology', 'Technology'), ('education', 'Education'), ('retail', 'Retail'), ('other', 'Other')]
    STATUS = [('active', 'Active'), ('inactive', 'Inactive')]
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    mobile = models.CharField(max_length=30, blank=True)
    company = models.CharField(max_length=200, blank=True)
    website = models.URLField(blank=True)
    address = models.TextField(blank=True)
    category = models.CharField(max_length=30, choices=CATEGORY, blank=True)
    sub_category = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default='active')
    account_manager = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='managed_clients')
    lead_contact = models.ForeignKey('leads.LeadContact', null=True, blank=True, on_delete=models.SET_NULL, related_name='converted_clients')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

