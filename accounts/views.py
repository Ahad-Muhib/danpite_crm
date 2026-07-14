from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render

from .forms import BankAccountForm, ExpenseForm, InvoiceForm, PaymentForm
from .models import BankAccount, Expense, Invoice, Payment


@login_required
def invoice_list(request):
    q = request.GET.get('q', '')
    status = request.GET.get('status', '')
    qs = Invoice.objects.all()
    if q:
        qs = qs.filter(Q(code__icontains=q))
    if status:
        qs = qs.filter(status=status)
    return render(request, 'accounts/invoices.html', {'invoices': qs, 'q': q, 'status': status})


@login_required
def invoice_create(request):
    form = InvoiceForm(request.POST or None)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.created_by = request.user
        obj.save()
        messages.success(request, 'Invoice created.')
        return redirect('invoice_list')
    return render(request, 'accounts/invoice_form.html', {'form': form, 'action': 'Create'})


@login_required
def invoice_edit(request, pk):
    obj = get_object_or_404(Invoice, pk=pk)
    form = InvoiceForm(request.POST or None, instance=obj)
    if form.is_valid():
        form.save()
        messages.success(request, 'Invoice updated.')
        return redirect('invoice_list')
    return render(request, 'accounts/invoice_form.html', {'form': form, 'action': 'Edit'})


@login_required
def invoice_detail(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    items = invoice.items.all()
    payments = invoice.payments.all()
    return render(request, 'accounts/invoice_detail.html', {'invoice': invoice, 'items': items, 'payments': payments})


@login_required
def invoice_delete(request, pk):
    get_object_or_404(Invoice, pk=pk).delete()
    messages.success(request, 'Invoice deleted.')
    return redirect('invoice_list')


@login_required
def payment_list(request):
    qs = Payment.objects.all().order_by('-payment_date')
    total = qs.aggregate(Sum('amount'))['amount__sum'] or 0
    return render(request, 'accounts/payments.html', {'payments': qs, 'total': total})


@login_required
def payment_create(request):
    form = PaymentForm(request.POST or None)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.created_by = request.user
        obj.save()
        messages.success(request, 'Payment recorded.')
        return redirect('payment_list')
    return render(request, 'accounts/payment_form.html', {'form': form})


@login_required
def payment_delete(request, pk):
    get_object_or_404(Payment, pk=pk).delete()
    messages.success(request, 'Payment deleted.')
    return redirect('payment_list')


@login_required
def expense_list(request):
    qs = Expense.objects.all().order_by('-expense_date')
    total = qs.aggregate(Sum('amount'))['amount__sum'] or 0
    return render(request, 'accounts/expenses.html', {'expenses': qs, 'total': total})


@login_required
def expense_create(request):
    form = ExpenseForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.created_by = request.user
        obj.save()
        messages.success(request, 'Expense recorded.')
        return redirect('expense_list')
    return render(request, 'accounts/expense_form.html', {'form': form})


@login_required
def expense_delete(request, pk):
    get_object_or_404(Expense, pk=pk).delete()
    messages.success(request, 'Expense deleted.')
    return redirect('expense_list')


@login_required
def bank_account_list(request):
    qs = BankAccount.objects.all()
    return render(request, 'accounts/bank_accounts.html', {'accounts': qs})


@login_required
def bank_account_create(request):
    form = BankAccountForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Bank account added.')
        return redirect('bank_account_list')
    return render(request, 'accounts/bank_account_form.html', {'form': form})


@login_required
def bank_account_delete(request, pk):
    get_object_or_404(BankAccount, pk=pk).delete()
    messages.success(request, 'Bank account deleted.')
    return redirect('bank_account_list')
