from django.contrib import admin

from .models import Deal, FollowUp, LeadContact


@admin.register(LeadContact)
class LeadContactAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'company', 'lead_source', 'is_converted']
    list_filter = ['lead_source', 'is_converted']
    search_fields = ['name', 'email', 'company']


@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    list_display = ['deal_name', 'lead_contact', 'stage', 'value', 'close_date', 'next_follow_up']
    list_filter = ['pipeline', 'stage']


@admin.register(FollowUp)
class FollowUpAdmin(admin.ModelAdmin):
    list_display = ['subject', 'followup_type', 'lead', 'deal', 'next_followup_date', 'created_by', 'created_at']
    list_filter = ['followup_type']
    search_fields = ['subject', 'notes']

