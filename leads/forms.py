from django import forms

from .models import Comment, Deal, FollowUp, LeadContact


class LeadContactForm(forms.ModelForm):
    class Meta:
        model = LeadContact
        fields = ['salutation', 'name', 'email', 'phone', 'company', 'website', 'address', 'lead_source', 'contact_type', 'lead_owner', 'notes']
        widgets = {
            'salutation': forms.Select(attrs={'class': 'form-select'}, choices=[('', '--'), ('Mr.', 'Mr.'), ('Ms.', 'Ms.'), ('Mrs.', 'Mrs.'), ('Dr.', 'Dr.')]),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'company': forms.TextInput(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'lead_source': forms.TextInput(attrs={'class': 'form-control', 'list': 'lead-source-options', 'placeholder': 'Type or choose a source'}),
            'contact_type': forms.Select(attrs={'class': 'form-select'}),
            'lead_owner': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class DealForm(forms.ModelForm):
    class Meta:
        model = Deal
        fields = ['deal_name', 'lead_contact', 'pipeline', 'stage', 'value', 'currency', 'close_date', 'next_follow_up', 'deal_agent', 'lost_reason', 'description']
        widgets = {
            'deal_name': forms.TextInput(attrs={'class': 'form-control'}),
            'lead_contact': forms.Select(attrs={'class': 'form-select'}),
            'pipeline': forms.Select(attrs={'class': 'form-select'}),
            'stage': forms.Select(attrs={'class': 'form-select'}),
            'value': forms.NumberInput(attrs={'class': 'form-control'}),
            'currency': forms.TextInput(attrs={'class': 'form-control'}),
            'close_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'next_follow_up': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'deal_agent': forms.Select(attrs={'class': 'form-select'}),
            'lost_reason': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class FollowUpForm(forms.ModelForm):
    class Meta:
        model = FollowUp
        fields = ['lead', 'deal', 'followup_type', 'subject', 'notes', 'next_followup_date', 'outcome', 'is_recurring', 'recurrence_days']
        widgets = {
            'lead': forms.Select(attrs={'class': 'form-select'}),
            'deal': forms.Select(attrs={'class': 'form-select'}),
            'followup_type': forms.Select(attrs={'class': 'form-select'}),
            'subject': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'next_followup_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'outcome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Interested, Callback scheduled'}),
            'is_recurring': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'recurrence_days': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['body']
        widgets = {
            'body': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Add a comment...'}),
        }


class ActivityQuickForm(forms.Form):
    title = forms.CharField(max_length=200, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Subject'}))
    description = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Details...'}))


class LeadAssignmentForm(forms.Form):
    lead_owner = forms.ModelChoiceField(queryset=None, required=False, widget=forms.Select(attrs={'class': 'form-select'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.contrib.auth.models import User
        self.fields['lead_owner'].queryset = User.objects.filter(is_active=True).order_by('username')
