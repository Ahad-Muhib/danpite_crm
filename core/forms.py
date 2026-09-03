from django import forms

from hr.models import Employee

from .models import CurrencySettings, Project, Schedule, Task


class CurrencySettingsForm(forms.ModelForm):
    class Meta:
        model = CurrencySettings
        fields = ['currency_code']
        widgets = {
            'currency_code': forms.Select(attrs={'class': 'form-select'}),
        }


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'description', 'priority', 'status', 'assigned_to', 'start_date', 'due_date']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['assigned_to'].queryset = Employee.objects.all().order_by('name')
        self.fields['assigned_to'].required = False
        self.fields['start_date'].required = False
        self.fields['due_date'].required = False


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name', 'description', 'status', 'start_date', 'end_date', 'manager']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'manager': forms.Select(attrs={'class': 'form-select'}),
        }


class ScheduleForm(forms.ModelForm):
    class Meta:
        model = Schedule
        fields = ['title', 'description', 'start_datetime', 'end_datetime', 'location']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'start_datetime': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_datetime': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
        }


class EmailOrUsernamePasswordResetForm(forms.Form):
    """
    Accepts either an email address or a username for password reset.
    Finds the user and sends the recovery email to their registered email address.
    """
    email = forms.CharField(
        label="Email or Username",
        max_length=254,
        widget=forms.TextInput(attrs={
            'class': 'form-control border-start-0 ps-0',
            'placeholder': 'Enter your email or username',
            'autofocus': True,
        })
    )

    def clean_email(self):
        return self.cleaned_data['email'].strip()

    def get_users(self, email_or_username):
        from django.contrib.auth import get_user_model
        from django.db.models import Q
        UserModel = get_user_model()
        active_users = UserModel._default_manager.filter(
            Q(email__iexact=email_or_username) | Q(username__iexact=email_or_username),
            is_active=True,
        )
        return (
            u for u in active_users
            if u.has_usable_password() and u.email and u.email.strip()
        )

    def save(
        self,
        domain_override=None,
        subject_template_name='registration/password_reset_subject.txt',
        email_template_name='registration/password_reset_email.txt',
        use_https=False,
        token_generator=None,
        from_email=None,
        request=None,
        html_email_template_name=None,
        extra_email_context=None,
    ):
        """
        Generates a one-use only link for resetting password and sends to the user.
        """
        from django.contrib.auth.tokens import default_token_generator
        from django.contrib.auth.forms import PasswordResetForm
        if token_generator is None:
            token_generator = default_token_generator
        f = PasswordResetForm()
        f.get_users = self.get_users
        f.is_bound = True
        f.cleaned_data = {'email': self.cleaned_data['email']}
        return f.save(
            domain_override=domain_override,
            subject_template_name=subject_template_name,
            email_template_name=email_template_name,
            use_https=use_https,
            token_generator=token_generator,
            from_email=from_email,
            request=request,
            html_email_template_name=html_email_template_name,
            extra_email_context=extra_email_context,
        )


