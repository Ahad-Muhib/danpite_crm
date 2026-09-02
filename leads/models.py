from django.contrib.auth.models import User
from django.db import models


class LeadSource(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Activity(models.Model):
    TYPE = [
        ('call', 'Call'),
        ('email', 'Email'),
        ('meeting', 'Meeting'),
        ('note', 'Note'),
        ('status_change', 'Status Change'),
        ('deal_update', 'Deal Update'),
        ('assignment', 'Assignment'),
        ('conversion', 'Conversion'),
        ('followup', 'Follow-up'),
        ('other', 'Other'),
    ]
    lead = models.ForeignKey('LeadContact', null=True, blank=True, on_delete=models.SET_NULL, related_name='activities')
    deal = models.ForeignKey('Deal', null=True, blank=True, on_delete=models.SET_NULL, related_name='activities')
    activity_type = models.CharField(max_length=20, choices=TYPE, default='note')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    meta = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='activities_created')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_activity_type_display()} - {self.title}"


class Comment(models.Model):
    lead = models.ForeignKey('LeadContact', on_delete=models.CASCADE, related_name='comments')
    body = models.TextField()
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='lead_comments')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Comment by {self.created_by} on {self.lead}"


class FollowUp(models.Model):
    TYPE = [('call', 'Call'), ('email', 'Email'), ('meeting', 'Meeting'), ('note', 'Note'), ('other', 'Other')]
    lead = models.ForeignKey('LeadContact', null=True, blank=True, on_delete=models.SET_NULL, related_name='followups')
    deal = models.ForeignKey('Deal', null=True, blank=True, on_delete=models.SET_NULL, related_name='followups')
    followup_type = models.CharField(max_length=20, choices=TYPE, default='call')
    subject = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    next_followup_date = models.DateField(null=True, blank=True)
    outcome = models.CharField(max_length=100, blank=True)
    is_recurring = models.BooleanField(default=False)
    recurrence_days = models.PositiveIntegerField(default=7, help_text='Days until next follow-up is auto-created')
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='followups_created')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_followup_type_display()} - {self.subject}"


class LeadContact(models.Model):
    SOURCE = [
        ('none', 'None'),
        ('affiliate', 'Affiliate'),
        ('email_marketing', 'Email Marketing'),
        ('event', 'Event'),
        ('existing_customer', 'Existing Customer'),
        ('facebook', 'Facebook'),
        ('facebook_ads', 'Facebook Ads'),
        ('google', 'Google'),
        ('google_ads', 'Google Ads'),
        ('instagram', 'Instagram'),
        ('linkedin', 'LinkedIn'),
        ('phone_call', 'Phone Call'),
        ('reference', 'Reference'),
        ('sms_campaign', 'SMS Campaign'),
        ('walk_in', 'Walk-in'),
        ('website', 'Website'),
        ('other', 'Other'),
    ]
    SOURCE_LABELS = dict(SOURCE)
    SOURCE_SUGGESTIONS = [label for _, label in SOURCE if label != 'None']
    CONTACT_TYPE = [('hot', 'Hot'), ('cold', 'Cold'), ('mid', 'Mid')]
    STATE = [('open', 'Open'), ('closed', 'Closed')]
    STATUS = [
        ('', '---'),
        ('attempted_contact', 'Attempted Contact'),
        ('contacted', 'Contacted'),
        ('convert_to_sale', 'Convert to Sale'),
        ('interested', 'Interested'),
        ('lost', 'Lost'),
        ('meeting_scheduled', 'Meeting Scheduled'),
        ('needs_follow_up', 'Needs Follow Up'),
        ('negotiation', 'Negotiation'),
        ('new_lead', 'New Lead'),
        ('not_interested', 'Not Interested'),
        ('proposal_sent', 'Proposal Sent'),
    ]
    FOLLOWUP_ACTION = [('call', 'Call'), ('text', 'Text'), ('meeting', 'Meeting'), ('email', 'Email'), ('other', 'Other')]
    salutation = models.CharField(max_length=10, blank=True)
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30)
    company = models.CharField(max_length=200, blank=True)
    website = models.URLField(blank=True)
    address = models.TextField(blank=True)
    lead_source = models.CharField(max_length=100, default='none', blank=True)
    contact_type = models.CharField(max_length=10, choices=CONTACT_TYPE, default='cold')
    lead_owner = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='owned_leads')
    added_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='added_leads')
    is_converted = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    lead_state = models.CharField(max_length=10, choices=STATE, default='open')
    lead_status = models.CharField(max_length=25, choices=STATUS, default='new_lead', blank=True)
    budget = models.CharField(max_length=100, blank=True, help_text='Initial budget estimate')
    next_followup_date = models.DateField(null=True, blank=True)
    followup_action = models.CharField(max_length=20, choices=FOLLOWUP_ACTION, default='call', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    @property
    def lead_source_label(self):
        if not self.lead_source:
            return 'None'
        return self.SOURCE_LABELS.get(self.lead_source, self.lead_source)


class Deal(models.Model):
    PIPELINE = [('sales', 'Sales'), ('marketing', 'Marketing'), ('support', 'Support')]
    STAGE = [('generated', 'Generated'), ('won', 'Won'), ('lost', 'Lost')]
    LOST_REASON = [('', '—'), ('price', 'Price'), ('competitor', 'Competitor'), ('timing', 'Bad Timing'), ('budget', 'No Budget'), ('no_need', 'No Need'), ('no_response', 'No Response'), ('other', 'Other')]
    lead_contact = models.ForeignKey(LeadContact, null=True, blank=True, on_delete=models.SET_NULL, related_name='deals')
    deal_name = models.CharField(max_length=200)
    pipeline = models.CharField(max_length=30, choices=PIPELINE, default='sales')
    stage = models.CharField(max_length=30, choices=STAGE, default='generated')
    value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default='BDT')
    close_date = models.DateField(null=True, blank=True)
    next_follow_up = models.DateField(null=True, blank=True)
    deal_agent = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='agent_deals')
    deal_watcher = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='watched_deals')
    category = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    lost_reason = models.CharField(max_length=30, choices=LOST_REASON, blank=True, default='')
    auto_convert = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.deal_name
