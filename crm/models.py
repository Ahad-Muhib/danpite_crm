from django.db import models
from django.contrib.auth.models import User


# ──────────────────────────── CORE ────────────────────────────

class Task(models.Model):
    PRIORITY = [('low','Low'),('medium','Medium'),('high','High')]
    STATUS   = [('pending','Pending'),('in_progress','In Progress'),('completed','Completed')]
    title       = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    priority    = models.CharField(max_length=20, choices=PRIORITY, default='medium')
    status      = models.CharField(max_length=20, choices=STATUS, default='pending')
    assigned_to = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='tasks')
    due_date    = models.DateField(null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)
    def __str__(self): return self.title

class Project(models.Model):
    STATUS = [('not_started','Not Started'),('in_progress','In Progress'),('completed','Completed'),('on_hold','On Hold')]
    name        = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status      = models.CharField(max_length=20, choices=STATUS, default='not_started')
    start_date  = models.DateField(null=True, blank=True)
    end_date    = models.DateField(null=True, blank=True)
    manager     = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='projects')
    created_at  = models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.name

class Schedule(models.Model):
    title          = models.CharField(max_length=200)
    description    = models.TextField(blank=True)
    start_datetime = models.DateTimeField()
    end_datetime   = models.DateTimeField()
    location       = models.CharField(max_length=200, blank=True)
    created_by     = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='schedules')
    created_at     = models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.title


# ──────────────────────────── LEADS ────────────────────────────

class LeadContact(models.Model):
    SOURCE = [('none','None'),('cold_call','Cold Call'),('email','Email'),('website','Website'),('social','Social Media'),('referral','Referral'),('other','Other')]
    salutation  = models.CharField(max_length=10, blank=True)
    name        = models.CharField(max_length=200)
    email       = models.EmailField(blank=True)
    phone       = models.CharField(max_length=30, blank=True)
    company     = models.CharField(max_length=200, blank=True)
    website     = models.URLField(blank=True)
    address     = models.TextField(blank=True)
    lead_source = models.CharField(max_length=30, choices=SOURCE, default='none')
    lead_owner  = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='owned_leads')
    added_by    = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='added_leads')
    is_converted= models.BooleanField(default=False)
    notes       = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)
    def __str__(self): return self.name

class Deal(models.Model):
    PIPELINE = [('sales','Sales'),('marketing','Marketing'),('support','Support')]
    STAGE    = [('generated','Generated'),('qualified','Qualified'),('presentation','Presentation'),('negotiation','Negotiation'),('won','Won'),('lost','Lost')]
    lead_contact  = models.ForeignKey(LeadContact, null=True, blank=True, on_delete=models.SET_NULL, related_name='deals')
    deal_name     = models.CharField(max_length=200)
    pipeline      = models.CharField(max_length=30, choices=PIPELINE, default='sales')
    stage         = models.CharField(max_length=30, choices=STAGE, default='generated')
    value         = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency      = models.CharField(max_length=10, default='USD')
    close_date    = models.DateField(null=True, blank=True)
    deal_agent    = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='agent_deals')
    deal_watcher  = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='watched_deals')
    category      = models.CharField(max_length=100, blank=True)
    description   = models.TextField(blank=True)
    auto_convert  = models.BooleanField(default=False)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)
    def __str__(self): return self.deal_name


# ──────────────────────────── CLIENTS ────────────────────────────

class Client(models.Model):
    CATEGORY = [('food_restaurant','Food & Restaurant'),('health_medical','Health & Medical'),('technology','Technology'),('education','Education'),('retail','Retail'),('other','Other')]
    STATUS   = [('active','Active'),('inactive','Inactive')]
    name            = models.CharField(max_length=200)
    email           = models.EmailField(blank=True)
    phone           = models.CharField(max_length=30, blank=True)
    mobile          = models.CharField(max_length=30, blank=True)
    company         = models.CharField(max_length=200, blank=True)
    website         = models.URLField(blank=True)
    address         = models.TextField(blank=True)
    category        = models.CharField(max_length=30, choices=CATEGORY, blank=True)
    sub_category    = models.CharField(max_length=100, blank=True)
    status          = models.CharField(max_length=20, choices=STATUS, default='active')
    account_manager = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='managed_clients')
    notes           = models.TextField(blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)
    def __str__(self): return self.name


# ──────────────────────────── HR ────────────────────────────

class Department(models.Model):
    name        = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.name

class Designation(models.Model):
    title      = models.CharField(max_length=100)
    department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.title

class Employee(models.Model):
    ROLE   = [('employee','Employee'),('manager','Manager'),('hr','HR'),('admin','Administrator')]
    STATUS = [('active','Active'),('inactive','Inactive'),('on_leave','On Leave')]
    user         = models.OneToOneField(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='employee_profile')
    employee_id  = models.CharField(max_length=50, unique=True)
    name         = models.CharField(max_length=200)
    email        = models.EmailField()
    phone        = models.CharField(max_length=30, blank=True)
    role         = models.CharField(max_length=20, choices=ROLE, default='employee')
    designation  = models.ForeignKey(Designation, null=True, blank=True, on_delete=models.SET_NULL)
    department   = models.ForeignKey(Department, null=True, blank=True, on_delete=models.SET_NULL)
    reporting_to = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='reports')
    status       = models.CharField(max_length=20, choices=STATUS, default='active')
    joining_date = models.DateField(null=True, blank=True)
    salary       = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    address      = models.TextField(blank=True)
    avatar       = models.ImageField(upload_to='avatars/', null=True, blank=True)
    is_new_hire  = models.BooleanField(default=False)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)
    def __str__(self): return self.name
    def save(self, *args, **kwargs):
        if not self.employee_id:
            last = Employee.objects.order_by('id').last()
            self.employee_id = f"EMP{(last.id + 1 if last else 1):04d}"
        super().save(*args, **kwargs)

class Leave(models.Model):
    TYPES  = [('casual','Casual'),('sick','Sick'),('earned','Earned'),('maternity','Maternity'),('other','Other')]
    STATUS = [('pending','Pending'),('approved','Approved'),('rejected','Rejected')]
    employee   = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leaves')
    leave_type = models.CharField(max_length=20, choices=TYPES, default='casual')
    start_date = models.DateField()
    end_date   = models.DateField()
    reason     = models.TextField(blank=True)
    status     = models.CharField(max_length=20, choices=STATUS, default='pending')
    approved_by= models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return f"{self.employee} - {self.leave_type}"

class Attendance(models.Model):
    STATUS = [('present','Present'),('absent','Absent'),('late','Late'),('half_day','Half Day')]
    employee  = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='attendances')
    date      = models.DateField()
    check_in  = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)
    status    = models.CharField(max_length=20, choices=STATUS, default='present')
    notes     = models.TextField(blank=True)
    created_at= models.DateTimeField(auto_now_add=True)
    def __str__(self): return f"{self.employee} - {self.date}"


# ──────────────────────────── ACCOUNTS ────────────────────────────

class Invoice(models.Model):
    STATUS = [('draft','Draft'),('sent','Sent'),('paid','Paid'),('overdue','Overdue'),('cancelled','Cancelled')]
    code         = models.CharField(max_length=50, unique=True)
    client       = models.ForeignKey(Client, null=True, blank=True, on_delete=models.SET_NULL, related_name='invoices')
    project      = models.CharField(max_length=200, blank=True)
    total        = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax          = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount     = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    invoice_date = models.DateField()
    due_date     = models.DateField(null=True, blank=True)
    status       = models.CharField(max_length=20, choices=STATUS, default='draft')
    notes        = models.TextField(blank=True)
    created_by   = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)
    def __str__(self): return self.code
    def save(self, *args, **kwargs):
        if not self.code:
            last = Invoice.objects.order_by('id').last()
            self.code = f"INV-{(last.id + 1 if last else 1):04d}"
        super().save(*args, **kwargs)

class InvoiceItem(models.Model):
    invoice     = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    description = models.CharField(max_length=300)
    quantity    = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price  = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total       = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    def save(self, *args, **kwargs):
        self.total = self.quantity * self.unit_price
        super().save(*args, **kwargs)

class Payment(models.Model):
    METHOD = [('cash','Cash'),('bank_transfer','Bank Transfer'),('cheque','Cheque'),('card','Card'),('online','Online')]
    invoice      = models.ForeignKey(Invoice, null=True, blank=True, on_delete=models.SET_NULL, related_name='payments')
    client       = models.ForeignKey(Client, null=True, blank=True, on_delete=models.SET_NULL, related_name='payments')
    amount       = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateField()
    method       = models.CharField(max_length=20, choices=METHOD, default='cash')
    reference    = models.CharField(max_length=100, blank=True)
    notes        = models.TextField(blank=True)
    created_by   = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    created_at   = models.DateTimeField(auto_now_add=True)
    def __str__(self): return f"{self.amount} - {self.payment_date}"

class Expense(models.Model):
    CATEGORY = [('office','Office Supplies'),('travel','Travel'),('marketing','Marketing'),('utilities','Utilities'),('salary','Salary'),('rent','Rent'),('equipment','Equipment'),('other','Other')]
    title        = models.CharField(max_length=200)
    category     = models.CharField(max_length=30, choices=CATEGORY, default='other')
    amount       = models.DecimalField(max_digits=12, decimal_places=2)
    expense_date = models.DateField()
    description  = models.TextField(blank=True)
    receipt      = models.FileField(upload_to='receipts/', null=True, blank=True)
    created_by   = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    created_at   = models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.title

class BankAccount(models.Model):
    TYPES = [('savings','Savings'),('current','Current'),('fixed','Fixed Deposit'),('other','Other')]
    bank_name       = models.CharField(max_length=200)
    account_name    = models.CharField(max_length=200)
    account_number  = models.CharField(max_length=100)
    account_type    = models.CharField(max_length=20, choices=TYPES, default='current')
    branch          = models.CharField(max_length=200, blank=True)
    routing_number  = models.CharField(max_length=100, blank=True)
    opening_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    is_active       = models.BooleanField(default=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    def __str__(self): return f"{self.bank_name} - {self.account_number}"


# ──────────────────────────── ORDERS ────────────────────────────

class Order(models.Model):
    STATUS = [('pending','Pending'),('processing','Processing'),('shipped','Shipped'),('delivered','Delivered'),('cancelled','Cancelled')]
    order_number  = models.CharField(max_length=50, unique=True)
    client        = models.ForeignKey(Client, null=True, blank=True, on_delete=models.SET_NULL, related_name='orders')
    status        = models.CharField(max_length=20, choices=STATUS, default='pending')
    total         = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes         = models.TextField(blank=True)
    assigned_to   = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    order_date    = models.DateField(auto_now_add=True)
    delivery_date = models.DateField(null=True, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)
    def __str__(self): return self.order_number
    def save(self, *args, **kwargs):
        if not self.order_number:
            last = Order.objects.order_by('id').last()
            self.order_number = f"ORD-{(last.id + 1 if last else 1):04d}"
        super().save(*args, **kwargs)

class OrderItem(models.Model):
    order        = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product_name = models.CharField(max_length=200)
    quantity     = models.PositiveIntegerField(default=1)
    unit_price   = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total        = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    def save(self, *args, **kwargs):
        self.total = self.quantity * self.unit_price
        super().save(*args, **kwargs)
