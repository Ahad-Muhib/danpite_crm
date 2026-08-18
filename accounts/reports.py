from collections import OrderedDict
from datetime import datetime
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import render
from django.template.loader import render_to_string

from accounts.models import Invoice, Payment, Expense, BankAccount, ExpenseCategory, AccountCategory, CATEGORY_KEY_MAP
from core.models import Project


def financial_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        from core.views import get_user_role
        if get_user_role(request.user) not in ('admin', 'manager', 'staff'):
            return HttpResponseForbidden('You do not have permission to view financial reports.')
        return view_func(request, *args, **kwargs)
    return _wrapped


def _dates(request):
    f = request.GET.get('from', '')
    t = request.GET.get('to', '')
    return f, t


METHOD_LABELS = {
    'cash': 'Cash', 'bank': 'Bank', 'cheque': 'Cheque', 'check': 'Check',
    'card': 'Card', 'online': 'Online', 'bkash': 'bKash', 'nagad': 'Nagad', 'rocket': 'Rocket',
    'upay': 'Upay', 'mobile': 'Mobile', 'other': 'Other',
}
METHOD_ORDER = ['cash', 'bank', 'check', 'cheque', 'card', 'online', 'bkash', 'nagad', 'rocket', 'upay', 'mobile', 'other']


def _method_choices_from(keys):
    methods = sorted(keys, key=lambda m: (METHOD_ORDER.index(m) if m in METHOD_ORDER else len(METHOD_ORDER), m))
    return [(m, METHOD_LABELS.get(m, m.title())) for m in methods]


def _annotate_payments(payments):
    for p in payments:
        p.report_method_label = METHOD_LABELS.get(p.method, p.get_method_display())
    return payments


def _income_report_context(request):
    f, t = _dates(request)
    method = request.GET.get('method', '')
    payments = Payment.objects.all().order_by('-created_at')
    if f:
        payments = payments.filter(payment_date__gte=f)
    if t:
        payments = payments.filter(payment_date__lte=t)
    if method:
        payments = payments.filter(method=method)
    total_income = payments.aggregate(Sum('amount'))['amount__sum'] or 0
    invoiced_income = payments.filter(invoice__isnull=False).aggregate(Sum('amount'))['amount__sum'] or 0
    direct_income = total_income - invoiced_income
    method_keys = set(Payment.objects.values_list('method', flat=True))
    for cat in AccountCategory.objects.filter(is_active=True):
        method_keys.add(cat.name.lower())
    return {
        'payments': payments, 'total_income': total_income, 'invoiced_income': invoiced_income,
        'direct_income': direct_income, 'from': f, 'to': t,
        'methods': _method_choices_from(method_keys), 'selected_method': method,
    }


@financial_required
def income_report(request):
    context = _income_report_context(request)
    paginator = Paginator(context['payments'], 25)
    page = paginator.get_page(request.GET.get('page'))
    context['payments'] = _annotate_payments(page.object_list)
    return render(request, 'accounts/reports/income_report.html', context)


@financial_required
def income_report_pdf(request):
    context = _income_report_context(request)
    context['payments'] = _annotate_payments(context['payments'])
    html_string = render_to_string('accounts/reports/income_report_pdf.html', context, request=request)
    html_string = html_string.replace('</body>', '<script>window.onload=function(){setTimeout(function(){window.print();},300);}</script></body>')
    return HttpResponse(html_string)


@financial_required
def income_report_print(request):
    context = _income_report_context(request)
    context['payments'] = _annotate_payments(context['payments'])
    html_string = render_to_string('accounts/reports/income_report_pdf.html', context, request=request)
    html_string = html_string.replace('</body>', '<script>window.onload=function(){setTimeout(function(){window.print();},300);}</script></body>')
    return HttpResponse(html_string)


def _expense_method(expense):
    if expense.method:
        return expense.method.lower()
    acct = expense.bank_account
    if not acct or not acct.account_category:
        return 'cash'
    return acct.account_category.name.lower()


def _category_method(cat):
    return cat.name.lower()


def _expense_category_choices():
    choices = OrderedDict()
    for c in ExpenseCategory.objects.filter(is_active=True):
        key = CATEGORY_KEY_MAP.get(c.name.lower(), c.name.lower())
        choices[key] = c.name
    return list(choices.items())


def _expense_report_context(request):
    f, t = _dates(request)
    cat = request.GET.get('category', '')
    method = request.GET.get('method', '')
    sort = request.GET.get('sort', 'date')
    dir = request.GET.get('dir', 'desc')

    expenses = list(Expense.objects.all())
    if f:
        expenses = [e for e in expenses if str(e.expense_date) >= f]
    if t:
        expenses = [e for e in expenses if str(e.expense_date) <= t]
    if cat:
        expenses = [e for e in expenses if e.category == cat]

    method_keys = set()
    for e in expenses:
        method_keys.add(_expense_method(e))
    for cat in AccountCategory.objects.filter(is_active=True):
        method_keys.add(_category_method(cat))
    methods = _method_choices_from(method_keys)
    if method:
        expenses = [e for e in expenses if _expense_method(e) == method]

    for e in expenses:
        key = _expense_method(e)
        e.report_method = key
        e.report_method_label = METHOD_LABELS.get(key, key.title())

    cat_map = dict(_expense_category_choices())
    for e in expenses:
        e.report_category = cat_map.get(e.category, e.get_category_display())

    sort_keys = {'date': 'created_at', 'title': 'title', 'category': 'category', 'amount': 'amount', 'method': 'report_method'}
    skey = sort_keys.get(sort, 'expense_date')
    expenses.sort(key=lambda e: getattr(e, skey), reverse=(dir == 'desc'))

    total = sum(e.amount for e in expenses) or 0

    return {
        'expenses': expenses, 'total_expense': total,
        'categories': _expense_category_choices(), 'selected_category': cat,
        'methods': methods, 'selected_method': method,
        'from': f, 'to': t, 'sort': sort, 'dir': dir,
    }


@financial_required
def expense_report(request):
    context = _expense_report_context(request)
    paginator = Paginator(context['expenses'], 25)
    context['expenses'] = paginator.get_page(request.GET.get('page'))
    return render(request, 'accounts/reports/expense_report.html', context)


@financial_required
def expense_report_pdf(request):
    context = _expense_report_context(request)
    html_string = render_to_string('accounts/reports/expense_report_pdf.html', context, request=request)
    html_string = html_string.replace('</body>', '<script>window.onload=function(){setTimeout(function(){window.print();},300);}</script></body>')
    return HttpResponse(html_string)


@financial_required
def expense_report_print(request):
    context = _expense_report_context(request)
    html_string = render_to_string('accounts/reports/expense_report_pdf.html', context, request=request)
    html_string = html_string.replace('</body>', '<script>window.onload=function(){setTimeout(function(){window.print();},300);}</script></body>')
    return HttpResponse(html_string)


def _balance_report_context(request):
    f, t = _dates(request)
    method = request.GET.get('method', '')
    payments = Payment.objects.all()
    expenses = list(Expense.objects.all())
    if f:
        payments = payments.filter(payment_date__gte=f)
        expenses = [e for e in expenses if str(e.expense_date) >= f]
    if t:
        payments = payments.filter(payment_date__lte=t)
        expenses = [e for e in expenses if str(e.expense_date) <= t]

    method_keys = set(Payment.objects.values_list('method', flat=True))
    for cat in AccountCategory.objects.filter(is_active=True):
        method_keys.add(cat.name.lower())
    for e in expenses:
        method_keys.add(_expense_method(e))

    if method:
        payments = payments.filter(method=method)
        expenses = [e for e in expenses if _expense_method(e) == method]

    total_income = payments.aggregate(Sum('amount'))['amount__sum'] or 0
    total_expense = sum(e.amount for e in expenses) or 0
    net = total_income - total_expense
    bank_accounts = BankAccount.objects.filter(is_active=True).order_by('account_name')
    if method:
        bank_accounts = bank_accounts.filter(account_category__name__iexact=method)
    return {
        'total_income': total_income, 'total_expense': total_expense, 'net_balance': net,
        'bank_accounts': bank_accounts, 'from': f, 'to': t,
        'methods': _method_choices_from(method_keys), 'selected_method': method,
    }


@financial_required
def balance_report(request):
    context = _balance_report_context(request)
    paginator = Paginator(context['bank_accounts'], 25)
    context['bank_accounts'] = paginator.get_page(request.GET.get('page'))
    return render(request, 'accounts/reports/balance_report.html', context)


@financial_required
def balance_report_pdf(request):
    context = _balance_report_context(request)
    html_string = render_to_string('accounts/reports/balance_report_pdf.html', context, request=request)
    html_string = html_string.replace('</body>', '<script>window.onload=function(){setTimeout(function(){window.print();},300);}</script></body>')
    return HttpResponse(html_string)


@financial_required
def balance_report_print(request):
    context = _balance_report_context(request)
    html_string = render_to_string('accounts/reports/balance_report_pdf.html', context, request=request)
    html_string = html_string.replace('</body>', '<script>window.onload=function(){setTimeout(function(){window.print();},300);}</script></body>')
    return HttpResponse(html_string)


def _bank_details_context(request):
    q = request.GET.get('q', '')
    status = request.GET.get('status', '')
    category = request.GET.get('category', '')
    sort = request.GET.get('sort', 'balance')
    dir = request.GET.get('dir', 'desc')

    accounts = BankAccount.objects.select_related('account_category').all()
    if status:
        accounts = accounts.filter(is_active=(status == 'active'))
    if category:
        accounts = accounts.filter(account_category__name__iexact=category)
    accounts = list(accounts)
    if q:
        ql = q.lower()
        accounts = [a for a in accounts if any(
            ql in (f or '').lower() for f in (
                a.account_name, a.bank_name, a.holder_name, a.card_holder_name,
                a.account_number, a.mobile_number, a.branch, a.routing_number,
                a.display_name, a.account_category.name if a.account_category else '',
            )
        )]
    accounts.sort(key=lambda a: a.available_balance, reverse=(dir == 'desc'))

    categories = [(c.name.lower(), c.name) for c in AccountCategory.objects.filter(is_active=True).order_by('name')]
    return {
        'accounts': accounts, 'q': q, 'status': status, 'selected_category': category,
        'categories': categories, 'sort': sort, 'dir': dir,
    }


@financial_required
def bank_details(request):
    context = _bank_details_context(request)
    paginator = Paginator(context['accounts'], 25)
    context['accounts'] = paginator.get_page(request.GET.get('page'))
    return render(request, 'accounts/reports/bank_details.html', context)


@financial_required
def bank_details_pdf(request):
    context = _bank_details_context(request)
    html_string = render_to_string('accounts/reports/bank_details_pdf.html', context, request=request)
    html_string = html_string.replace('</body>', '<script>window.onload=function(){setTimeout(function(){window.print();},300);}</script></body>')
    return HttpResponse(html_string)


@financial_required
def bank_details_print(request):
    context = _bank_details_context(request)
    html_string = render_to_string('accounts/reports/bank_details_pdf.html', context, request=request)
    html_string = html_string.replace('</body>', '<script>window.onload=function(){setTimeout(function(){window.print();},300);}</script></body>')
    return HttpResponse(html_string)


@financial_required
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
