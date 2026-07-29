from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.models import log_action
from .forms import ClientForm
from .models import Client, ClientCategory


@login_required
def client_list(request):
    if request.method == 'POST' and 'bulk_action' in request.POST:
        selected_ids = request.POST.getlist('selected_clients')
        if not selected_ids:
            messages.error(request, 'Select at least one client first.')
            return redirect('client_list')
        if not request.user.is_superuser:
            messages.error(request, 'Only superusers can delete clients.')
            return redirect('client_list')
        for client in Client.objects.filter(pk__in=selected_ids):
            log_action(request, 'delete', 'Client', client)
            client.delete()
        messages.success(request, f'{len(selected_ids)} client(s) deleted.')
        return redirect('client_list')

    q = request.GET.get('q', '')
    status = request.GET.get('status', '')
    sort_by = request.GET.get('sort', 'name')
    sort_order = request.GET.get('order', 'asc')
    valid_sorts = {'id': 'id', 'name': 'name'}
    sort_field = valid_sorts.get(sort_by, 'name')
    order_field = sort_field if sort_order == 'asc' else f'-{sort_field}'
    qs = Client.objects.all().order_by(order_field)
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(email__icontains=q) | Q(company__icontains=q))
    if status:
        qs = qs.filter(status=status)
    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'clients/clients.html', {'clients': page, 'q': q, 'status': status, 'sort_by': sort_by, 'sort_order': sort_order})


@login_required
def client_create(request):
    form = ClientForm(request.POST or None)
    if form.is_valid():
        obj = form.save()
        log_action(request, 'create', 'Client', obj)
        messages.success(request, 'Client added.')
        return redirect('client_list')
    return render(request, 'clients/client_form.html', {'form': form, 'action': 'Add'})


@login_required
def client_edit(request, pk):
    obj = get_object_or_404(Client, pk=pk)
    form = ClientForm(request.POST or None, instance=obj)
    if form.is_valid():
        form.save()
        log_action(request, 'update', 'Client', obj)
        messages.success(request, 'Client updated.')
        return redirect('client_list')
    return render(request, 'clients/client_form.html', {'form': form, 'action': 'Edit', 'client': obj})


@login_required
def client_detail(request, pk):
    client = get_object_or_404(Client, pk=pk)
    invoices = client.invoices.all()[:5]
    orders = client.orders.all()[:5]
    deals = client.lead_contact.deals.all() if client.lead_contact else []
    return render(request, 'clients/client_detail.html', {'client': client, 'invoices': invoices, 'orders': orders, 'deals': deals})


@login_required
def client_delete(request, pk):
    if not request.user.is_superuser:
        messages.error(request, 'Only superusers can delete clients.')
        return redirect('client_list')
    obj = get_object_or_404(Client, pk=pk)
    log_action(request, 'delete', 'Client', obj)
    obj.delete()
    messages.success(request, 'Client deleted.')
    return redirect('client_list')


@login_required
@require_POST
def add_client_category(request):
    name = request.POST.get('name', '').strip()
    if not name:
        return JsonResponse({'ok': False, 'error': 'Category name is required.'})
    cat, created = ClientCategory.objects.get_or_create(name=name)
    if not created:
        return JsonResponse({'ok': False, 'error': 'Category already exists.'})
    return JsonResponse({'ok': True, 'name': cat.name})


@login_required
@require_POST
def client_update_state(request, pk):
    client = get_object_or_404(Client, pk=pk)
    new_state = request.POST.get('status', '')
    if new_state in ['active', 'inactive']:
        client.status = new_state
        client.save(update_fields=['status', 'updated_at'])
        log_action(request, 'update', 'Client', client, description=f'Status changed to {new_state}')
        return JsonResponse({'ok': True, 'status': new_state})
    return JsonResponse({'ok': False, 'error': 'Invalid status.'})


@login_required
def client_statement(request, pk):
    from django.db.models import Sum
    client = get_object_or_404(Client, pk=pk)
    invoices = client.invoices.all().order_by('created_at')
    payments = client.payments.all().order_by('created_at')
    transactions = []
    for inv in invoices:
        transactions.append({
            'date': inv.created_at,
            'type': 'Invoice',
            'description': f'{inv.code} — {inv.get_status_display}',
            'debit': float(inv.total),
            'credit': 0,
        })
    for p in payments:
        transactions.append({
            'date': p.created_at,
            'type': 'Payment',
            'description': f'{p.get_method_display}' + (f' ({p.invoice.code})' if p.invoice else ''),
            'debit': 0,
            'credit': float(p.amount),
        })
    transactions.sort(key=lambda t: t['date'])
    balance = 0
    for t in transactions:
        balance += t['debit'] - t['credit']
        t['balance'] = balance
    total_invoiced = sum(t['debit'] for t in transactions)
    total_paid = sum(t['credit'] for t in transactions)
    return render(request, 'clients/client_statement.html', {
        'client': client,
        'transactions': transactions,
        'total_invoiced': total_invoiced,
        'total_paid': total_paid,
        'balance_due': total_invoiced - total_paid,
    })
