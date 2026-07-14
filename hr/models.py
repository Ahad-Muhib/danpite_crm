from django.contrib.auth.models import User
from django.db import models


class Department(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Designation(models.Model):
    title = models.CharField(max_length=100)
    department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Employee(models.Model):
    ROLE = [('employee', 'Employee'), ('manager', 'Manager'), ('hr', 'HR'), ('admin', 'Administrator')]
    STATUS = [('active', 'Active'), ('inactive', 'Inactive'), ('on_leave', 'On Leave')]
    user = models.OneToOneField(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='employee_profile')
    employee_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    role = models.CharField(max_length=20, choices=ROLE, default='employee')
    designation = models.ForeignKey(Designation, null=True, blank=True, on_delete=models.SET_NULL)
    department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.SET_NULL)
    reporting_to = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='reports')
    status = models.CharField(max_length=20, choices=STATUS, default='active')
    joining_date = models.DateField(null=True, blank=True)
    salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    address = models.TextField(blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    is_new_hire = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.employee_id:
            last = Employee.objects.order_by('id').last()
            self.employee_id = f"EMP{(last.id + 1 if last else 1):04d}"
        super().save(*args, **kwargs)


class Leave(models.Model):
    TYPES = [('casual', 'Casual'), ('sick', 'Sick'), ('earned', 'Earned'), ('maternity', 'Maternity'), ('other', 'Other')]
    STATUS = [('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')]
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leaves')
    leave_type = models.CharField(max_length=20, choices=TYPES, default='casual')
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default='pending')
    approved_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.employee} - {self.leave_type}"


class Attendance(models.Model):
    STATUS = [('present', 'Present'), ('absent', 'Absent'), ('late', 'Late'), ('half_day', 'Half Day')]
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField()
    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default='present')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.employee} - {self.date}"

