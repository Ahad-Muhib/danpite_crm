from django.contrib import admin

from .models import Deal, LeadContact


@admin.register(LeadContact)
class LeadContactAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'company', 'lead_source', 'is_converted']
    list_filter = ['lead_source', 'is_converted']
    search_fields = ['name', 'email', 'company']


@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    list_display = ['deal_name', 'lead_contact', 'stage', 'value', 'close_date']
    list_filter = ['pipeline', 'stage']

