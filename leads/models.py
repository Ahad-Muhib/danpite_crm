from django.contrib.auth.models import User
from django.db import models


class FollowUp(models.Model):
    TYPE = [('call', 'Call'), ('email', 'Email'), ('meeting', 'Meeting'), ('note', 'Note'), ('other', 'Other')]
    lead = models.ForeignKey('LeadContact', null=True, blank=True, on_delete=models.SET_NULL, related_name='followups')
    deal = models.ForeignKey('Deal', null=True, blank=True, on_delete=models.SET_NULL, related_name='followups')
    followup_type = models.CharField(max_length=20, choices=TYPE, default='call')
    subject = models.CharField(max_length=200)
    notes = models.TextField(blank=True)
    next_followup_date = models.DateField(null=True, blank=True)
    outcome = models.CharField(max_length=100, blank=True)
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='followups_created')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_followup_type_display()} - {self.subject}"


class LeadContact(models.Model):
    SOURCE = [('none', 'None'), ('cold_call', 'Cold Call'), ('email', 'Email'), ('website', 'Website'), ('social', 'Social Media'), ('referral', 'Referral'), ('other', 'Other')]
    SOURCE_LABELS = dict(SOURCE)
    SOURCE_SUGGESTIONS = [label for _, label in SOURCE if label != 'None']
    CONTACT_TYPE = [('lead', 'Lead'), ('deal', 'Deal')]
    salutation = models.CharField(max_length=10, blank=True)
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30)
    company = models.CharField(max_length=200, blank=True)
    website = models.URLField(blank=True)
    address = models.TextField(blank=True)
    lead_source = models.CharField(max_length=100, default='none', blank=True)
    contact_type = models.CharField(max_length=10, choices=CONTACT_TYPE, default='lead')
    lead_owner = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='owned_leads')
    added_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='added_leads')
    is_converted = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
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
    STAGE = [('generated', 'Generated'), ('qualified', 'Qualified'), ('presentation', 'Presentation'), ('negotiation', 'Negotiation'), ('won', 'Won'), ('lost', 'Lost')]
    lead_contact = models.ForeignKey(LeadContact, null=True, blank=True, on_delete=models.SET_NULL, related_name='deals')
    deal_name = models.CharField(max_length=200)
    pipeline = models.CharField(max_length=30, choices=PIPELINE, default='sales')
    stage = models.CharField(max_length=30, choices=STAGE, default='generated')
    value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default='USD')
    close_date = models.DateField(null=True, blank=True)
    next_follow_up = models.DateField(null=True, blank=True)
    deal_agent = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='agent_deals')
    deal_watcher = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='watched_deals')
    category = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    auto_convert = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.deal_name
