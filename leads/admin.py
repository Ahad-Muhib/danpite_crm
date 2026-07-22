from django.contrib import admin

from .models import Activity, Comment, Deal, FollowUp, LeadContact


@admin.register(LeadContact)
class LeadContactAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'company', 'lead_source', 'lead_owner', 'is_converted']
    list_filter = ['lead_source', 'is_converted']
    search_fields = ['name', 'email', 'company']


@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    list_display = ['deal_name', 'lead_contact', 'stage', 'value', 'close_date', 'next_follow_up', 'lost_reason']
    list_filter = ['pipeline', 'stage']


@admin.register(FollowUp)
class FollowUpAdmin(admin.ModelAdmin):
    list_display = ['subject', 'followup_type', 'lead', 'deal', 'next_followup_date', 'is_recurring', 'created_by', 'created_at']
    list_filter = ['followup_type', 'is_recurring']
    search_fields = ['subject', 'notes']


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ['title', 'activity_type', 'lead', 'deal', 'created_by', 'created_at']
    list_filter = ['activity_type']
    search_fields = ['title', 'description']


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['lead', 'created_by', 'body', 'created_at']
    search_fields = ['body']
