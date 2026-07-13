from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Sum
from django.db import transaction
from django.shortcuts import redirect, render

from .forms import AccountEntryForm, ClientForm, ExpenseForm, InvoiceForm, PaymentForm, StaffProfileForm
from .models import AccountEntry, Client, Expense, Invoice, Payment, StaffProfile


def staff_only(view_func):
    return user_passes_test(lambda user: user.is_staff)(view_func)


@login_required
def dashboard(request):
    invoice_total = Invoice.objects.aggregate(total=Sum("subtotal"))["total"] or Decimal("0")
    paid_total = Payment.objects.aggregate(total=Sum("amount"))["total"] or Decimal("0")
    expense_total = Expense.objects.aggregate(total=Sum("amount"))["total"] or Decimal("0")
    accounts_total = AccountEntry.objects.aggregate(total=Sum("amount"))["total"] or Decimal("0")
    context = {
        "staff_count": StaffProfile.objects.count(),
        "client_count": Client.objects.count(),
        "invoice_count": Invoice.objects.count(),
        "payment_count": Payment.objects.count(),
        "expense_count": Expense.objects.count(),
        "invoice_total": invoice_total,
        "paid_total": paid_total,
        "expense_total": expense_total,
        "accounts_total": accounts_total,
    }
    return render(request, "dashboard.html", context)


@login_required
@staff_only
def staff_list(request):
    staff_members = StaffProfile.objects.select_related("user").order_by("user__first_name", "user__last_name")
    return render(request, "crm/staff_list.html", {"staff_members": staff_members})


@login_required
@staff_only
def staff_create(request):
    if request.method == "POST":
        form = StaffProfileForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data["username"],
                email=form.cleaned_data["email"],
                password=form.cleaned_data["password"],
                first_name=form.cleaned_data["first_name"],
                last_name=form.cleaned_data["last_name"],
            )
            user.is_staff = True
            user.is_active = form.cleaned_data["is_active"]
            user.save(update_fields=["is_staff", "is_active"])
            StaffProfile.objects.create(
                user=user,
                phone=form.cleaned_data["phone"],
                job_title=form.cleaned_data["job_title"],
                is_active=form.cleaned_data["is_active"],
            )
            messages.success(request, "Staff member created.")
            return redirect("staff-list")
    else:
        form = StaffProfileForm()
    return render(request, "crm/staff_form.html", {"form": form})


@login_required
def client_list(request):
    clients = Client.objects.annotate(invoice_count=Count("invoices")).order_by("name")
    return render(request, "crm/client_list.html", {"clients": clients})


@login_required
@staff_only
def client_create(request):
    if request.method == "POST":
        form = ClientForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Client saved.")
            return redirect("client-list")
    else:
        form = ClientForm()
    return render(request, "crm/client_form.html", {"form": form})


@login_required
def invoice_list(request):
    invoices = Invoice.objects.select_related("client").all()
    return render(request, "crm/invoice_list.html", {"invoices": invoices})


@login_required
@staff_only
def invoice_create(request):
    if request.method == "POST":
        form = InvoiceForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Invoice saved.")
            return redirect("invoice-list")
    else:
        form = InvoiceForm()
    return render(request, "crm/invoice_form.html", {"form": form})


@login_required
def payment_list(request):
    payments = Payment.objects.select_related("invoice", "invoice__client")
    return render(request, "crm/payment_list.html", {"payments": payments})


@login_required
@staff_only
def payment_create(request):
    if request.method == "POST":
        form = PaymentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Payment saved.")
            return redirect("payment-list")
    else:
        form = PaymentForm()
    return render(request, "crm/payment_form.html", {"form": form})


@login_required
def expense_list(request):
    expenses = Expense.objects.all()
    return render(request, "crm/expense_list.html", {"expenses": expenses})


@login_required
@staff_only
def expense_create(request):
    if request.method == "POST":
        form = ExpenseForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                expense = form.save()
                AccountEntry.objects.create(
                    date=expense.date,
                    entry_type=AccountEntry.EntryType.EXPENSE,
                    title=expense.title,
                    amount=expense.amount,
                    description=expense.notes,
                )
            messages.success(request, "Expense saved.")
            return redirect("expense-list")
    else:
        form = ExpenseForm()
    return render(request, "crm/expense_form.html", {"form": form})


@login_required
def account_list(request):
    entries = AccountEntry.objects.all()
    balance = Decimal("0")
    for entry in entries:
        if entry.entry_type == AccountEntry.EntryType.INCOME:
            balance += entry.amount
        else:
            balance -= entry.amount
    return render(request, "crm/account_list.html", {"entries": entries, "balance": balance})


@login_required
@staff_only
def account_create(request):
    if request.method == "POST":
        form = AccountEntryForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                account_entry = form.save()
                if account_entry.entry_type == AccountEntry.EntryType.EXPENSE:
                    Expense.objects.create(
                        date=account_entry.date,
                        title=account_entry.title,
                        amount=account_entry.amount,
                        notes=account_entry.description,
                    )
            messages.success(request, "Account entry saved.")
            return redirect("account-list")
    else:
        form = AccountEntryForm()
    return render(request, "crm/account_form.html", {"form": form})
