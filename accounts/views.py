from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render

from clients.models import Client

from .forms import BankAccountForm, ExpenseForm, InvoiceForm, InvoiceItemFormSet, PaymentForm
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
    formset = InvoiceItemFormSet(request.POST or None)
    if request.method == 'POST':
        save_as_draft = 'save_as_draft' in request.POST
        if form.is_valid() and formset.is_valid():
            obj = form.save(commit=False)
            obj.created_by = request.user
            client_name = form.cleaned_data.get('client_name', '').strip()
            if client_name:
                client, _ = Client.objects.get_or_create(name=client_name)
                obj.client = client
            if save_as_draft:
                obj.status = 'draft'
            obj.save()
            formset.instance = obj
            formset.save()
            messages.success(request, 'Invoice created.')
            return redirect('invoice_list')
    return render(request, 'accounts/invoice_form.html', {'form': form, 'formset': formset, 'action': 'Create'})


@login_required
def invoice_edit(request, pk):
    obj = get_object_or_404(Invoice, pk=pk)
    form = InvoiceForm(request.POST or None, instance=obj)
    formset = InvoiceItemFormSet(request.POST or None, instance=obj)
    if request.method == 'POST':
        save_as_draft = 'save_as_draft' in request.POST
        if form.is_valid() and formset.is_valid():
            obj = form.save(commit=False)
            client_name = form.cleaned_data.get('client_name', '').strip()
            if client_name:
                client, _ = Client.objects.get_or_create(name=client_name)
                obj.client = client
            else:
                obj.client = None
            if save_as_draft:
                obj.status = 'draft'
            obj.save()
            formset.instance = obj
            formset.save()
            messages.success(request, 'Invoice updated.')
            return redirect('invoice_list')
    return render(request, 'accounts/invoice_form.html', {'form': form, 'formset': formset, 'action': 'Edit', 'invoice': obj})


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
        client_name = form.cleaned_data.get('client_name', '').strip()
        if client_name:
            client, _ = Client.objects.get_or_create(name=client_name)
            obj.client = client
        obj.save()
        messages.success(request, 'Payment recorded.')
        return redirect('payment_list')
    return render(request, 'accounts/payment_form.html', {'form': form, 'action': 'Record'})


@login_required
def payment_detail(request, pk):
    obj = get_object_or_404(Payment, pk=pk)
    return render(request, 'accounts/payment_detail.html', {'payment': obj})


@login_required
def payment_edit(request, pk):
    obj = get_object_or_404(Payment, pk=pk)
    form = PaymentForm(request.POST or None, instance=obj)
    if form.is_valid():
        obj = form.save(commit=False)
        client_name = form.cleaned_data.get('client_name', '').strip()
        if client_name:
            client, _ = Client.objects.get_or_create(name=client_name)
            obj.client = client
        else:
            obj.client = None
        obj.save()
        messages.success(request, 'Payment updated.')
        return redirect('payment_list')
    return render(request, 'accounts/payment_form.html', {'form': form, 'action': 'Edit'})


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
    return render(request, 'accounts/expense_form.html', {'form': form, 'action': 'Add'})


@login_required
def expense_detail(request, pk):
    obj = get_object_or_404(Expense, pk=pk)
    return render(request, 'accounts/expense_detail.html', {'expense': obj})


@login_required
def expense_edit(request, pk):
    obj = get_object_or_404(Expense, pk=pk)
    form = ExpenseForm(request.POST or None, request.FILES or None, instance=obj)
    if form.is_valid():
        form.save()
        messages.success(request, 'Expense updated.')
        return redirect('expense_list')
    return render(request, 'accounts/expense_form.html', {'form': form, 'action': 'Edit'})


@login_required
def expense_delete(request, pk):
    get_object_or_404(Expense, pk=pk).delete()
    messages.success(request, 'Expense deleted.')
    return redirect('expense_list')


@login_required
def bank_account_list(request):
    status = request.GET.get('status', '')
    qs = BankAccount.objects.all()
    if status == 'active':
        qs = qs.filter(is_active=True)
    elif status == 'inactive':
        qs = qs.filter(is_active=False)
    return render(request, 'accounts/bank_accounts.html', {'accounts': qs, 'status': status})


@login_required
def bank_account_create(request):
    form = BankAccountForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Bank account added.')
        return redirect('bank_account_list')
    return render(request, 'accounts/bank_account_form.html', {'form': form, 'action': 'Add'})


@login_required
def bank_account_detail(request, pk):
    obj = get_object_or_404(BankAccount, pk=pk)
    return render(request, 'accounts/bank_account_detail.html', {'account': obj})


@login_required
def bank_account_edit(request, pk):
    obj = get_object_or_404(BankAccount, pk=pk)
    form = BankAccountForm(request.POST or None, instance=obj)
    if form.is_valid():
        form.save()
        messages.success(request, 'Bank account updated.')
        return redirect('bank_account_list')
    return render(request, 'accounts/bank_account_form.html', {'form': form, 'action': 'Edit'})


@login_required
def bank_account_toggle(request, pk):
    obj = get_object_or_404(BankAccount, pk=pk)
    obj.is_active = not obj.is_active
    obj.save()
    status = "activated" if obj.is_active else "deactivated"
    messages.success(request, f'Bank account {status}.')
    return redirect('bank_account_list')


@login_required
def bank_account_delete(request, pk):
    get_object_or_404(BankAccount, pk=pk).delete()
    messages.success(request, 'Bank account deleted.')
    return redirect('bank_account_list')
