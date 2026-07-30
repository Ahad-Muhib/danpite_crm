from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string

from core.models import log_action
from clients.models import Client

from .forms import BankAccountForm, ExpenseForm, InvoiceForm, InvoiceItemFormSet, PaymentForm
from .models import BankAccount, Expense, ExpenseCategory, Invoice, Payment
from orders.models import Order, OrderItem
from datetime import date


def _update_invoice_paid_status(invoice):
    if invoice.is_fully_paid and invoice.status != 'paid':
        invoice.status = 'paid'
        invoice.received_payment = True
        invoice.save(update_fields=['status', 'received_payment'])
    elif not invoice.is_fully_paid and invoice.status == 'paid':
        invoice.status = 'sent'
        invoice.save(update_fields=['status'])


@login_required
def client_data_api(request):
    client_id = request.GET.get('id')
    if not client_id:
        return JsonResponse({'error': 'missing id'}, status=400)
    try:
        client = Client.objects.get(pk=client_id)
    except Client.DoesNotExist:
        return JsonResponse({'error': 'not found'}, status=404)
    return JsonResponse({
        'name': client.name,
        'phone': client.phone or '',
        'email': client.email or '',
        'company': client.company or '',
        'address': client.address or '',
    })


@login_required
def invoice_list(request):
    if request.method == 'POST' and 'bulk_action' in request.POST:
        selected_ids = request.POST.getlist('selected_invoices')
        if not selected_ids:
            messages.error(request, 'Select at least one invoice first.')
            return redirect('invoice_list')
        if not request.user.is_superuser:
            messages.error(request, 'Only superusers can delete invoices.')
            return redirect('invoice_list')
        for inv in Invoice.objects.filter(pk__in=selected_ids):
            log_action(request, 'delete', 'Invoice', inv, description=f'{inv.code} — Total: {inv.total}')
            inv.delete()
        messages.success(request, f'{len(selected_ids)} invoice(s) deleted.')
        return redirect('invoice_list')
    q = request.GET.get('q', '')
    status = request.GET.get('status', '')
    sort = request.GET.get('sort', 'id')
    dir = request.GET.get('dir', 'desc')
    sort_map = {'id': 'id', 'name': 'client__name', 'total': 'total', 'date': 'invoice_date', 'created': 'created_at'}
    order = sort_map.get(sort, 'id')
    if dir == 'desc':
        order = '-' + order
    qs = Invoice.objects.all().order_by(order)
    if q:
        qs = qs.filter(Q(code__icontains=q) | Q(bill_to_name__icontains=q) | Q(client__name__icontains=q))
    if status:
        qs = qs.filter(status=status)
    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'accounts/invoices.html', {'invoices': page, 'q': q, 'status': status, 'sort': sort, 'dir': dir})


@login_required
def bank_accounts_by_bank(request):
    category = request.GET.get('category', 'bank')
    bank_name = request.GET.get('bank_name', '')
    qs = BankAccount.objects.filter(is_active=True, category=category)
    if bank_name:
        qs = qs.filter(bank_name=bank_name)
    accounts = []
    for ba in qs:
        accounts.append({
            'id': ba.pk,
            'category': ba.category,
            'bank_name': ba.bank_name,
            'account_name': ba.account_name,
            'account_number': ba.account_number,
            'mobile_number': ba.mobile_number,
            'holder_name': ba.holder_name,
            'card_number': ba.card_number,
            'card_holder': ba.card_holder,
            'card_bank': ba.card_bank,
            'display_name': ba.display_name,
            'branch': ba.branch,
            'available_balance': str(ba.available_balance),
        })
    return JsonResponse({'accounts': accounts})


@login_required
def mobile_account_lookup(request):
    category = request.GET.get('type', '')
    number = request.GET.get('number', '')
    if category and number:
        acct = BankAccount.objects.filter(category=category, mobile_number=number, is_active=True).first()
        if acct:
            return JsonResponse({'found': True, 'category': acct.category, 'number': acct.mobile_number, 'holder_name': acct.holder_name})
    return JsonResponse({'found': False})


@login_required
def invoice_update_status(request, pk):
    if request.method == 'POST':
        inv = get_object_or_404(Invoice, pk=pk)
        new_status = request.POST.get('status', '')
        valid = [s[0] for s in Invoice.STATUS]
        if new_status in valid:
            inv.status = new_status
            inv.save(update_fields=['status'])
            log_action(request, 'update', 'Invoice', inv, description=f'Status changed to {new_status}')
            return JsonResponse({'ok': True, 'status': new_status})
        return JsonResponse({'ok': False, 'error': 'Invalid status.'}, status=400)
    return JsonResponse({'ok': False, 'error': 'POST required.'}, status=405)


@login_required
def invoice_create(request):
    form = InvoiceForm(request.POST or None, request.FILES or None)
    formset = InvoiceItemFormSet(request.POST or None)
    if request.method == 'POST':
        save_as_draft = 'save_as_draft' in request.POST
        if form.is_valid() and formset.is_valid():
            obj = form.save(commit=False)
            obj.created_by = request.user
            for f in ('tax', 'discount', 'shipping', 'total'):
                if not getattr(obj, f, None):
                    setattr(obj, f, 0)
            if not obj.status:
                obj.status = 'draft'
            if not obj.currency:
                obj.currency = 'BDT'
            bill_to = form.cleaned_data.get('bill_to_name', '').strip()
            if bill_to:
                client, _ = Client.objects.get_or_create(name=bill_to)
                obj.client = client
            if save_as_draft:
                obj.status = 'draft'
            obj.save()
            formset.instance = obj
            formset.save()
            item_total = obj.items.aggregate(s=Sum('total'))['s'] or 0
            after_discount = item_total - (item_total * (obj.discount or 0) / 100)
            obj.total = after_discount + (after_discount * (obj.tax or 0) / 100) + (obj.shipping or 0)
            obj.save(update_fields=['total'])
            amount_paid = form.cleaned_data.get('amount_paid') or 0
            if float(amount_paid) > 0:
                method = request.POST.get('payment_method', '') or 'cash'
                account_pk = request.POST.get('payment_bank_account', '')
                account = BankAccount.objects.filter(pk=account_pk).first() if account_pk else None
                mobile_number = request.POST.get('payment_mobile_number', '').strip()
                mobile_holder = request.POST.get('payment_mobile_holder', '').strip()
                if method in ('bkash', 'nagad', 'rocket') and mobile_number and not account:
                    account, _ = BankAccount.objects.get_or_create(
                        category=method, mobile_number=mobile_number,
                        defaults={'holder_name': mobile_holder, 'is_active': True},
                    )
                    if mobile_holder and account.holder_name != mobile_holder:
                        account.holder_name = mobile_holder
                        account.save()
                elif method in ('bkash', 'nagad', 'rocket') and mobile_number and account:
                    if account.mobile_number != mobile_number:
                        account.mobile_number = mobile_number
                    if mobile_holder and account.holder_name != mobile_holder:
                        account.holder_name = mobile_holder
                    account.save()
                ref = request.POST.get('payment_reference', '').strip() or f'Invoice {obj.code}'
                Payment.objects.create(
                    invoice=obj, client=obj.client, amount=amount_paid,
                    payment_date=date.today(),
                    method=method,
                    account=account,
                    reference=ref, created_by=request.user,
                )
            _update_invoice_paid_status(obj)
            log_action(request, 'create', 'Invoice', obj, description=f'{obj.code} — Total: {obj.total}')
            messages.success(request, 'Invoice created.')
            order = Order.objects.create(
                client=obj.client,
                status='processing' if obj.status == 'sent' else 'pending',
                total=obj.total,
                notes=f'Auto-created from {obj.code}',
                delivery_date=obj.delivery_date,
                assigned_to=request.user,
            )
            for item in obj.items.all():
                OrderItem.objects.create(
                    order=order,
                    product_name=item.description,
                    quantity=int(item.quantity),
                    unit_price=item.unit_price,
                )
            return redirect('invoice_list')
    clients = Client.objects.all().order_by('name')
    banks = list(
        BankAccount.objects.filter(is_active=True, category='bank')
        .values_list('bank_name', flat=True).distinct().order_by('bank_name')
    )
    return render(request, 'accounts/invoice_form.html', {
        'form': form, 'formset': formset, 'action': 'Create',
        'invoice': form.instance, 'clients': clients, 'banks': banks,
    })


@login_required
def invoice_edit(request, pk):
    obj = get_object_or_404(Invoice, pk=pk)
    form = InvoiceForm(request.POST or None, request.FILES or None, instance=obj)
    formset = InvoiceItemFormSet(request.POST or None, instance=obj)
    if request.method == 'POST':
        save_as_draft = 'save_as_draft' in request.POST
        if form.is_valid() and formset.is_valid():
            obj = form.save(commit=False)
            obj.updated_by = request.user
            for f in ('tax', 'discount', 'shipping', 'total'):
                if not getattr(obj, f, None):
                    setattr(obj, f, 0)
            bill_to = form.cleaned_data.get('bill_to_name', '').strip()
            if bill_to:
                client, _ = Client.objects.get_or_create(name=bill_to)
                obj.client = client
            else:
                obj.client = None
            if save_as_draft:
                obj.status = 'draft'
            obj.save()
            formset.instance = obj
            formset.save()
            item_total = obj.items.aggregate(s=Sum('total'))['s'] or 0
            after_discount = item_total - (item_total * (obj.discount or 0) / 100)
            obj.total = after_discount + (after_discount * (obj.tax or 0) / 100) + (obj.shipping or 0)
            obj.save(update_fields=['total'])
            new_amount = float(form.cleaned_data.get('amount_paid') or 0)
            current_paid = obj.payments.aggregate(s=Sum('amount'))['s'] or 0
            diff = new_amount - float(current_paid)
            if diff > 0:
                method = request.POST.get('payment_method', '') or 'cash'
                account_pk = request.POST.get('payment_bank_account', '')
                account = BankAccount.objects.filter(pk=account_pk).first() if account_pk else None
                mobile_number = request.POST.get('payment_mobile_number', '').strip()
                mobile_holder = request.POST.get('payment_mobile_holder', '').strip()
                if method in ('bkash', 'nagad', 'rocket') and mobile_number and not account:
                    account, _ = BankAccount.objects.get_or_create(
                        category=method, mobile_number=mobile_number,
                        defaults={'holder_name': mobile_holder, 'is_active': True},
                    )
                    if mobile_holder and account.holder_name != mobile_holder:
                        account.holder_name = mobile_holder
                        account.save()
                elif method in ('bkash', 'nagad', 'rocket') and mobile_number and account:
                    if account.mobile_number != mobile_number:
                        account.mobile_number = mobile_number
                    if mobile_holder and account.holder_name != mobile_holder:
                        account.holder_name = mobile_holder
                    account.save()
                ref = request.POST.get('payment_reference', '').strip() or f'Invoice {obj.code}'
                Payment.objects.create(
                    invoice=obj, client=obj.client, amount=diff,
                    payment_date=date.today(),
                    method=method,
                    account=account,
                    reference=ref, created_by=request.user,
                )
            elif diff < 0:
                for p in obj.payments.order_by('-created_at'):
                    if diff >= 0:
                        break
                    if p.amount <= abs(diff):
                        diff += float(p.amount)
                        p.delete()
                    else:
                        p.amount += diff
                        p.save()
                        diff = 0
            _update_invoice_paid_status(obj)
            Order.objects.filter(notes__contains=obj.code).update(delivery_date=obj.delivery_date)
            log_action(request, 'update', 'Invoice', obj, description=f'{obj.code} — Total: {obj.total}')
            messages.success(request, 'Invoice updated.')
            return redirect('invoice_list')
    clients = Client.objects.all().order_by('name')
    banks = list(
        BankAccount.objects.filter(is_active=True, category='bank')
        .values_list('bank_name', flat=True).distinct().order_by('bank_name')
    )
    return render(request, 'accounts/invoice_form.html', {
        'form': form, 'formset': formset, 'action': 'Edit',
        'invoice': obj, 'clients': clients, 'banks': banks,
    })


@login_required
def invoice_detail(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    items = invoice.items.all()
    payments = invoice.payments.all()
    total_paid = payments.aggregate(s=Sum('amount'))['s'] or 0
    subtotal = items.aggregate(s=Sum('total'))['s'] or 0
    discount_pct = float(invoice.discount or 0)
    tax_pct = float(invoice.tax or 0)
    shipping = float(invoice.shipping or 0)
    discount_amount = float(subtotal) * (discount_pct / 100)
    after_discount = float(subtotal) - discount_amount
    tax_amount = after_discount * (tax_pct / 100)
    total_with_tax = after_discount + tax_amount + shipping
    balance_due = total_with_tax - float(total_paid)
    return render(request, 'accounts/invoice_detail.html', {
        'invoice': invoice, 'items': items, 'payments': payments,
        'balance_due': balance_due, 'subtotal': subtotal,
        'discount_amount': discount_amount, 'tax_amount': tax_amount,
        'total_with_tax': total_with_tax, 'total_paid': total_paid,
        'shipping': shipping,
    })


@login_required
def invoice_delete(request, pk):
    if not request.user.is_superuser:
        messages.error(request, 'Only superusers can delete invoices.')
        return redirect('invoice_list')
    obj = get_object_or_404(Invoice, pk=pk)
    log_action(request, 'delete', 'Invoice', obj, description=f'{obj.code} — Total: {obj.total}')
    obj.delete()
    messages.success(request, 'Invoice deleted.')
    return redirect('invoice_list')


@login_required
def payment_list(request):
    if request.method == 'POST' and 'bulk_action' in request.POST:
        selected_ids = request.POST.getlist('selected_payments')
        if not selected_ids:
            messages.error(request, 'Select at least one payment first.')
            return redirect('payment_list')
        if not request.user.is_superuser:
            messages.error(request, 'Only superusers can delete payments.')
            return redirect('payment_list')
        for pay in Payment.objects.filter(pk__in=selected_ids):
            cname = pay.client.name if pay.client else '—'
            log_action(request, 'delete', 'Payment', pay, description=f'{pay.amount} — {cname} — {pay.payment_date}')
            pay.delete()
        messages.success(request, f'{len(selected_ids)} payment(s) deleted.')
        return redirect('payment_list')
    q = request.GET.get('q', '')
    method = request.GET.get('method', '')
    sort = request.GET.get('sort', 'id')
    dir = request.GET.get('dir', 'desc')
    sort_map = {'id': 'id', 'name': 'client__name', 'amount': 'amount', 'date': 'payment_date', 'created': 'created_at'}
    order = sort_map.get(sort, 'id')
    if dir == 'desc':
        order = '-' + order
    qs = Payment.objects.all().order_by(order)
    if q:
        qs = qs.filter(Q(client__name__icontains=q) | Q(invoice__code__icontains=q) | Q(amount__icontains=q) | Q(reference__icontains=q))
    if method:
        qs = qs.filter(method=method)
    total = qs.aggregate(Sum('amount'))['amount__sum'] or 0
    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'accounts/payments.html', {'payments': page, 'total': total, 'q': q, 'method': method, 'sort': sort, 'dir': dir})


@login_required
def payment_create(request):
    initial = {}
    invoice_id = request.GET.get('invoice')
    client_name = request.GET.get('client_name')
    if invoice_id and not request.method == 'POST':
        try:
            inv = Invoice.objects.get(pk=invoice_id)
            initial['invoice'] = inv
            initial['amount'] = inv.balance_due if inv.balance_due > 0 else inv.total
        except Invoice.DoesNotExist:
            pass
    if client_name and not request.method == 'POST':
        initial['client_name'] = client_name
    form = PaymentForm(request.POST or None, initial=initial or None)
    accounts = BankAccount.objects.filter(is_active=True).order_by('category', 'account_name')
    invoices = Invoice.objects.all().order_by('-created_at')[:100]
    clients = Client.objects.all().order_by('name')
    if form.is_valid():
        obj = form.save(commit=False)
        obj.created_by = request.user
        client_name = form.cleaned_data.get('client_name', '').strip()
        if client_name:
            client, _ = Client.objects.get_or_create(name=client_name)
            obj.client = client
        obj.save()
        if obj.invoice:
            _update_invoice_paid_status(obj.invoice)
        cname = obj.client.name if obj.client else '—'
        log_action(request, 'create', 'Payment', obj, description=f'{obj.amount} — {cname} — {obj.payment_date}')
        messages.success(request, 'Payment recorded.')
        return redirect('payment_list')
    return render(request, 'accounts/payment_form.html', {
        'form': form, 'action': 'Record', 'accounts': accounts, 'invoices': invoices, 'clients': clients,
    })


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
        obj.updated_by = request.user
        client_name = form.cleaned_data.get('client_name', '').strip()
        if client_name:
            client, _ = Client.objects.get_or_create(name=client_name)
            obj.client = client
        else:
            obj.client = None
        old_invoice = Payment.objects.get(pk=pk).invoice
        obj.save()
        if obj.invoice:
            _update_invoice_paid_status(obj.invoice)
        if old_invoice and old_invoice != obj.invoice:
            _update_invoice_paid_status(old_invoice)
        cname = obj.client.name if obj.client else '—'
        log_action(request, 'update', 'Payment', obj, description=f'{obj.amount} — {cname} — {obj.payment_date}')
        messages.success(request, 'Payment updated.')
        return redirect('payment_list')
    accounts = BankAccount.objects.filter(is_active=True).order_by('category', 'account_name')
    invoices = Invoice.objects.all().order_by('-created_at')[:100]
    clients = Client.objects.all().order_by('name')
    return render(request, 'accounts/payment_form.html', {
        'form': form, 'action': 'Edit', 'accounts': accounts, 'invoices': invoices, 'clients': clients,
    })


@login_required
def payment_delete(request, pk):
    if not request.user.is_superuser:
        messages.error(request, 'Only superusers can delete payments.')
        return redirect('payment_list')
    obj = get_object_or_404(Payment, pk=pk)
    invoice = obj.invoice
    cname = obj.client.name if obj.client else '—'
    log_action(request, 'delete', 'Payment', obj, description=f'{obj.amount} — {cname} — {obj.payment_date}')
    obj.delete()
    if invoice:
        _update_invoice_paid_status(invoice)
    messages.success(request, 'Payment deleted.')
    return redirect('payment_list')


@login_required
def expense_list(request):
    if request.method == 'POST' and 'bulk_action' in request.POST:
        selected_ids = request.POST.getlist('selected_expenses')
        if not selected_ids:
            messages.error(request, 'Select at least one expense first.')
            return redirect('expense_list')
        if not request.user.is_superuser:
            messages.error(request, 'Only superusers can delete expenses.')
            return redirect('expense_list')
        for obj in Expense.objects.filter(pk__in=selected_ids):
            log_action(request, 'delete', 'Expense', obj, description=f'{obj.title} — {obj.amount}')
            obj.delete()
        messages.success(request, f'{len(selected_ids)} expense(s) deleted.')
        return redirect('expense_list')
    q = request.GET.get('q', '')
    category = request.GET.get('category', '')
    sort = request.GET.get('sort', 'date')
    dir = request.GET.get('dir', 'desc')
    sort_map = {'id': 'id', 'title': 'title', 'category': 'category', 'amount': 'amount', 'date': 'expense_date', 'created': 'created_at'}
    order = sort_map.get(sort, 'expense_date')
    if dir == 'desc':
        order = '-' + order
    qs = Expense.objects.all().order_by(order)
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))
    if category:
        qs = qs.filter(category=category)
    total = qs.aggregate(Sum('amount'))['amount__sum'] or 0
    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'accounts/expenses.html', {'expenses': page, 'total': total, 'q': q, 'category': category, 'sort': sort, 'dir': dir})


@login_required
def expense_create(request):
    form = ExpenseForm(request.POST or None, request.FILES or None)
    accounts = BankAccount.objects.filter(is_active=True).order_by('category', 'account_name')
    if form.is_valid():
        obj = form.save(commit=False)
        obj.created_by = request.user
        obj.save()
        log_action(request, 'create', 'Expense', obj)
        messages.success(request, 'Expense recorded.')
        return redirect('expense_list')
    return render(request, 'accounts/expense_form.html', {'form': form, 'action': 'Add', 'accounts': accounts})


@login_required
def expense_detail(request, pk):
    obj = get_object_or_404(Expense, pk=pk)
    return render(request, 'accounts/expense_detail.html', {'expense': obj})


@login_required
def expense_edit(request, pk):
    obj = get_object_or_404(Expense, pk=pk)
    form = ExpenseForm(request.POST or None, request.FILES or None, instance=obj)
    accounts = BankAccount.objects.filter(is_active=True).order_by('category', 'account_name')
    if form.is_valid():
        obj = form.save()
        log_action(request, 'update', 'Expense', obj)
        messages.success(request, 'Expense updated.')
        return redirect('expense_list')
    return render(request, 'accounts/expense_form.html', {'form': form, 'action': 'Edit', 'accounts': accounts})


@login_required
def expense_delete(request, pk):
    if not request.user.is_superuser:
        messages.error(request, 'Only superusers can delete expenses.')
        return redirect('expense_list')
    obj = get_object_or_404(Expense, pk=pk)
    log_action(request, 'delete', 'Expense', obj)
    obj.delete()
    messages.success(request, 'Expense deleted.')
    return redirect('expense_list')


@login_required
def expense_category_list(request):
    if request.method == 'POST' and 'bulk_action' in request.POST:
        selected_ids = request.POST.getlist('selected_categories')
        if not selected_ids:
            messages.error(request, 'Select at least one category first.')
            return redirect('expense_category_list')
        if not request.user.is_superuser:
            messages.error(request, 'Only superusers can delete categories.')
            return redirect('expense_category_list')
        ExpenseCategory.objects.filter(pk__in=selected_ids).delete()
        messages.success(request, f'{len(selected_ids)} category(ies) deleted.')
        return redirect('expense_category_list')
    q = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '')
    sort = request.GET.get('sort', 'name')
    dir = request.GET.get('dir', 'asc')
    qs = ExpenseCategory.objects.all()
    if q:
        qs = qs.filter(name__icontains=q)
    if status_filter:
        qs = qs.filter(is_active=(status_filter == 'active'))
    if sort in ('name', 'created_at'):
        qs = qs.order_by(sort if dir == 'asc' else f'-{sort}')
    else:
        qs = qs.order_by('name')
    return render(request, 'accounts/expense_category_list.html', {
        'categories': qs, 'q': q, 'status_filter': status_filter, 'sort': sort, 'dir': dir,
    })


@login_required
def expense_category_create(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        is_active = request.POST.get('is_active') == '1'
        if not name:
            messages.error(request, 'Category name is required.')
            return redirect('expense_category_create')
        ExpenseCategory.objects.create(name=name, is_active=is_active)
        messages.success(request, f'Category "{name}" created.')
        return redirect('expense_category_list')
    return render(request, 'accounts/expense_category_form.html', {'action': 'Add', 'category': None})


@login_required
def expense_category_detail(request, pk):
    cat = get_object_or_404(ExpenseCategory, pk=pk)
    return render(request, 'accounts/expense_category_detail.html', {'category': cat})


@login_required
def expense_category_update_status(request, pk):
    if request.method == 'POST':
        cat = get_object_or_404(ExpenseCategory, pk=pk)
        is_active = request.POST.get('is_active')
        if is_active in ('1', 'true'):
            cat.is_active = True
        elif is_active in ('0', 'false'):
            cat.is_active = False
        else:
            return JsonResponse({'ok': False, 'error': 'Invalid value.'}, status=400)
        cat.save(update_fields=['is_active'])
        log_action(request, 'update', 'ExpenseCategory', cat, description=f'status={"active" if cat.is_active else "inactive"}')
        return JsonResponse({'ok': True, 'is_active': cat.is_active})
    return JsonResponse({'ok': False, 'error': 'POST required.'}, status=405)


@login_required
def expense_category_edit(request, pk):
    cat = get_object_or_404(ExpenseCategory, pk=pk)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        is_active = request.POST.get('is_active') == '1'
        if not name:
            messages.error(request, 'Category name is required.')
            return redirect('expense_category_edit', pk=pk)
        cat.name = name
        cat.is_active = is_active
        cat.save()
        messages.success(request, f'Category updated.')
        return redirect('expense_category_list')
    return render(request, 'accounts/expense_category_form.html', {'action': 'Edit', 'category': cat})


@login_required
def bank_account_list(request):
    if request.method == 'POST' and 'bulk_action' in request.POST:
        selected_ids = request.POST.getlist('selected_accounts')
        action = request.POST.get('bulk_action')
        selected = BankAccount.objects.filter(pk__in=selected_ids)

        if not selected_ids:
            messages.error(request, 'Select at least one bank account first.')
            return redirect('bank_account_list')

        if action == 'delete':
            if not request.user.is_superuser:
                messages.error(request, 'Only superusers can delete bank accounts.')
                return redirect('bank_account_list')
            deleted = selected.count()
            for obj in selected:
                log_action(request, 'delete', 'BankAccount', obj)
            selected.delete()
            messages.success(request, f'{deleted} bank account(s) deleted.')
        else:
            messages.error(request, 'Choose a bulk action first.')
        return redirect('bank_account_list')

    q = request.GET.get('q', '')
    status = request.GET.get('status', '')
    category = request.GET.get('category', '')
    sort_by = request.GET.get('sort', 'id')
    sort_order = request.GET.get('order', 'desc')

    valid_sorts = {
        'id': 'id', 'bank_name': 'bank_name', 'account_name': 'account_name',
        'account_number': 'account_number', 'account_type': 'account_type',
        'opening_balance': 'opening_balance',
    }
    sort_field = valid_sorts.get(sort_by, 'id')
    if sort_order == 'asc':
        order_field = sort_field
    else:
        order_field = f'-{sort_field}'

    qs = BankAccount.objects.all().order_by(order_field)
    if q:
        qs = qs.filter(
            Q(bank_name__icontains=q) | Q(account_name__icontains=q) |
            Q(account_number__icontains=q) | Q(mobile_number__icontains=q) |
            Q(holder_name__icontains=q) | Q(card_number__icontains=q) |
            Q(card_holder__icontains=q)
        )
    if category:
        qs = qs.filter(category=category)
    if status == 'active':
        qs = qs.filter(is_active=True)
    elif status == 'inactive':
        qs = qs.filter(is_active=False)
    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'accounts/bank_accounts.html', {
        'accounts': page, 'status': status, 'q': q, 'category': category,
        'sort_by': sort_by, 'sort_order': sort_order,
    })


@login_required
def bank_account_create(request):
    form = BankAccountForm(request.POST or None)
    if form.is_valid():
        obj = form.save()
        log_action(request, 'create', 'BankAccount', obj)
        messages.success(request, 'Bank account added.')
        return redirect('bank_account_list')
    return render(request, 'accounts/bank_account_form.html', {'form': form, 'action': 'Add'})


@login_required
def bank_account_detail(request, pk):
    from django.db.models import Sum
    obj = get_object_or_404(BankAccount, pk=pk)
    total_payments = obj.payments.aggregate(s=Sum('amount'))['s'] or 0
    total_expenses = obj.expenses.aggregate(s=Sum('amount'))['s'] or 0
    return render(request, 'accounts/bank_account_detail.html', {
        'account': obj,
        'total_payments': total_payments,
        'total_expenses': total_expenses,
    })


@login_required
def bank_account_edit(request, pk):
    obj = get_object_or_404(BankAccount, pk=pk)
    form = BankAccountForm(request.POST or None, instance=obj)
    if form.is_valid():
        obj = form.save()
        log_action(request, 'update', 'BankAccount', obj)
        messages.success(request, 'Bank account updated.')
        return redirect('bank_account_list')
    return render(request, 'accounts/bank_account_form.html', {'form': form, 'action': 'Edit'})


@login_required
def bank_account_toggle(request, pk):
    obj = get_object_or_404(BankAccount, pk=pk)
    obj.is_active = not obj.is_active
    obj.save()
    status = "activated" if obj.is_active else "deactivated"
    log_action(request, 'update', 'BankAccount', obj, description=f'{status}')
    messages.success(request, f'Bank account {status}.')
    return redirect('bank_account_list')


@login_required
def bank_account_update_status(request, pk):
    if request.method == 'POST':
        obj = get_object_or_404(BankAccount, pk=pk)
        is_active = request.POST.get('is_active')
        if is_active in ('1', 'true'):
            obj.is_active = True
        elif is_active in ('0', 'false'):
            obj.is_active = False
        else:
            return JsonResponse({'ok': False, 'error': 'Invalid value.'}, status=400)
        obj.save(update_fields=['is_active'])
        log_action(request, 'update', 'BankAccount', obj, description=f'status={"active" if obj.is_active else "inactive"}')
        return JsonResponse({'ok': True, 'is_active': obj.is_active})
    return JsonResponse({'ok': False, 'error': 'POST required.'}, status=405)


@login_required
def bank_account_delete(request, pk):
    if not request.user.is_superuser:
        messages.error(request, 'Only superusers can delete bank accounts.')
        return redirect('bank_account_list')
    obj = get_object_or_404(BankAccount, pk=pk)
    log_action(request, 'delete', 'BankAccount', obj)
    obj.delete()
    messages.success(request, 'Bank account deleted.')
    return redirect('bank_account_list')


@login_required
def invoice_pdf(request, pk):
    from weasyprint import HTML
    from django.db.models import Sum
    from django.conf import settings
    invoice = get_object_or_404(Invoice, pk=pk)
    items = invoice.items.all()
    subtotal = items.aggregate(s=Sum('total'))['s'] or 0
    discount_pct = float(invoice.discount or 0)
    tax_pct = float(invoice.tax or 0)
    shipping = float(invoice.shipping or 0)
    discount_amount = float(subtotal) * (discount_pct / 100)
    after_discount = float(subtotal) - discount_amount
    tax_amount = after_discount * (tax_pct / 100)
    total_with_tax = after_discount + tax_amount + shipping
    total_paid = invoice.payments.aggregate(s=Sum('amount'))['s'] or 0
    balance_due = total_with_tax - float(total_paid)
    logo_path = settings.MEDIA_ROOT / 'invoice_logos/danpite-ezgif.com-webp-to-jpg-converter.jpg'
    html_string = render_to_string('accounts/invoice_pdf.html', {
        'invoice': invoice, 'items': items,
        'subtotal': subtotal, 'discount_amount': discount_amount,
        'tax_amount': tax_amount, 'total_with_tax': total_with_tax,
        'total_paid': total_paid, 'balance_due': balance_due,
        'shipping': shipping, 'logo_path': logo_path,
    }, request=request)
    pdf = HTML(string=html_string, base_url=settings.BASE_DIR).write_pdf()
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{invoice.code}.pdf"'
    return response


@login_required
def invoice_mark_paid(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    if request.method == 'POST':
        invoice.status = 'paid'
        invoice.received_payment = True
        invoice.save()
        messages.success(request, f'{invoice.code} marked as paid.')
    return redirect('invoice_detail', pk=pk)
