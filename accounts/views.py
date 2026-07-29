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
from .models import BankAccount, Expense, Invoice, Payment
from orders.models import Order, OrderItem
from datetime import date


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
                Payment.objects.create(
                    invoice=obj, client=obj.client, amount=amount_paid,
                    payment_date=date.today(), method='cash',
                    reference=f'Invoice {obj.code}', created_by=request.user,
                )
            log_action(request, 'create', 'Invoice', obj, description=f'{obj.code} — Total: {obj.total}')
            messages.success(request, 'Invoice created.')
            order = Order.objects.create(
                client=obj.client,
                status='processing' if obj.status == 'sent' else 'pending',
                total=obj.total,
                notes=f'Auto-created from {obj.code}',
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
    return render(request, 'accounts/invoice_form.html', {'form': form, 'formset': formset, 'action': 'Create', 'invoice': form.instance, 'clients': clients})


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
                Payment.objects.create(
                    invoice=obj, client=obj.client, amount=diff,
                    payment_date=date.today(), method='cash',
                    reference=f'Invoice {obj.code}', created_by=request.user,
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
            log_action(request, 'update', 'Invoice', obj, description=f'{obj.code} — Total: {obj.total}')
            messages.success(request, 'Invoice updated.')
            return redirect('invoice_list')
    clients = Client.objects.all().order_by('name')
    return render(request, 'accounts/invoice_form.html', {'form': form, 'formset': formset, 'action': 'Edit', 'invoice': obj, 'clients': clients})


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
    form = PaymentForm(request.POST or None)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.created_by = request.user
        client_name = form.cleaned_data.get('client_name', '').strip()
        if client_name:
            client, _ = Client.objects.get_or_create(name=client_name)
            obj.client = client
        obj.save()
        cname = obj.client.name if obj.client else '—'
        log_action(request, 'create', 'Payment', obj, description=f'{obj.amount} — {cname} — {obj.payment_date}')
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
        obj.updated_by = request.user
        client_name = form.cleaned_data.get('client_name', '').strip()
        if client_name:
            client, _ = Client.objects.get_or_create(name=client_name)
            obj.client = client
        else:
            obj.client = None
        obj.save()
        cname = obj.client.name if obj.client else '—'
        log_action(request, 'update', 'Payment', obj, description=f'{obj.amount} — {cname} — {obj.payment_date}')
        messages.success(request, 'Payment updated.')
        return redirect('payment_list')
    return render(request, 'accounts/payment_form.html', {'form': form, 'action': 'Edit'})


@login_required
def payment_delete(request, pk):
    if not request.user.is_superuser:
        messages.error(request, 'Only superusers can delete payments.')
        return redirect('payment_list')
    obj = get_object_or_404(Payment, pk=pk)
    cname = obj.client.name if obj.client else '—'
    log_action(request, 'delete', 'Payment', obj, description=f'{obj.amount} — {cname} — {obj.payment_date}')
    obj.delete()
    messages.success(request, 'Payment deleted.')
    return redirect('payment_list')


@login_required
def expense_list(request):
    qs = Expense.objects.all().order_by('-expense_date')
    total = qs.aggregate(Sum('amount'))['amount__sum'] or 0
    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'accounts/expenses.html', {'expenses': page, 'total': total})


@login_required
def expense_create(request):
    form = ExpenseForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.created_by = request.user
        obj.save()
        log_action(request, 'create', 'Expense', obj)
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
        obj = form.save()
        log_action(request, 'update', 'Expense', obj)
        messages.success(request, 'Expense updated.')
        return redirect('expense_list')
    return render(request, 'accounts/expense_form.html', {'form': form, 'action': 'Edit'})


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
def bank_account_list(request):
    status = request.GET.get('status', '')
    qs = BankAccount.objects.all().order_by('-id')
    if status == 'active':
        qs = qs.filter(is_active=True)
    elif status == 'inactive':
        qs = qs.filter(is_active=False)
    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'accounts/bank_accounts.html', {'accounts': page, 'status': status})


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
    obj = get_object_or_404(BankAccount, pk=pk)
    return render(request, 'accounts/bank_account_detail.html', {'account': obj})


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
    html_string = render_to_string('accounts/invoice_pdf.html', {
        'invoice': invoice, 'items': items,
        'subtotal': subtotal, 'discount_amount': discount_amount,
        'tax_amount': tax_amount, 'total_with_tax': total_with_tax,
        'total_paid': total_paid, 'balance_due': balance_due,
        'shipping': shipping,
    })
    pdf = HTML(string=html_string).write_pdf()
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
