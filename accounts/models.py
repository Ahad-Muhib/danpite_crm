from datetime import date
from django.contrib.auth.models import User
from django.db import models
from django.core.validators import MinValueValidator

from clients.models import Client


CURRENCY_CHOICES = [
    ('USD', 'USD — $'),
    ('BDT', 'BDT — ৳'),
    ('EUR', 'EUR — €'),
    ('GBP', 'GBP — £'),
    ('INR', 'INR — ₹'),
    ('JPY', 'JPY — ¥'),
    ('CAD', 'CAD — C$'),
    ('AUD', 'AUD — A$'),
    ('AED', 'AED — د.إ'),
    ('SAR', 'SAR — ر.س'),
]

CURRENCY_SYMBOLS = {
    'USD': '$', 'BDT': '৳', 'EUR': '€', 'GBP': '£',
    'INR': '₹', 'JPY': '¥', 'CAD': 'C$', 'AUD': 'A$',
    'AED': 'د.إ', 'SAR': 'ر.س',
}

METHOD_CHOICES = [
    ('cash', 'Cash'), ('bank', 'Bank'), ('check', 'Check'),
    ('cheque', 'Cheque'), ('card', 'Card'), ('online', 'Online'), ('bkash', 'bKash'),
    ('nagad', 'Nagad'), ('rocket', 'Rocket'), ('upay', 'Upay'),
]


class Invoice(models.Model):
    STATUS = [('draft', 'Draft'), ('sent', 'Sent'), ('paid', 'Paid'), ('overdue', 'Overdue'), ('cancelled', 'Cancelled')]
    code = models.CharField(max_length=50, unique=True, blank=True)
    logo = models.ImageField(upload_to='invoice_logos/', null=True, blank=True)
    currency = models.CharField(max_length=5, choices=CURRENCY_CHOICES, default='BDT')
    bill_from_company = models.CharField(max_length=200, blank=True)
    bill_from_address = models.TextField(blank=True)
    bill_from_phone = models.CharField(max_length=30, blank=True)
    bill_to_name = models.CharField(max_length=200, blank=True)
    client = models.ForeignKey(Client, null=True, blank=True, on_delete=models.SET_NULL, related_name='invoices')
    phone = models.CharField(max_length=30, blank=True)
    ship_to = models.TextField(blank=True)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    shipping = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    invoice_date = models.DateField(null=True, blank=True)
    delivery_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default='draft')
    received_payment = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    terms = models.TextField(blank=True)
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.code

    def save(self, *args, **kwargs):
        if not self.code:
            last = Invoice.objects.order_by('id').last()
            self.code = f"INV-{(last.id + 1 if last else 1):04d}"
        super().save(*args, **kwargs)

    @property
    def balance_due(self):
        from django.db.models import Sum
        total_paid = self.payments.aggregate(s=Sum('amount'))['s'] or 0
        return self.total - total_paid

    @property
    def is_fully_paid(self):
        return self.balance_due <= 0


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    description = models.CharField(max_length=300)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        self.total = self.quantity * self.unit_price
        super().save(*args, **kwargs)


class AccountType(models.Model):
    key = models.CharField(max_length=20, unique=True)
    label = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['key']

    def __str__(self):
        return self.label


class AccountCategory(models.Model):
    name = models.CharField(max_length=50, unique=True)
    account_type = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['account_type', 'name']
        verbose_name_plural = 'Account Categories'

    def __str__(self):
        return self.name


class BankAccount(models.Model):
    BANK_TYPES = [('savings', 'Savings'), ('current', 'Current'), ('fixed', 'Fixed Deposit'), ('other', 'Other')]
    MOBILE_TYPES = [('personal', 'Personal'), ('agent', 'Agent')]
    MOBILE_PROVIDERS = [('bkash', 'bKash'), ('nagad', 'Nagad'), ('upay', 'Upay'), ('rocket', 'Rocket')]

    account_category = models.ForeignKey(AccountCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='accounts')
    mobile_provider = models.CharField(max_length=20, choices=MOBILE_PROVIDERS, blank=True)

    # Bank fields
    bank_name = models.CharField(max_length=200, blank=True)
    account_name = models.CharField(max_length=200, blank=True)
    account_number = models.CharField(max_length=100, blank=True)
    account_type = models.CharField(max_length=20, choices=BANK_TYPES, default='current')
    branch = models.CharField(max_length=200, blank=True)
    routing_number = models.CharField(max_length=100, blank=True)

    # Mobile fields
    mobile_number = models.CharField(max_length=50, blank=True)
    holder_name = models.CharField(max_length=200, blank=True)
    mobile_type = models.CharField(max_length=10, choices=MOBILE_TYPES, default='personal')

    # Card fields (for bank-type card categories)
    card_number = models.CharField(max_length=50, blank=True)
    card_holder_name = models.CharField(max_length=200, blank=True)

    # Cash fields
    contact_number = models.CharField(max_length=50, blank=True)
    currency = models.CharField(max_length=5, blank=True, default='BDT')

    # Common
    opening_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    details = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def available_balance(self):
        from django.db.models import Sum
        total_payments = self.payments.aggregate(s=Sum('amount'))['s'] or 0
        total_expenses = self.expenses.aggregate(s=Sum('amount'))['s'] or 0
        transfers_out = self.transfers_out.aggregate(s=Sum('amount'))['s'] or 0
        transfers_in = self.transfers_in.aggregate(s=Sum('amount'))['s'] or 0
        return self.opening_balance + total_payments - total_expenses - transfers_out + transfers_in

    @property
    def display_name(self):
        cat = self.account_category
        if not cat:
            return 'Uncategorized'
        if cat.name.lower() == 'card' and cat.account_type == 'bank':
            parts = [p for p in [self.card_holder_name, self.card_number, self.bank_name] if p]
            return ' - '.join(parts) if parts else 'Card'
        if cat.account_type == 'bank':
            parts = [p for p in [self.bank_name, self.account_name, self.account_number] if p]
            return ' - '.join(parts) if parts else cat.name
        elif cat.account_type == 'mobile':
            return f"{self.get_mobile_provider_display() or cat.name} - {self.mobile_number or '(no number)'}"
        elif cat.account_type == 'cash':
            parts = [p for p in ['Cash', self.contact_number] if p]
            return ' - '.join(parts)
        return cat.name

    def __str__(self):
        return self.display_name


class ExpenseCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


PREDEFINED_EXPENSE_CATEGORIES = ['Office Supplies', 'Marketing', 'Travel', 'Utilities', 'Rent', 'Salary', 'Equipment', 'Other']

EXPENSE_CATEGORY_CHOICES = [('office', 'Office Supplies'), ('travel', 'Travel'), ('marketing', 'Marketing'), ('utilities', 'Utilities'), ('salary', 'Salary'), ('rent', 'Rent'), ('equipment', 'Equipment'), ('other', 'Other')]

CATEGORY_KEY_MAP = {label.lower(): key for key, label in EXPENSE_CATEGORY_CHOICES}


class Expense(models.Model):
    CATEGORY = EXPENSE_CATEGORY_CHOICES
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=30, choices=CATEGORY, default='other')
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default='cash')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    expense_date = models.DateField()
    bank_account = models.ForeignKey('BankAccount', null=True, blank=True, on_delete=models.SET_NULL, related_name='expenses')
    description = models.TextField(blank=True)
    receipt = models.FileField(upload_to='receipts/', null=True, blank=True)
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Payment(models.Model):
    METHOD = METHOD_CHOICES
    invoice = models.ForeignKey(Invoice, null=True, blank=True, on_delete=models.SET_NULL, related_name='payments')
    client = models.ForeignKey(Client, null=True, blank=True, on_delete=models.SET_NULL, related_name='payments')
    account = models.ForeignKey('BankAccount', null=True, blank=True, on_delete=models.SET_NULL, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0.01)])
    payment_date = models.DateField()
    method = models.CharField(max_length=20, choices=METHOD, default='cash')
    reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    receipt = models.FileField(upload_to='receipts/', null=True, blank=True)
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.amount} - {self.payment_date}"


class Transfer(models.Model):
    from_account = models.ForeignKey(BankAccount, on_delete=models.CASCADE, related_name='transfers_out')
    to_account = models.ForeignKey(BankAccount, on_delete=models.CASCADE, related_name='transfers_in')
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0.01)])
    transfer_date = models.DateField()
    reference = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    receipt = models.FileField(upload_to='receipts/', null=True, blank=True)
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.from_account} → {self.to_account}: {self.amount}"


DEFAULT_CRM_FEATURES = [
    "Dashboard",
    "User Management",
    "Role & Permission Management",
    "Branch Management",
    "Activity Management",
    "Follow-up Management",
    "Lead Management",
    "Quotation Management",
    "Sales Management",
    "Product Category & Subcategory Management",
    "Brand Management",
    "Organization Management",
    "Organization Category & Type Management",
    "Division, District, Upazila & Union Management",
    "Sales Report",
    "Leads Report",
    "Project Report",
    "Activity Report",
    "Business Settings",
]

DEFAULT_HRM_FEATURES = [
    "Employee Management",
    "Department & Designation",
    "Attendance Management",
    "Leave Management",
    "Holiday Management",
    "Payroll & Payslip",
    "Salary Advance",
    "Employee Documents",
    "Notice & Announcement",
    "Employee Performance",
    "Resignation & Exit Management",
    "HRM Reports",
]

DEFAULT_MOBILE_FEATURES = [
    "Dashboard",
    "Lead Management",
    "Follow-up Management",
    "Customer Management",
    "Organization Management",
    "Activity & Task Management",
    "Quotation Management",
    "Sales Management",
    "Product Management",
    "Employee Management",
    "Attendance Management",
    "Leave Management",
    "Payroll Management",
]

DEFAULT_SYSTEM_FEATURES = [
    "Performance Management",
    "Reports & Analytics",
    "Calendar & Schedule",
    "Notifications",
    "Document Management",
    "Approval Center",
    "Settings",
]

DEFAULT_TECH_STACK = [
    "Frontend: Bootstrap, Laravel Blade, HTML, CSS, JavaScript, jQuery",
    "Backend: PHP Laravel (REST API)",
    "Mobile App: Flutter (Android & iOS)",
    "Database: MySQL",
    "Authentication: Laravel Sanctum",
    "Deployment: Linux, Apache/Nginx, Git, SSL",
]

DEFAULT_SECURITY_FEATURES = [
    "Multi-Factor Authentication (MFA)",
    "Role-Based Access Control (RBAC)",
    "End-to-End Data Encryption",
    "Secure REST API",
    "Audit Trail & Activity Logs",
    "Automated Backup & Disaster Recovery",
    "SSL/TLS Secure Communication",
    "Advanced Threat Protection",
]

DEFAULT_TRAINING_SUPPORT = [
    "Installation",
    "User Training",
    "Bug Fix Support",
    "Technical Support",
    "Pre-recorded Video",
    "Remote Assistance",
]

DEFAULT_DELIVERABLES = [
    "Web Application",
    "Android Mobile Application",
    "REST API",
    "Admin Panel",
    "Source Code (One-Time License Only)",
    "MySQL Database",
    "User Documentation",
]

DEFAULT_PRICING_PLANS = [
    {"package": "", "license": "", "price": "", "delivery_time": "", "is_selected": True},
]


def get_default_feature_sections():
    return []


def get_default_terms_sections():
    return [
        {"title": "Payment Terms", "content": ""},
        {"title": "Delivery & Support Policy", "content": ""},
        {"title": "Terms & Conditions", "content": ""},
        {"title": "Warranty Details", "content": ""},
        {"title": "Not Included / Exclusions", "content": ""},
        {"title": "Why Danpite Tech?", "content": ""},
    ]


DEFAULT_PAYMENT_TERMS = ""
DEFAULT_DELIVERY_SUPPORT = ""
DEFAULT_TERMS_CONDITIONS = ""
DEFAULT_WARRANTY = ""
DEFAULT_NOT_INCLUDED = ""
DEFAULT_WHY_DANPITE = ""


class Quotation(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    ]

    CURRENCY_CHOICES = [
        ('BDT', 'BDT (৳)'),
        ('USD', 'USD ($)'),
        ('EUR', 'EUR (€)'),
        ('GBP', 'GBP (£)'),
    ]

    code = models.CharField(max_length=50, unique=True, blank=True)
    quotation_date = models.DateField(default=date.today)
    valid_days = models.IntegerField(default=15)

    # Linked Client / Lead
    client = models.ForeignKey(Client, null=True, blank=True, on_delete=models.SET_NULL, related_name='quotations')
    lead = models.ForeignKey('leads.LeadContact', null=True, blank=True, on_delete=models.SET_NULL, related_name='quotations')

    # Recipient Information
    company_name = models.CharField(max_length=200, blank=True)
    contact_person = models.CharField(max_length=200, blank=True)
    designation = models.CharField(max_length=150, blank=True)
    contact_number = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)

    # Proposal Introduction
    subject = models.CharField(max_length=300, blank=True, default='')
    intro_letter = models.TextField(
        blank=True,
        default=''
    )

    # Feature Modules & Custom Scope Sections (Dynamic JSON list of {title, content})
    feature_sections = models.JSONField(default=list, blank=True)
    crm_features = models.JSONField(default=list, blank=True)
    hrm_features = models.JSONField(default=list, blank=True)
    mobile_app_features = models.JSONField(default=list, blank=True)
    system_features = models.JSONField(default=list, blank=True)
    tech_stack = models.JSONField(default=list, blank=True)
    security_features = models.JSONField(default=list, blank=True)
    training_support = models.JSONField(default=list, blank=True)
    deliverables = models.JSONField(default=list, blank=True)

    # Pricing Table & Terms
    pricing_plans = models.JSONField(default=list, blank=True)
    payment_terms = models.TextField(blank=True, default='')
    delivery_terms = models.TextField(blank=True, default='')
    terms_conditions = models.TextField(blank=True, default='')
    warranty = models.TextField(blank=True, default='')
    not_included = models.TextField(blank=True, default='')
    why_danpite = models.TextField(blank=True, default='')
    custom_terms = models.JSONField(default=list, blank=True)
    terms_sections = models.JSONField(default=list, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    currency = models.CharField(max_length=5, choices=CURRENCY_CHOICES, default='BDT')

    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-quotation_date', '-id']

    def __str__(self):
        return f"{self.code} - {self.company_name or (self.client.name if self.client else 'Quotation')}"

    def save(self, *args, **kwargs):
        if self.intro_letter:
            import re
            plain = re.sub(r'<[^>]*>', '', str(self.intro_letter)).replace('&nbsp;', ' ').replace('&#160;', ' ').strip()
            if not plain and not any(tag in str(self.intro_letter).lower() for tag in ('<img', '<hr', '<table', '<iframe')):
                self.intro_letter = ''
        if not self.code:
            import re
            existing_codes = Quotation.objects.values_list('code', flat=True)
            max_num = 0
            for c in existing_codes:
                m = re.search(r'(\d+)$', c or '')
                if m:
                    max_num = max(max_num, int(m.group(1)))
            candidate = max_num + 1
            while Quotation.objects.filter(code=f"DPT-CRM-{candidate:03d}").exists():
                candidate += 1
            self.code = f"DPT-CRM-{candidate:03d}"
        if not self.quotation_date:
            from datetime import date
            self.quotation_date = date.today()
        super().save(*args, **kwargs)
