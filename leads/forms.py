from django import forms

from .models import Deal, LeadContact


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
        fields = ['deal_name', 'lead_contact', 'pipeline', 'stage', 'value', 'currency', 'close_date', 'deal_agent', 'description']
        widgets = {
            'deal_name': forms.TextInput(attrs={'class': 'form-control'}),
            'lead_contact': forms.Select(attrs={'class': 'form-select'}),
            'pipeline': forms.Select(attrs={'class': 'form-select'}),
            'stage': forms.Select(attrs={'class': 'form-select'}),
            'value': forms.NumberInput(attrs={'class': 'form-control'}),
            'currency': forms.TextInput(attrs={'class': 'form-control'}),
            'close_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'deal_agent': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
