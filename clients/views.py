from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ClientForm
from .models import Client


@login_required
def client_list(request):
    q = request.GET.get('q', '')
    status = request.GET.get('status', '')
    qs = Client.objects.all()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(email__icontains=q) | Q(company__icontains=q))
    if status:
        qs = qs.filter(status=status)
    return render(request, 'clients/clients.html', {'clients': qs, 'q': q, 'status': status})


@login_required
def client_create(request):
    form = ClientForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Client added.')
        return redirect('client_list')
    return render(request, 'clients/client_form.html', {'form': form, 'action': 'Add'})


@login_required
def client_edit(request, pk):
    obj = get_object_or_404(Client, pk=pk)
    form = ClientForm(request.POST or None, instance=obj)
    if form.is_valid():
        form.save()
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
    get_object_or_404(Client, pk=pk).delete()
    messages.success(request, 'Client deleted.')
    return redirect('client_list')
