from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from clients.models import Client

from .forms import DealForm, LeadContactForm
from .models import Deal, LeadContact


@login_required
def lead_list(request):
    q = request.GET.get('q', '')
    src = request.GET.get('source', '')
    qs = LeadContact.objects.all()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(email__icontains=q) | Q(company__icontains=q))
    if src:
        qs = qs.filter(lead_source=src)
    return render(request, 'leads/leads.html', {'leads': qs, 'q': q, 'source': src})


@login_required
def lead_create(request):
    form = LeadContactForm(request.POST or None)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.added_by = request.user
        obj.save()
        messages.success(request, 'Lead contact added.')
        return redirect('lead_list')
    return render(request, 'leads/lead_form.html', {'form': form, 'action': 'Add'})


@login_required
def lead_edit(request, pk):
    obj = get_object_or_404(LeadContact, pk=pk)
    form = LeadContactForm(request.POST or None, instance=obj)
    if form.is_valid():
        form.save()
        messages.success(request, 'Lead updated.')
        return redirect('lead_list')
    return render(request, 'leads/lead_form.html', {'form': form, 'action': 'Edit', 'lead': obj})


@login_required
def lead_detail(request, pk):
    lead = get_object_or_404(LeadContact, pk=pk)
    deals = lead.deals.all()
    return render(request, 'leads/lead_detail.html', {'lead': lead, 'deals': deals})


@login_required
def lead_delete(request, pk):
    get_object_or_404(LeadContact, pk=pk).delete()
    messages.success(request, 'Lead deleted.')
    return redirect('lead_list')


@login_required
def lead_convert(request, pk):
    lead = get_object_or_404(LeadContact, pk=pk)
    Client.objects.create(
        name=lead.name,
        email=lead.email,
        phone=lead.phone,
        company=lead.company,
        website=lead.website,
        address=lead.address,
        account_manager=request.user,
    )
    lead.is_converted = True
    lead.save()
    messages.success(request, f'{lead.name} converted to client.')
    return redirect('lead_list')


@login_required
def deal_list(request):
    qs = Deal.objects.all().order_by('-created_at')
    return render(request, 'leads/deals.html', {'deals': qs})


@login_required
def deal_create(request):
    form = DealForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Deal created.')
        return redirect('deal_list')
    return render(request, 'leads/deal_form.html', {'form': form, 'action': 'Create'})


@login_required
def deal_edit(request, pk):
    obj = get_object_or_404(Deal, pk=pk)
    form = DealForm(request.POST or None, instance=obj)
    if form.is_valid():
        form.save()
        messages.success(request, 'Deal updated.')
        return redirect('deal_list')
    return render(request, 'leads/deal_form.html', {'form': form, 'action': 'Edit'})


@login_required
def deal_delete(request, pk):
    get_object_or_404(Deal, pk=pk).delete()
    messages.success(request, 'Deal deleted.')
    return redirect('deal_list')
