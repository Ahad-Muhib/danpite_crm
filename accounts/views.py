import json
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Sum, F, Value
from django.db.models.functions import Coalesce
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string

from core.models import log_action
from clients.models import Client
from leads.models import LeadContact

from .forms import BankAccountForm, ExpenseForm, InvoiceForm, InvoiceItemFormSet, PaymentForm, TransferForm, QuotationForm
from .models import (AccountCategory, AccountType, BankAccount, Expense, ExpenseCategory, Invoice, Payment, Transfer, Quotation,
                     METHOD_CHOICES, CATEGORY_KEY_MAP,
                     DEFAULT_CRM_FEATURES, DEFAULT_HRM_FEATURES, DEFAULT_MOBILE_FEATURES, DEFAULT_SYSTEM_FEATURES,
                     DEFAULT_TECH_STACK, DEFAULT_SECURITY_FEATURES, DEFAULT_TRAINING_SUPPORT, DEFAULT_DELIVERABLES,
                     DEFAULT_PRICING_PLANS, get_default_feature_sections, get_default_terms_sections)
from orders.models import Order, OrderItem
from datetime import date

MOBILE_METHODS = {'bkash', 'nagad', 'rocket', 'upay'}


def _available_payment_methods():
    """Only offer payment methods whose linked account category actually has active accounts."""
    from django.db.models import Exists, OuterRef
    sub = BankAccount.objects.filter(is_active=True, account_category=OuterRef('pk'))
    cats = list(AccountCategory.objects.filter(is_active=True).annotate(has_accts=Exists(sub)))
    has = {c.name.lower(): c.has_accts for c in cats}
    choices = []
    for value, label in METHOD_CHOICES:
        if value in MOBILE_METHODS:
            if has.get(value):
                choices.append((value, label))
        elif value == 'cash':
            if has.get('cash'):
                choices.append((value, label))
        elif value == 'card':
            if has.get('card'):
                choices.append((value, label))
        elif has.get('bank'):
            choices.append((value, label))
    return choices


def _client_suggestions():
    return [
        {'pk': c.pk, 'name': c.name, 'phone': c.phone or '', 'address': c.address or ''}
        for c in Client.objects.filter(status='active').order_by('name')
    ]


def _parse_payment_rows(request, invoice_code):
    """Parse dynamic payment rows from the invoice form into a list of dicts.

    Every row with an amount must reference an account that exists in the
    bank accounts section — nothing is auto-created here. Returns (rows, errors).
    """
    rows = []
    errors = []
    try:
        count = int(request.POST.get('payments-TOTAL_FORMS', 0))
    except (TypeError, ValueError):
        count = 0
    for i in range(count):
        p = f'payments-{i}-'
        method = request.POST.get(p + 'method', '').strip().lower()
        amount_str = request.POST.get(p + 'amount', '').strip()
        if not method and not amount_str:
            continue
        try:
            amount = Decimal(amount_str or 0)
        except Exception:
            amount = Decimal('0')
        if amount is not None and amount <= 0:
            continue

        account = None
        account_pk = request.POST.get(p + 'account_pk', '').strip()
        if account_pk:
            account = BankAccount.objects.filter(pk=account_pk).first()

        if not account and method in MOBILE_METHODS:
            mobile_number = request.POST.get(p + 'mobile_number', '').strip()
            if mobile_number:
                account = BankAccount.objects.filter(
                    account_category__name__iexact=method,
                    mobile_number=mobile_number,
                ).first()

        if not account:
            if not method:
                errors.append(f'Payment row {i + 1}: select a payment method and its account from the bank accounts page.')
            else:
                errors.append(f'Payment row {i + 1}: please select the "{method}" account from the bank accounts page.')
            rows.append({
                'id': request.POST.get(p + 'id', '').strip(),
                'method': method,
                'amount': amount,
                'account': None,
                'reference': request.POST.get(p + 'reference', '').strip(),
                'error': True,
            })
            continue

        pid = request.POST.get(p + 'id', '').strip()
        reference = request.POST.get(p + 'reference', '').strip()
        if not reference:
            reference = f'Invoice {invoice_code}' if invoice_code else ''
        rows.append({
            'id': pid,
            'method': method,
            'amount': amount,
            'account': account,
            'reference': reference,
        })
    return rows, errors


def _serialize_payments(invoice):
    data = []
    for pay in invoice.payments.all():
        account = None
        if pay.account:
            cat = pay.account.account_category
            account = {
                'pk': pay.account.pk,
                'display_name': pay.account.display_name,
                'category_name': cat.name if cat else '',
                'category_type': cat.account_type if cat else '',
                'bank_name': pay.account.bank_name,
                'account_number': pay.account.account_number,
                'mobile_number': pay.account.mobile_number,
                'mobile_holder': pay.account.holder_name,
                'holder_name': pay.account.holder_name,
            }
        data.append({
            'id': pay.pk,
            'method': pay.method,
            'amount': str(pay.amount),
            'reference': pay.reference,
            'account': account,
        })
    return data


def _update_invoice_paid_status(invoice):
    if invoice.is_fully_paid and invoice.status != 'paid':
        invoice.status = 'paid'
        invoice.received_payment = True
        invoice.save(update_fields=['status', 'received_payment'])
    elif not invoice.is_fully_paid and invoice.status == 'paid':
        invoice.status = 'sent'
        invoice.save(update_fields=['status'])


def _serialize_parsed_rows(rows):
    """Convert parsed payment rows back into the JS-serialized payment shape (for re-render)."""
    data = []
    for row in rows:
        account = None
        if row.get('account'):
            acc = row['account']
            cat = acc.account_category
            account = {
                'pk': acc.pk,
                'display_name': acc.display_name,
                'category_name': cat.name if cat else '',
                'category_type': cat.account_type if cat else '',
                'bank_name': acc.bank_name,
                'account_number': acc.account_number,
                'mobile_number': acc.mobile_number,
                'mobile_holder': acc.holder_name,
                'holder_name': acc.holder_name,
            }
        data.append({
            'id': row.get('id') or '',
            'method': row.get('method', ''),
            'amount': str(row.get('amount', 0)),
            'reference': row.get('reference', ''),
            'account': account,
        })
    return data


def _invoice_form_context(request, form, formset, obj, action, existing_payments_json):
    clients = _client_suggestions()
    bank_cats = AccountCategory.objects.filter(is_active=True, account_type='bank').values_list('pk', flat=True)
    banks = list(
        BankAccount.objects.filter(is_active=True, account_category__in=bank_cats)
        .values_list('bank_name', flat=True).distinct().order_by('bank_name')
    )
    categories = AccountCategory.objects.filter(is_active=True)
    return {
        'form': form, 'formset': formset, 'action': action,
        'invoice': obj, 'clients': clients, 'banks': banks,
        'categories': categories, 'method_choices': _available_payment_methods(),
        'existing_payments_json': existing_payments_json,
    }


def _formset_item_total(formset):
    total = 0
    for f in formset:
        if not f.cleaned_data or f.cleaned_data.get('DELETE'):
            continue
        total += (f.cleaned_data.get('quantity') or 0) * (f.cleaned_data.get('unit_price') or 0)
    return total


def _invoice_overpaid(total, paid):
    return paid > total


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
    qs = Invoice.objects.annotate(
        paid=Coalesce(Sum('payments__amount'), Value(Decimal('0'))),
    ).annotate(due=F('total') - F('paid')).order_by(order)
    if q:
        qs = qs.filter(Q(code__icontains=q) | Q(bill_to_name__icontains=q) | Q(client__name__icontains=q))
    if status:
        qs = qs.filter(status=status)
    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'accounts/invoices.html', {'invoices': page, 'q': q, 'status': status, 'sort': sort, 'dir': dir})


@login_required
def bank_accounts_by_bank(request):
    category_pk = request.GET.get('category', '')
    bank_name = request.GET.get('bank_name', '')
    account_type = request.GET.get('account_type', '')
    qs = BankAccount.objects.filter(is_active=True)
    if category_pk:
        qs = qs.filter(account_category_id=category_pk)
    if bank_name:
        qs = qs.filter(bank_name=bank_name)
    if account_type:
        qs = qs.filter(account_category__account_type=account_type)
    accounts = []
    for ba in qs:
        cat_name = ba.account_category.name if ba.account_category else ''
        cat_type = ba.account_category.account_type if ba.account_category else ''
        accounts.append({
            'id': ba.pk,
            'account_category_id': ba.account_category_id,
            'category': cat_name,
            'category_type': cat_type,
            'mobile_provider': ba.mobile_provider,
            'bank_name': ba.bank_name,
            'account_name': ba.account_name,
            'account_number': ba.account_number,
            'mobile_number': ba.mobile_number,
            'holder_name': ba.holder_name,
            'contact_number': ba.contact_number,
            'currency': ba.currency,
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
        acct = BankAccount.objects.filter(account_category_id=category, mobile_number=number, is_active=True).first()
        if acct:
            return JsonResponse({'found': True, 'category': acct.account_category_id, 'number': acct.mobile_number, 'holder_name': acct.holder_name})
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
            client_pk = request.POST.get('client_pk', '').strip()
            if bill_to and client_pk:
                try:
                    obj.client = Client.objects.get(pk=client_pk)
                except (Client.DoesNotExist, ValueError):
                    messages.error(request, 'Please select a valid client from the dropdown.')
                    context = _invoice_form_context(request, form, formset, obj, 'Create', json.dumps([]))
                    return render(request, 'accounts/invoice_form.html', context)
                if obj.client.status != 'active':
                    messages.error(request, 'This client is inactive and cannot be invoiced.')
                    context = _invoice_form_context(request, form, formset, obj, 'Create', json.dumps([]))
                    return render(request, 'accounts/invoice_form.html', context)
            elif bill_to and not client_pk:
                messages.error(request, 'Please select a client from the dropdown instead of typing a name.')
                context = _invoice_form_context(request, form, formset, obj, 'Create', json.dumps([]))
                return render(request, 'accounts/invoice_form.html', context)
            elif not bill_to:
                messages.error(request, 'Please select a client before creating an invoice.')
                context = _invoice_form_context(request, form, formset, obj, 'Create', json.dumps([]))
                return render(request, 'accounts/invoice_form.html', context)
            item_total = _formset_item_total(formset)
            if item_total <= 0:
                messages.error(request, 'Please add at least one line item with a valid amount.')
                context = _invoice_form_context(request, form, formset, obj, 'Create', json.dumps([]))
                return render(request, 'accounts/invoice_form.html', context)
            if save_as_draft:
                obj.status = 'draft'
            rows, pay_errors = _parse_payment_rows(request, '')
            if pay_errors:
                messages.error(request, ' '.join(pay_errors))
                context = _invoice_form_context(request, form, formset, obj, 'Create', json.dumps(_serialize_parsed_rows(rows)))
                return render(request, 'accounts/invoice_form.html', context)
            item_total = _formset_item_total(formset)
            after_discount = item_total - (item_total * (obj.discount or 0) / 100)
            obj.total = after_discount + (after_discount * (obj.tax or 0) / 100) + (obj.shipping or 0)
            paid = sum(r['amount'] for r in rows)
            if _invoice_overpaid(obj.total, paid):
                messages.error(request, f'Paid amount ({paid}) is greater than the invoice total ({obj.total}). Please reduce the paid amount so it does not exceed the total.')
                context = _invoice_form_context(request, form, formset, obj, 'Create', json.dumps(_serialize_parsed_rows(rows)))
                return render(request, 'accounts/invoice_form.html', context)
            obj.save()
            formset.instance = obj
            formset.save()
            item_total = obj.items.aggregate(s=Sum('total'))['s'] or 0
            after_discount = item_total - (item_total * (obj.discount or 0) / 100)
            obj.total = after_discount + (after_discount * (obj.tax or 0) / 100) + (obj.shipping or 0)
            obj.save(update_fields=['total'])
            for row in _parse_payment_rows(request, obj.code)[0]:
                Payment.objects.create(
                    invoice=obj, client=obj.client, amount=row['amount'],
                    payment_date=date.today(), method=row['method'],
                    account=row['account'], reference=row['reference'],
                    created_by=request.user,
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
    return render(request, 'accounts/invoice_form.html',
                  _invoice_form_context(request, form, formset, form.instance, 'Create', json.dumps([])))


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
            client_pk = request.POST.get('client_pk', '').strip()
            if bill_to and client_pk:
                try:
                    obj.client = Client.objects.get(pk=client_pk)
                except (Client.DoesNotExist, ValueError):
                    messages.error(request, 'Please select a valid client from the dropdown.')
                    context = _invoice_form_context(request, form, formset, obj, 'Edit', json.dumps(_serialize_payments(obj)))
                    return render(request, 'accounts/invoice_form.html', context)
                if obj.client.status != 'active':
                    messages.error(request, 'This client is inactive and cannot be invoiced.')
                    context = _invoice_form_context(request, form, formset, obj, 'Edit', json.dumps(_serialize_payments(obj)))
                    return render(request, 'accounts/invoice_form.html', context)
            elif bill_to and not client_pk:
                messages.error(request, 'Please select a client from the dropdown instead of typing a name.')
                context = _invoice_form_context(request, form, formset, obj, 'Edit', json.dumps(_serialize_payments(obj)))
                return render(request, 'accounts/invoice_form.html', context)
            elif not bill_to:
                messages.error(request, 'Please select a client before saving an invoice.')
                context = _invoice_form_context(request, form, formset, obj, 'Edit', json.dumps(_serialize_payments(obj)))
                return render(request, 'accounts/invoice_form.html', context)
            item_total = _formset_item_total(formset)
            if item_total <= 0:
                messages.error(request, 'Please add at least one line item with a valid amount.')
                context = _invoice_form_context(request, form, formset, obj, 'Edit', json.dumps(_serialize_payments(obj)))
                return render(request, 'accounts/invoice_form.html', context)
            if save_as_draft:
                obj.status = 'draft'
            rows, pay_errors = _parse_payment_rows(request, obj.code)
            if pay_errors:
                messages.error(request, ' '.join(pay_errors))
                context = _invoice_form_context(request, form, formset, obj, 'Edit', json.dumps(_serialize_parsed_rows(rows)))
                return render(request, 'accounts/invoice_form.html', context)
            item_total = _formset_item_total(formset)
            after_discount = item_total - (item_total * (obj.discount or 0) / 100)
            obj.total = after_discount + (after_discount * (obj.tax or 0) / 100) + (obj.shipping or 0)
            paid = sum(r['amount'] for r in rows)
            if _invoice_overpaid(obj.total, paid):
                messages.error(request, f'Paid amount ({paid}) is greater than the invoice total ({obj.total}). Please reduce the paid amount so it does not exceed the total.')
                context = _invoice_form_context(request, form, formset, obj, 'Edit', json.dumps(_serialize_parsed_rows(rows)))
                return render(request, 'accounts/invoice_form.html', context)
            obj.save()
            formset.instance = obj
            formset.save()
            item_total = obj.items.aggregate(s=Sum('total'))['s'] or 0
            after_discount = item_total - (item_total * (obj.discount or 0) / 100)
            obj.total = after_discount + (after_discount * (obj.tax or 0) / 100) + (obj.shipping or 0)
            obj.save(update_fields=['total'])
            existing = {p.pk: p for p in obj.payments.all()}
            submitted = []
            for row in rows:
                try:
                    pid = int(row['id']) if row['id'] else None
                except ValueError:
                    pid = None
                if pid and pid in existing:
                    p = existing[pid]
                    p.method = row['method']
                    p.amount = row['amount']
                    p.account = row['account']
                    p.reference = row['reference']
                    p.save()
                    submitted.append(pid)
                else:
                    p = Payment.objects.create(
                        invoice=obj, client=obj.client, amount=row['amount'],
                        payment_date=date.today(), method=row['method'],
                        account=row['account'], reference=row['reference'],
                        created_by=request.user,
                    )
                    submitted.append(p.pk)
            for pk, p in existing.items():
                if pk not in submitted:
                    p.delete()
            _update_invoice_paid_status(obj)
            Order.objects.filter(notes__contains=obj.code).update(delivery_date=obj.delivery_date)
            log_action(request, 'update', 'Invoice', obj, description=f'{obj.code} — Total: {obj.total}')
            messages.success(request, 'Invoice updated.')
            return redirect('invoice_list')
    return render(request, 'accounts/invoice_form.html',
                  _invoice_form_context(request, form, formset, obj, 'Edit', json.dumps(_serialize_payments(obj))))


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


def _payment_overflows(invoice, new_amount, subtract=0):
    current_paid = invoice.total - invoice.balance_due
    return current_paid - subtract + new_amount > invoice.total


@login_required
def payment_create(request):
    initial = {'payment_date': date.today()}
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
    form = PaymentForm(request.POST or None, request.FILES or None, initial=initial or None,
                       method_choices=_available_payment_methods())
    accounts = BankAccount.objects.filter(is_active=True).order_by('account_category__account_type', 'account_name')
    invoices = Invoice.objects.all().order_by('-created_at')[:100]
    clients = Client.objects.all().order_by('name')
    if form.is_valid():
        obj = form.save(commit=False)
        obj.created_by = request.user
        client_name = form.cleaned_data.get('client_name', '').strip()
        if client_name:
            client, _ = Client.objects.get_or_create(name=client_name)
            obj.client = client
        if obj.invoice and _payment_overflows(obj.invoice, obj.amount):
            messages.error(request, f'This payment ({obj.amount}) would exceed the invoice total ({obj.invoice.total}). Please fix the amount.')
            return render(request, 'accounts/payment_form.html', {
                'form': form, 'action': 'Record', 'accounts': accounts, 'invoices': invoices, 'clients': clients,
            })
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
    accounts = BankAccount.objects.filter(is_active=True).order_by('account_category__account_type', 'account_name')
    invoices = Invoice.objects.all().order_by('-created_at')[:100]
    clients = Client.objects.all().order_by('name')
    form = PaymentForm(request.POST or None, request.FILES or None, instance=obj,
                       method_choices=_available_payment_methods())
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
        if obj.invoice:
            subtract = old_invoice.total if old_invoice and old_invoice.pk == obj.invoice.pk else 0
            if _payment_overflows(obj.invoice, obj.amount, subtract=subtract):
                messages.error(request, f'This payment ({obj.amount}) would exceed the invoice total ({obj.invoice.total}). Please fix the amount.')
                return render(request, 'accounts/payment_form.html', {
                    'form': form, 'action': 'Edit', 'accounts': accounts, 'invoices': invoices, 'clients': clients,
                })
        obj.save()
        if obj.invoice:
            _update_invoice_paid_status(obj.invoice)
        if old_invoice and old_invoice != obj.invoice:
            _update_invoice_paid_status(old_invoice)
        cname = obj.client.name if obj.client else '—'
        log_action(request, 'update', 'Payment', obj, description=f'{obj.amount} — {cname} — {obj.payment_date}')
        messages.success(request, 'Payment updated.')
        return redirect('payment_list')
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
    sort = request.GET.get('sort', 'created')
    dir = request.GET.get('dir', 'desc')
    sort_map = {'id': 'id', 'title': 'title', 'category': 'category', 'method': 'method', 'amount': 'amount', 'date': 'expense_date', 'created': 'created_at'}
    order = sort_map.get(sort, 'created_at')
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
    categories = [(CATEGORY_KEY_MAP.get(c.name.lower(), c.name.lower()), c.name)
                  for c in ExpenseCategory.objects.filter(is_active=True).order_by('name')]
    return render(request, 'accounts/expenses.html',
                  {'expenses': page, 'total': total, 'q': q, 'category': category, 'sort': sort, 'dir': dir, 'categories': categories})


@login_required
@login_required
def expense_create(request):
    form = ExpenseForm(request.POST or None, request.FILES or None, method_choices=_available_payment_methods())
    accounts = BankAccount.objects.filter(is_active=True).order_by('account_category__account_type', 'account_name')
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
    form = ExpenseForm(request.POST or None, request.FILES or None, instance=obj, method_choices=_available_payment_methods())
    accounts = BankAccount.objects.filter(is_active=True).order_by('account_category__account_type', 'account_name')
    if form.is_valid():
        obj = form.save()
        log_action(request, 'update', 'Expense', obj)
        messages.success(request, 'Expense updated.')
        return redirect('expense_list')
    return render(request, 'accounts/expense_form.html', {'form': form, 'action': 'Edit', 'accounts': accounts})


@login_required
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
    sort = request.GET.get('sort', 'created')
    dir = request.GET.get('dir', 'desc')
    qs = ExpenseCategory.objects.all()
    if q:
        qs = qs.filter(name__icontains=q)
    if status_filter:
        qs = qs.filter(is_active=(status_filter == 'active'))
    if sort in ('name', 'created_at'):
        qs = qs.order_by(sort if dir == 'asc' else f'-{sort}')
    else:
        qs = qs.order_by('-created_at')
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
def categories_json(request):
    cats = AccountCategory.objects.all().order_by('account_type', 'name')
    type_map = {t.key: t.label for t in AccountType.objects.all()}
    data = [{'pk': c.pk, 'name': c.name, 'account_type': c.account_type, 'type_display': type_map.get(c.account_type, c.account_type), 'is_active': c.is_active} for c in cats]
    return JsonResponse(data, safe=False)


@login_required
def category_toggle_status(request, pk):
    if request.method == 'POST':
        cat = get_object_or_404(AccountCategory, pk=pk)
        is_active = request.POST.get('is_active')
        if is_active in ('1', 'true'):
            cat.is_active = True
        elif is_active in ('0', 'false'):
            cat.is_active = False
        else:
            return JsonResponse({'ok': False, 'error': 'Invalid value.'}, status=400)
        cat.save(update_fields=['is_active'])
        return JsonResponse({'ok': True, 'is_active': cat.is_active})
    return JsonResponse({'ok': False, 'error': 'POST required.'}, status=405)


@login_required
def type_add(request):
    if request.method == 'POST':
        key = request.POST.get('key', '').strip().lower().replace(' ', '_')
        label = request.POST.get('label', '').strip()
        if not key or not label:
            return JsonResponse({'ok': False, 'error': 'Enter both key and label.'})
        if AccountType.objects.filter(key=key).exists():
            return JsonResponse({'ok': False, 'error': 'Type already exists.'})
        AccountType.objects.create(key=key, label=label)
        data = list(AccountType.objects.all().values('key', 'label'))
        return JsonResponse({'ok': True, 'types': data})
    return JsonResponse({'ok': False, 'error': 'POST required.'}, status=405)


@login_required
def category_add(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        account_type = request.POST.get('account_type', '')
        if not name or not account_type:
            return JsonResponse({'ok': False, 'error': 'Invalid name or type.'})
        if AccountCategory.objects.filter(name__iexact=name).exists():
            return JsonResponse({'ok': False, 'error': 'Category already exists.'})
        AccountCategory.objects.create(name=name, account_type=account_type)
        return JsonResponse({'ok': True})
    return JsonResponse({'ok': False, 'error': 'POST required.'}, status=405)


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
            Q(holder_name__icontains=q) | Q(contact_number__icontains=q)
        )
    if category:
        qs = qs.filter(account_category_id=category)
    if status == 'active':
        qs = qs.filter(is_active=True)
    elif status == 'inactive':
        qs = qs.filter(is_active=False)
    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))
    all_categories = AccountCategory.objects.filter(is_active=True)
    return render(request, 'accounts/bank_accounts.html', {
        'accounts': page, 'status': status, 'q': q, 'category': category,
        'sort_by': sort_by, 'sort_order': sort_order,
        'all_categories': all_categories,
    })


@login_required
def bank_account_create(request):
    form = BankAccountForm(request.POST or None)
    categories = AccountCategory.objects.filter(is_active=True)
    type_choices = list(AccountType.objects.all().values_list('key', 'label'))
    cats_json = json.dumps([{'pk': c.pk, 'name': c.name, 'account_type': c.account_type} for c in categories])
    bank_accounts = BankAccount.objects.filter(is_active=True, account_category__name='Bank')
    types_json = json.dumps([{'key': t.key, 'label': t.label} for t in AccountType.objects.all()])
    if form.is_valid():
        obj = form.save()
        log_action(request, 'create', 'BankAccount', obj)
        messages.success(request, 'Bank account added.')
        return redirect('bank_account_list')
    return render(request, 'accounts/bank_account_form.html', {
        'form': form, 'action': 'Add', 'categories': categories,
        'type_choices': type_choices, 'categories_json': cats_json,
        'types_json': types_json,
        'selected_type': None, 'bank_accounts': bank_accounts,
    })


@login_required
def bank_account_detail(request, pk):
    from django.db.models import Sum
    obj = get_object_or_404(BankAccount, pk=pk)
    if request.method == 'POST' and request.user.is_superuser and 'adjust_balance' in request.POST:
        try:
            desired = Decimal(request.POST.get('new_available_balance', '0'))
            total_payments = obj.payments.aggregate(s=Sum('amount'))['s'] or 0
            total_expenses = obj.expenses.aggregate(s=Sum('amount'))['s'] or 0
            transfers_out = obj.transfers_out.aggregate(s=Sum('amount'))['s'] or 0
            transfers_in = obj.transfers_in.aggregate(s=Sum('amount'))['s'] or 0
            obj.opening_balance = desired - total_payments + total_expenses + transfers_out - transfers_in
            obj.save(update_fields=['opening_balance'])
            messages.success(request, f'Available balance adjusted to {desired}.')
        except Exception:
            messages.error(request, 'Invalid balance value.')
        return redirect('bank_account_detail', pk=pk)
    total_payments = obj.payments.aggregate(s=Sum('amount'))['s'] or 0
    total_expenses = obj.expenses.aggregate(s=Sum('amount'))['s'] or 0
    transactions = []
    for p in obj.payments.all():
        transactions.append({'date': p.created_at, 'kind': 'payment', 'label': p.reference or 'Payment', 'detail': p.invoice.code if p.invoice else '', 'amount': p.amount})
    for e in obj.expenses.all():
        transactions.append({'date': e.created_at, 'kind': 'expense', 'label': e.title, 'detail': '', 'amount': e.amount})
    transactions.sort(key=lambda t: t['date'], reverse=True)
    categories = AccountCategory.objects.filter(is_active=True)
    return render(request, 'accounts/bank_account_detail.html', {
        'account': obj,
        'total_payments': total_payments,
        'total_expenses': total_expenses,
        'categories': categories,
        'transactions': transactions,
    })


@login_required
def bank_account_edit(request, pk):
    obj = get_object_or_404(BankAccount, pk=pk)
    if request.method == 'POST' and request.user.is_superuser and 'adjust_balance' in request.POST:
        try:
            desired = Decimal(request.POST.get('new_available_balance', '0'))
            total_payments = obj.payments.aggregate(s=Sum('amount'))['s'] or 0
            total_expenses = obj.expenses.aggregate(s=Sum('amount'))['s'] or 0
            transfers_out = obj.transfers_out.aggregate(s=Sum('amount'))['s'] or 0
            transfers_in = obj.transfers_in.aggregate(s=Sum('amount'))['s'] or 0
            obj.opening_balance = desired - total_payments + total_expenses + transfers_out - transfers_in
            obj.save(update_fields=['opening_balance'])
            messages.success(request, f'Available balance adjusted to {desired}.')
        except Exception:
            messages.error(request, 'Invalid balance value.')
        return redirect('bank_account_edit', pk=pk)
    form = BankAccountForm(request.POST or None, instance=obj)
    categories = AccountCategory.objects.filter(is_active=True)
    selected_type = obj.account_category.account_type if obj.account_category else None
    type_choices = list(AccountType.objects.all().values_list('key', 'label'))
    cats_json = json.dumps([{'pk': c.pk, 'name': c.name, 'account_type': c.account_type} for c in categories])
    bank_accounts = BankAccount.objects.filter(is_active=True, account_category__name='Bank')
    types_json = json.dumps([{'key': t.key, 'label': t.label} for t in AccountType.objects.all()])
    if form.is_valid():
        obj = form.save()
        log_action(request, 'update', 'BankAccount', obj)
        messages.success(request, 'Bank account updated.')
        return redirect('bank_account_list')
    return render(request, 'accounts/bank_account_form.html', {
        'form': form, 'action': 'Edit', 'categories': categories,
        'type_choices': type_choices, 'categories_json': cats_json,
        'types_json': types_json,
        'selected_type': selected_type, 'bank_accounts': bank_accounts,
    })


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
    invoice = get_object_or_404(Invoice, pk=pk)
    context = _invoice_pdf_context(invoice)
    html_string = render_to_string('accounts/invoice_pdf.html', context, request=request)
    html_string = html_string.replace('</body>', '<script>window.onload=function(){setTimeout(function(){window.print();},300);}</script></body>')
    return HttpResponse(html_string)


def _invoice_pdf_context(invoice):
    from django.db.models import Sum
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
    payments = invoice.payments.all()
    return {
        'invoice': invoice, 'items': items,
        'subtotal': subtotal, 'discount_amount': discount_amount,
        'tax_amount': tax_amount, 'total_with_tax': total_with_tax,
        'total_paid': total_paid, 'balance_due': balance_due,
        'shipping': shipping, 'payments': payments,
    }


@login_required
def invoice_print(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    context = _invoice_pdf_context(invoice)
    html_string = render_to_string('accounts/invoice_pdf.html', context, request=request)
    html_string = html_string.replace('</body>', '<script>window.onload=function(){setTimeout(function(){window.print();},300);}</script></body>')
    return HttpResponse(html_string)


@login_required
def transfer_list(request):
    if request.method == 'POST' and 'bulk_action' in request.POST:
        selected_ids = request.POST.getlist('selected_transfers')
        if not selected_ids:
            messages.error(request, 'Select at least one transfer first.')
            return redirect('transfer_list')
        if not request.user.is_superuser:
            messages.error(request, 'Only superusers can delete transfers.')
            return redirect('transfer_list')
        for obj in Transfer.objects.filter(pk__in=selected_ids):
            log_action(request, 'delete', 'Transfer', obj, description=f'{obj.from_account} → {obj.to_account}: {obj.amount}')
            obj.delete()
        messages.success(request, f'{len(selected_ids)} transfer(s) deleted.')
        return redirect('transfer_list')
    bank_id = request.GET.get('bank', '')
    sort = request.GET.get('sort', 'created')
    dir = request.GET.get('dir', 'desc')
    sort_map = {'id': 'id', 'amount': 'amount', 'date': 'transfer_date', 'created': 'created_at'}
    order = sort_map.get(sort, 'created_at')
    if dir == 'desc':
        order = '-' + order
    qs = Transfer.objects.all().order_by(order)
    if bank_id:
        qs = qs.filter(Q(from_account_id=bank_id) | Q(to_account_id=bank_id))
        sent_total = Transfer.objects.filter(from_account_id=bank_id).aggregate(s=Sum('amount'))['s'] or 0
        recv_total = Transfer.objects.filter(to_account_id=bank_id).aggregate(s=Sum('amount'))['s'] or 0
    else:
        agg = Transfer.objects.aggregate(s=Sum('amount'))
        sent_total = recv_total = agg['s'] or 0
    total = qs.aggregate(Sum('amount'))['amount__sum'] or 0
    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))
    bank_accounts = BankAccount.objects.filter(is_active=True).order_by('account_category__account_type', 'account_name')
    return render(request, 'accounts/transfer_list.html', {
        'transfers': page, 'total': total, 'bank_id': bank_id,
        'sent_total': sent_total, 'recv_total': recv_total,
        'sort': sort, 'dir': dir, 'bank_accounts': bank_accounts,
    })


@login_required
def transfer_create(request):
    form = TransferForm(request.POST or None, request.FILES or None)
    bank_cats = AccountCategory.objects.filter(is_active=True, account_type='bank').values_list('pk', flat=True)
    banks = list(
        BankAccount.objects.filter(is_active=True, account_category__in=bank_cats)
        .values_list('bank_name', flat=True).distinct().order_by('bank_name')
    )
    accounts = BankAccount.objects.filter(is_active=True).order_by('account_category__account_type', 'account_name')
    if form.is_valid():
        obj = form.save(commit=False)
        obj.created_by = request.user
        obj.save()
        log_action(request, 'create', 'Transfer', obj, description=f'{obj.from_account} → {obj.to_account}: {obj.amount}')
        messages.success(request, 'Transfer completed.')
        return redirect('transfer_list')
    return render(request, 'accounts/transfer_form.html', {'form': form, 'action': 'Add', 'banks': banks, 'accounts': accounts})


@login_required
def transfer_detail(request, pk):
    obj = get_object_or_404(Transfer, pk=pk)
    return render(request, 'accounts/transfer_detail.html', {'transfer': obj})


@login_required
def transfer_delete(request, pk):
    if not request.user.is_superuser:
        messages.error(request, 'Only superusers can delete transfers.')
        return redirect('transfer_list')
    obj = get_object_or_404(Transfer, pk=pk)
    log_action(request, 'delete', 'Transfer', obj, description=f'{obj.from_account} → {obj.to_account}: {obj.amount}')
    obj.delete()
    messages.success(request, 'Transfer deleted.')
    return redirect('transfer_list')


# ── Quotation Views ────────────────────────────────────────────────────────────

@login_required
def lead_data_api(request):
    lead_id = request.GET.get('id')
    if not lead_id:
        return JsonResponse({'error': 'missing id'}, status=400)
    try:
        lead = LeadContact.objects.get(pk=lead_id)
    except LeadContact.DoesNotExist:
        return JsonResponse({'error': 'not found'}, status=404)
    return JsonResponse({
        'name': lead.name,
        'phone': lead.phone or '',
        'email': lead.email or '',
        'company': lead.company or '',
        'address': lead.address or '',
    })


@login_required
def quotation_list(request):
    if request.method == 'POST' and 'bulk_action' in request.POST:
        selected_ids = request.POST.getlist('selected_quotations')
        if not selected_ids:
            messages.error(request, 'Select at least one quotation first.')
            return redirect('quotation_list')
        action = request.POST.get('bulk_action')
        qs = Quotation.objects.filter(pk__in=selected_ids)
        if action == 'delete':
            count = qs.count()
            for obj in qs:
                log_action(request, 'delete', 'Quotation', obj, description=f'Bulk deleted quotation {obj.code}')
            qs.delete()
            messages.success(request, f'Deleted {count} quotation(s).')
        elif action in ('draft', 'sent', 'accepted', 'rejected', 'expired'):
            count = qs.update(status=action)
            messages.success(request, f'Updated status of {count} quotation(s) to {action.title()}.')
        return redirect('quotation_list')

    qs = Quotation.objects.select_related('client', 'lead', 'created_by').all()
    q = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()

    if q:
        qs = qs.filter(
            Q(code__icontains=q) |
            Q(company_name__icontains=q) |
            Q(contact_person__icontains=q) |
            Q(client__name__icontains=q) |
            Q(client__company__icontains=q) |
            Q(lead__name__icontains=q) |
            Q(subject__icontains=q)
        )
    if status_filter:
        qs = qs.filter(status=status_filter)
    if date_from:
        qs = qs.filter(quotation_date__gte=date_from)
    if date_to:
        qs = qs.filter(quotation_date__lte=date_to)

    total_count = Quotation.objects.count()
    draft_count = Quotation.objects.filter(status='draft').count()
    sent_count = Quotation.objects.filter(status='sent').count()
    accepted_count = Quotation.objects.filter(status='accepted').count()

    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'accounts/quotations.html', {
        'page_obj': page_obj,
        'quotations': page_obj,
        'q': q,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'total_count': total_count,
        'draft_count': draft_count,
        'sent_count': sent_count,
        'accepted_count': accepted_count,
    })


def _extract_quotation_lists(request):
    """Extract and sanitize multi-select feature lists, pricing plans and dynamic sections from POST."""
    crm_features = request.POST.getlist('crm_features') if 'crm_features' in request.POST else []
    hrm_features = request.POST.getlist('hrm_features') if 'hrm_features' in request.POST else []
    mobile_app_features = request.POST.getlist('mobile_app_features') if 'mobile_app_features' in request.POST else []
    system_features = request.POST.getlist('system_features') if 'system_features' in request.POST else []
    tech_stack = request.POST.getlist('tech_stack') if 'tech_stack' in request.POST else []
    security_features = request.POST.getlist('security_features') if 'security_features' in request.POST else []
    training_support = request.POST.getlist('training_support') if 'training_support' in request.POST else []
    deliverables = request.POST.getlist('deliverables') if 'deliverables' in request.POST else []

    # Dynamic pricing plans
    pricing_plans = []
    total_plans = 0
    try:
        total_plans = int(request.POST.get('pricing_plans_count', 0))
    except (ValueError, TypeError):
        total_plans = 0

    if total_plans > 0:
        for i in range(total_plans):
            pkg = request.POST.get(f'plan_pkg_{i}', '').strip()
            lic = request.POST.get(f'plan_lic_{i}', '').strip()
            prc = request.POST.get(f'plan_prc_{i}', '').strip()
            dt = request.POST.get(f'plan_dt_{i}', '').strip()
            is_sel = (request.POST.get(f'plan_sel_{i}') in ('on', 'true', '1')) or (request.POST.get('plan_selected_radio') == str(i))
            if pkg or prc:
                pricing_plans.append({
                    'package': pkg,
                    'license': lic,
                    'price': prc,
                    'delivery_time': dt,
                    'is_selected': is_sel,
                })

    # Extract Dynamic Feature Sections
    sections_count = int(request.POST.get('sections_count', 0))
    feature_sections = []
    for i in range(sections_count):
        title = request.POST.get(f'section_title_{i}', '').strip()
        content = request.POST.get(f'section_content_{i}', '').strip()
        if title or (content and content not in ('<p><br></p>', '<p></p>', '')):
            feature_sections.append({
                'title': title,
                'content': content
            })

    # Extract Dynamic Terms Sections (Draggable)
    terms_count = int(request.POST.get('terms_count', 0))
    terms_sections = []
    for i in range(terms_count):
        title = request.POST.get(f'term_title_{i}', '').strip()
        content = request.POST.get(f'term_content_{i}', '').strip()
        if title or (content and content not in ('<p><br></p>', '<p></p>', '')):
            terms_sections.append({
                'title': title or 'Terms Section',
                'content': content
            })

    return {
        'feature_sections': feature_sections,
        'terms_sections': terms_sections,
        'crm_features': crm_features,
        'hrm_features': hrm_features,
        'mobile_app_features': mobile_app_features,
        'system_features': system_features,
        'tech_stack': tech_stack,
        'security_features': security_features,
        'training_support': training_support,
        'deliverables': deliverables,
        'pricing_plans': pricing_plans,
    }


@login_required
def quotation_create(request):
    from core.models import CurrencySettings
    clients = Client.objects.filter(status='active').order_by('name')

    if request.method == 'POST':
        form = QuotationForm(request.POST)
        if form.is_valid():
            quotation = form.save(commit=False)
            quotation.created_by = request.user
            quotation.updated_by = request.user
            quotation.currency = getattr(CurrencySettings.load(), 'currency_code', 'BDT')

            extracted = _extract_quotation_lists(request)
            for k, v in extracted.items():
                setattr(quotation, k, v)

            quotation.save()
            log_action(request, 'create', 'Quotation', quotation, description=f'Created quotation {quotation.code} for {quotation.company_name}')
            messages.success(request, f'Quotation {quotation.code} created successfully.')
            return redirect('quotation_detail', pk=quotation.pk)
    else:
        form = QuotationForm()

    return render(request, 'accounts/quotation_form.html', {
        'form': form,
        'action': 'Create',
        'clients': clients,
        'default_feature_sections': get_default_feature_sections(),
        'default_terms_sections': get_default_terms_sections(),
        'default_pricing_plans': DEFAULT_PRICING_PLANS,
    })


@login_required
def quotation_edit(request, pk):
    from core.models import CurrencySettings
    quotation = get_object_or_404(Quotation, pk=pk)
    clients = Client.objects.filter(status='active').order_by('name')

    if request.method == 'POST':
        form = QuotationForm(request.POST, instance=quotation)
        if form.is_valid():
            quotation = form.save(commit=False)
            quotation.updated_by = request.user
            if not quotation.currency:
                quotation.currency = getattr(CurrencySettings.load(), 'currency_code', 'BDT')

            extracted = _extract_quotation_lists(request)
            for k, v in extracted.items():
                setattr(quotation, k, v)

            quotation.save()
            log_action(request, 'update', 'Quotation', quotation, description=f'Updated quotation {quotation.code}')
            messages.success(request, f'Quotation {quotation.code} updated.')
            return redirect('quotation_detail', pk=quotation.pk)
    else:
        form = QuotationForm(instance=quotation)

    # Use existing feature sections or fallback to defaults
    feature_sections = quotation.feature_sections if quotation.feature_sections else get_default_feature_sections()

    # Use existing terms sections or fallback to legacy terms / defaults
    terms_sections = quotation.terms_sections
    if not terms_sections:
        legacy_terms = []
        if quotation.payment_terms:
            legacy_terms.append({'title': 'Payment Terms', 'content': quotation.payment_terms})
        if quotation.delivery_terms:
            legacy_terms.append({'title': 'Delivery & Support Policy', 'content': quotation.delivery_terms})
        if quotation.terms_conditions:
            legacy_terms.append({'title': 'Terms & Conditions', 'content': quotation.terms_conditions})
        if quotation.warranty:
            legacy_terms.append({'title': 'Warranty Details', 'content': quotation.warranty})
        if quotation.not_included:
            legacy_terms.append({'title': 'Not Included / Exclusions', 'content': quotation.not_included})
        if quotation.why_danpite:
            legacy_terms.append({'title': 'Why Danpite Tech?', 'content': quotation.why_danpite})
        if quotation.custom_terms:
            for ct in quotation.custom_terms:
                legacy_terms.append({'title': ct.get('title', 'Additional Terms'), 'content': ct.get('content', '')})
        terms_sections = legacy_terms if legacy_terms else get_default_terms_sections()

    return render(request, 'accounts/quotation_form.html', {
        'form': form,
        'action': 'Edit',
        'quotation': quotation,
        'clients': clients,
        'default_feature_sections': feature_sections,
        'default_terms_sections': terms_sections,
        'default_pricing_plans': quotation.pricing_plans or DEFAULT_PRICING_PLANS,
    })


@login_required
def quotation_detail(request, pk):
    quotation = get_object_or_404(Quotation.objects.select_related('client', 'lead', 'created_by'), pk=pk)
    return render(request, 'accounts/quotation_detail.html', {
        'quotation': quotation,
    })


@login_required
def quotation_duplicate(request, pk):
    original = get_object_or_404(Quotation, pk=pk)
    quotation = Quotation.objects.get(pk=pk)
    quotation.pk = None
    quotation.code = ''
    quotation.status = 'draft'
    quotation.quotation_date = date.today()
    quotation.created_by = request.user
    quotation.updated_by = request.user
    quotation.save()
    log_action(request, 'create', 'Quotation', quotation, description=f'Cloned from {original.code} to {quotation.code}')
    messages.success(request, f'Quotation duplicated as draft {quotation.code}.')
    return redirect('quotation_edit', pk=quotation.pk)


@login_required
def quotation_delete(request, pk):
    quotation = get_object_or_404(Quotation, pk=pk)
    code = quotation.code
    log_action(request, 'delete', 'Quotation', quotation, description=f'Deleted quotation {code}')
    quotation.delete()
    messages.success(request, f'Quotation {code} deleted.')
    return redirect('quotation_list')


@login_required
def quotation_pdf(request, pk):
    quotation = get_object_or_404(Quotation.objects.select_related('client', 'lead'), pk=pk)
    html_string = render_to_string('accounts/quotation_pdf.html', {'quotation': quotation}, request=request)
    html_string = html_string.replace('</body>', '<script>window.onload=function(){setTimeout(function(){window.print();},400);}</script></body>')
    return HttpResponse(html_string)


@login_required
def quotation_print(request, pk):
    return quotation_pdf(request, pk)


@login_required
def quotation_update_status(request, pk):
    if request.method == 'POST':
        quotation = get_object_or_404(Quotation, pk=pk)
        new_status = request.POST.get('status', '').strip()
        if new_status in dict(Quotation.STATUS_CHOICES):
            quotation.status = new_status
            quotation.updated_by = request.user
            quotation.save(update_fields=['status', 'updated_by', 'updated_at'])
            log_action(request, 'update', 'Quotation', quotation, description=f'Changed status to {new_status}')
            messages.success(request, f'Status updated to "{quotation.get_status_display()}".')
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'quotation_list'
    return redirect(next_url)

