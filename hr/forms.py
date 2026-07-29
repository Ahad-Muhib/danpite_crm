from django import forms
from django.contrib.auth.models import User
from django.utils.crypto import get_random_string

from .models import Attendance, Employee, EmployeeRole, Leave


class EmployeeForm(forms.ModelForm):
    create_login = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Create Login Account',
    )
    login_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Set a password'}),
        label='Password',
        help_text='Leave blank to auto-generate.',
    )

    class Meta:
        model = Employee
        fields = ['name', 'email', 'phone', 'role', 'status', 'joining_date', 'salary', 'address', 'notes', 'avatar', 'is_new_hire']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'joining_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'salary': forms.NumberInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'avatar': forms.FileInput(attrs={'class': 'form-control'}),
            'is_new_hire': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        request_user = kwargs.pop('request_user', None)
        instance = kwargs.get('instance')
        super().__init__(*args, **kwargs)
        is_admin_user = request_user and (
            request_user.is_superuser
            or getattr(getattr(request_user, 'employee_profile', None), 'role', None) == 'admin'
        )
        if instance and instance.user:
            self.fields['create_login'].initial = True
            self.fields['create_login'].widget.attrs['disabled'] = True
            if not is_admin_user:
                self.fields['login_password'].widget.attrs['disabled'] = True
            else:
                self.fields['login_password'].widget.attrs.pop('disabled', None)
                self.fields['login_password'].help_text = 'Leave blank to keep current password.'
        base_choices = [('', '-- Select Role --')]
        hardcoded = [
            ('employee', 'Employee'), ('manager', 'Manager'),
            ('hr', 'HR'), ('admin', 'Administrator'),
        ]
        base_choices.extend(hardcoded)
        for r in EmployeeRole.objects.all():
            base_choices.append((r.name, r.name))
        self.fields['role'] = forms.ChoiceField(
            choices=base_choices,
            widget=forms.Select(attrs={'class': 'form-select'}),
        )

    def save(self, commit=True):
        instance = super().save(commit=commit)
        if commit:
            create_login = self.cleaned_data.get('create_login')
            if create_login and not instance.user:
                username = instance.email
                if User.objects.filter(username=username).exists():
                    username = f"{instance.email.split('@')[0]}_{instance.employee_id}"
                raw_password = self.cleaned_data.get('login_password') or get_random_string(length=10)
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
            elif instance.user and self.cleaned_data.get('login_password'):
                instance.user.set_password(self.cleaned_data['login_password'])
                instance.user.save()
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

