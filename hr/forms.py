from django import forms
from django.contrib.auth.models import User
from django.utils.crypto import get_random_string

from .models import Attendance, Employee, Leave


class EmployeeForm(forms.ModelForm):
    create_login = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Create Login Account',
        help_text='Generate login credentials for this employee (Admin/Manager roles only).',
    )

    class Meta:
        model = Employee
        fields = ['name', 'email', 'phone', 'role', 'designation', 'department', 'reporting_to', 'status', 'joining_date', 'salary', 'address', 'avatar', 'is_new_hire']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'designation': forms.Select(attrs={'class': 'form-select'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'reporting_to': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'joining_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'salary': forms.NumberInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'avatar': forms.FileInput(attrs={'class': 'form-control'}),
            'is_new_hire': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')
        super().__init__(*args, **kwargs)
        if instance and instance.user:
            self.fields['create_login'].initial = True
            self.fields['create_login'].widget.attrs['disabled'] = True

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        create_login = cleaned_data.get('create_login')
        if create_login and role not in ('admin', 'manager'):
            raise forms.ValidationError('Login accounts can only be created for Admin or Manager roles.')
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=commit)
        if commit:
            create_login = self.cleaned_data.get('create_login')
            if create_login and not instance.user and instance.role in ('admin', 'manager'):
                username = instance.email
                if User.objects.filter(username=username).exists():
                    username = f"{instance.email.split('@')[0]}_{instance.employee_id}"
                raw_password = get_random_string(length=10)
                user = User.objects.create_user(
                    username=username,
                    email=instance.email,
                    password=raw_password,
                    first_name=instance.name.split()[0] if instance.name else '',
                    last_name=' '.join(instance.name.split()[1:]) if instance.name and len(instance.name.split()) > 1 else '',
                )
                instance.user = user
                instance.save()
                instance._raw_password = raw_password
        return instance


class LeaveForm(forms.ModelForm):
    class Meta:
        model = Leave
        fields = ['employee', 'leave_type', 'start_date', 'end_date', 'reason']
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-select'}),
            'leave_type': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class AttendanceForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = ['employee', 'date', 'check_in', 'check_out', 'status', 'notes']
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'check_in': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'check_out': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

