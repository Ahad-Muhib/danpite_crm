from collections import OrderedDict
from datetime import datetime

from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth
from django.shortcuts import render

from accounts.models import Invoice, Payment, Expense, BankAccount
from core.models import Project


def _dates(request):
    f = request.GET.get('from', '')
    t = request.GET.get('to', '')
    return f, t


def income_report(request):
    f, t = _dates(request)
    payments = Payment.objects.all().order_by('-payment_date')
    if f:
        payments = payments.filter(payment_date__gte=f)
    if t:
        payments = payments.filter(payment_date__lte=t)
    total_income = payments.aggregate(Sum('amount'))['amount__sum'] or 0
    invoiced_income = payments.filter(invoice__isnull=False).aggregate(Sum('amount'))['amount__sum'] or 0
    direct_income = total_income - invoiced_income
    return render(request, 'accounts/reports/income_report.html', {
        'payments': payments, 'total_income': total_income, 'invoiced_income': invoiced_income,
        'direct_income': direct_income, 'from': f, 'to': t,
    })


def expense_report(request):
    f, t = _dates(request)
    cat = request.GET.get('category', '')
    expenses = Expense.objects.all().order_by('-expense_date')
    if f:
        expenses = expenses.filter(expense_date__gte=f)
    if t:
        expenses = expenses.filter(expense_date__lte=t)
    if cat:
        expenses = expenses.filter(category=cat)
    total = expenses.aggregate(Sum('amount'))['amount__sum'] or 0
    categories = Expense.objects.values_list('category', flat=True).distinct().order_by('category')
    return render(request, 'accounts/reports/expense_report.html', {
        'expenses': expenses, 'total_expense': total, 'categories': categories,
        'from': f, 'to': t, 'selected_category': cat,
    })


def balance_report(request):
    f, t = _dates(request)
    payments = Payment.objects.all()
    expenses = Expense.objects.all()
    if f:
        payments = payments.filter(payment_date__gte=f)
        expenses = expenses.filter(expense_date__gte=f)
    if t:
        payments = payments.filter(payment_date__lte=t)
        expenses = expenses.filter(expense_date__lte=t)
    total_income = payments.aggregate(Sum('amount'))['amount__sum'] or 0
    total_expense = expenses.aggregate(Sum('amount'))['amount__sum'] or 0
    net = total_income - total_expense
    bank_accounts = BankAccount.objects.filter(is_active=True)
    return render(request, 'accounts/reports/balance_report.html', {
        'total_income': total_income, 'total_expense': total_expense, 'net_balance': net,
        'bank_accounts': bank_accounts, 'from': f, 'to': t,
    })


def bank_details(request):
    accounts = BankAccount.objects.all().order_by('bank_name', 'account_name')
    return render(request, 'accounts/reports/bank_details.html', {'accounts': accounts})


def sales_report(request):
    f, t = _dates(request)
    sel_month = request.GET.get('month', '')

    payments_qs = Payment.objects.all()
    expenses_qs = Expense.objects.all()
    projects_qs = Project.objects.filter(status='completed')
    if f:
        payments_qs = payments_qs.filter(payment_date__gte=f)
        expenses_qs = expenses_qs.filter(expense_date__gte=f)
        projects_qs = projects_qs.filter(end_date__gte=f)
    if t:
        payments_qs = payments_qs.filter(payment_date__lte=t)
        expenses_qs = expenses_qs.filter(expense_date__lte=t)
        projects_qs = projects_qs.filter(end_date__lte=t)

    monthly_income = payments_qs.annotate(month=TruncMonth('payment_date')).values('month').annotate(total=Sum('amount')).order_by('-month')
    monthly_expense = expenses_qs.annotate(month=TruncMonth('expense_date')).values('month').annotate(total=Sum('amount')).order_by('-month')
    monthly_projects = projects_qs.annotate(month=TruncMonth('end_date')).values('month').annotate(count=Count('id')).order_by('-month')

    months = set()
    inc_map, exp_map, proj_map = {}, {}, {}
    for r in monthly_income:
        months.add(r['month']); inc_map[r['month']] = r['total']
    for r in monthly_expense:
        months.add(r['month']); exp_map[r['month']] = r['total']
    for r in monthly_projects:
        months.add(r['month']); proj_map[r['month']] = r['count']

    report_data = []
    for m in sorted(months, reverse=True):
        report_data.append({'month': m, 'income': inc_map.get(m, 0), 'expense': exp_map.get(m, 0), 'net': inc_map.get(m, 0) - exp_map.get(m, 0), 'projects': proj_map.get(m, 0)})

    month_invoices, month_expenses, month_projects = [], [], []
    selected_month_display = ''
    if sel_month:
        try:
            dt = datetime.strptime(sel_month, '%Y-%m-%d')
            selected_month_display = dt.strftime('%B %Y')
            month_invoices = Invoice.objects.filter(invoice_date__year=dt.year, invoice_date__month=dt.month).order_by('-invoice_date')
            month_expenses = Expense.objects.filter(expense_date__year=dt.year, expense_date__month=dt.month).order_by('-expense_date')
            month_projects = Project.objects.filter(status='completed', end_date__year=dt.year, end_date__month=dt.month).order_by('-end_date')
        except ValueError:
            pass

    return render(request, 'accounts/reports/sales_report.html', {
        'report_data': report_data, 'selected_month': sel_month,
        'selected_month_display': selected_month_display,
        'month_invoices': month_invoices, 'month_expenses': month_expenses, 'month_projects': month_projects,
        'from': f, 'to': t,
    })
