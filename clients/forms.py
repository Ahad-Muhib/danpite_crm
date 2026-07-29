from django import forms

from .models import Client, ClientCategory


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['salutation', 'name', 'page', 'email', 'phone', 'mobile', 'company', 'website', 'address', 'category', 'sub_category', 'status', 'notes']
        widgets = {
            'salutation': forms.Select(attrs={'class': 'form-select'}, choices=[('', '--'), ('Mr.', 'Mr.'), ('Ms.', 'Ms.'), ('Mrs.', 'Mrs.'), ('Dr.', 'Dr.')]),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full name'}),
            'page': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Facebook / Instagram / etc.'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email address'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Mobile number'}),
            'company': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Company name'}),
            'website': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Address'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'sub_category': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Sub category'}),
            'notes': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['notes'].required = False
        self.fields['status'].label = 'Status'
        base_choices = [('', '-- Select Category --')]
        hardcoded = [
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
        base_choices.extend(hardcoded)
        for c in ClientCategory.objects.all():
            base_choices.append((c.name, c.name))
        self.fields['category'] = forms.ChoiceField(
            choices=base_choices,
            widget=forms.Select(attrs={'class': 'form-select'}),
        )

