from django.contrib.auth.models import User
from django.db import models


class ClientCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Client categories'

    def __str__(self):
        return self.name


class Client(models.Model):
    CATEGORY = [
        ('education', 'Education'),
        ('local_shop', 'Local Shop'),
        ('retail_shopping', 'Retail & Shopping'),
        ('it_technology', 'IT & Technology'),
        ('finance_legal', 'Finance & Legal'),
        ('food_restaurant', 'Food & Restaurant'),
        ('fashion', 'Fashion'),
        ('hospitality_travels', 'Hospitality & Travels'),
        ('real_estate_construction', 'Real Estate & Construction'),
        ('automotive', 'Automotive'),
        ('beauty_personal_care', 'Beauty & Personal Care'),
        ('sports_fitness', 'Sports & Fitness'),
        ('health_medical', 'Health & Medical'),
        ('business_services', 'Business & Services'),
        ('home_local_services', 'Home & Local Services'),
        ('entertainment_lifestyle', 'Entertainment & Lifestyle'),
        ('logistics_transport', 'Logistics & Transport'),
        ('architecture_engineering', 'Architecture & Engineering Consultancy'),
        ('agriculture', 'Agriculture'),
    ]
    STATE = [('active', 'Active'), ('inactive', 'Inactive')]
    salutation = models.CharField(max_length=10, blank=True)
    name = models.CharField(max_length=200)
    page = models.CharField(max_length=200, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    mobile = models.CharField(max_length=30, blank=True)
    company = models.CharField(max_length=200, blank=True)
    website = models.URLField(blank=True)
    address = models.TextField(blank=True)
    category = models.CharField(max_length=30, choices=CATEGORY, blank=True)
    sub_category = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATE, default='open')
    account_manager = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='managed_clients')
    lead_contact = models.ForeignKey('leads.LeadContact', null=True, blank=True, on_delete=models.SET_NULL, related_name='converted_clients')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

