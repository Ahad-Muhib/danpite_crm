from django.contrib.auth.models import User
from django.db import models


CURRENCY_CHOICES = [
    ('USD', 'USD ($)'),
    ('BDT', 'BDT (৳)'),
    ('EUR', 'EUR (€)'),
    ('GBP', 'GBP (£)'),
    ('INR', 'INR (₹)'),
    ('CAD', 'CAD (C$)'),
    ('AUD', 'AUD (A$)'),
    ('SGD', 'SGD (S$)'),
    ('MYR', 'MYR (RM)'),
    ('AED', 'AED (د.إ)'),
    ('SAR', 'SAR (﷼)'),
    ('JPY', 'JPY (¥)'),
    ('CNY', 'CNY (¥)'),
    ('KRW', 'KRW (₩)'),
    ('THB', 'THB (฿)'),
    ('PHP', 'PHP (₱)'),
    ('IDR', 'IDR (Rp)'),
    ('PKR', 'PKR (₨)'),
    ('LKR', 'LKR (Rs)'),
    ('NGN', 'NGN (₦)'),
    ('ZAR', 'ZAR (R)'),
    ('BRL', 'BRL (R$)'),
    ('MXN', 'MXN ($)'),
    ('TRY', 'TRY (₺)'),
    ('RUB', 'RUB (₽)'),
    ('SEK', 'SEK (kr)'),
    ('NOK', 'NOK (kr)'),
    ('DKK', 'DKK (kr)'),
    ('CHF', 'CHF (CHF)'),
    ('PLN', 'PLN (zł)'),
]

CURRENCY_SYMBOLS = {
    'USD': '$', 'BDT': '৳', 'EUR': '€', 'GBP': '£', 'INR': '₹',
    'CAD': 'C$', 'AUD': 'A$', 'SGD': 'S$', 'MYR': 'RM', 'AED': 'د.إ',
    'SAR': '﷼', 'JPY': '¥', 'CNY': '¥', 'KRW': '₩', 'THB': '฿',
    'PHP': '₱', 'IDR': 'Rp', 'PKR': '₨', 'LKR': 'Rs', 'NGN': '₦',
    'ZAR': 'R', 'BRL': 'R$', 'MXN': '$', 'TRY': '₺', 'RUB': '₽',
    'SEK': 'kr', 'NOK': 'kr', 'DKK': 'kr', 'CHF': 'CHF', 'PLN': 'zł',
}


class CurrencySettings(models.Model):
    currency_code = models.CharField(max_length=10, choices=CURRENCY_CHOICES, default='BDT')

    class Meta:
        verbose_name = 'Currency Settings'
        verbose_name_plural = 'Currency Settings'

    def __str__(self):
        return self.get_currency_code_display()

    @property
    def symbol(self):
        return CURRENCY_SYMBOLS.get(self.currency_code, self.currency_code)

    def save(self, *args, **kwargs):
        if not self.pk and CurrencySettings.objects.exists():
            raise ValueError('Only one currency settings instance is allowed.')
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class SiteSettings(models.Model):
    logo_image = models.ImageField(upload_to='logos/', blank=True, null=True)

    class Meta:
        verbose_name = 'Site Settings'
        verbose_name_plural = 'Site Settings'

    def save(self, *args, **kwargs):
        if not self.pk and SiteSettings.objects.exists():
            raise ValueError('Only one site settings instance is allowed.')
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class Task(models.Model):
    PRIORITY = [('low', 'Low'), ('medium', 'Medium'), ('high', 'High')]
    STATUS = [('pending', 'Pending'), ('in_progress', 'In Progress'), ('completed', 'Completed')]
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    priority = models.CharField(max_length=20, choices=PRIORITY, default='medium')
    status = models.CharField(max_length=20, choices=STATUS, default='pending')
    assigned_to = models.ForeignKey('hr.Employee', null=True, blank=True, on_delete=models.SET_NULL, related_name='tasks')
    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class Project(models.Model):
    STATUS = [('not_started', 'Not Started'), ('in_progress', 'In Progress'), ('completed', 'Completed'), ('on_hold', 'On Hold')]
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default='not_started')
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    manager = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='projects')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Log(models.Model):
    ACTION = [('create', 'Create'), ('update', 'Update'), ('delete', 'Delete')]
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='global_logs')
    action = models.CharField(max_length=10, choices=ACTION)
    model_name = models.CharField(max_length=100)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    object_repr = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_action_display()}] {self.model_name} #{self.object_id} by {self.user}"


def log_action(request, action, model_name, obj, description=''):
    Log.objects.create(
        user=request.user,
        action=action,
        model_name=model_name,
        object_id=obj.pk,
        object_repr=str(obj)[:200],
        description=description,
    )


class Schedule(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    location = models.CharField(max_length=200, blank=True)
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='schedules')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

