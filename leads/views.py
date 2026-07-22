from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from clients.models import Client

from .forms import DealForm, FollowUpForm, LeadContactForm
from .models import Deal, FollowUp, LeadContact


@login_required
def lead_list(request):
    if request.method == 'POST' and 'bulk_action' in request.POST:
        selected_ids = request.POST.getlist('selected_leads')
        action = request.POST.get('bulk_action')
        selected = LeadContact.objects.filter(pk__in=selected_ids)

        if not selected_ids:
            messages.error(request, 'Select at least one lead contact first.')
            return redirect('lead_list')

        if action == 'convert':
            converted_count = 0
            for lead in selected.filter(is_converted=False):
                Client.objects.create(
                    name=lead.name,
                    email=lead.email,
                    phone=lead.phone,
                    company=lead.company,
                    website=lead.website,
                    address=lead.address,
                    account_manager=request.user,
                    lead_contact=lead,
                )
                lead.is_converted = True
                lead.save(update_fields=['is_converted', 'updated_at'])
                converted_count += 1
            messages.success(request, f'{converted_count} lead contact(s) converted to client.')
        elif action == 'delete':
            deleted_count = selected.count()
            selected.delete()
            messages.success(request, f'{deleted_count} lead contact(s) deleted.')
        else:
            messages.error(request, 'Choose a bulk action first.')
        return redirect('lead_list')

    q = request.GET.get('q', '')
    src = request.GET.get('source', '')
    contact_type = request.GET.get('type', '')
    qs = LeadContact.objects.all().order_by('-id')
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(email__icontains=q) | Q(phone__icontains=q) | Q(company__icontains=q))
    if src:
        qs = qs.filter(lead_source=src)
    if contact_type in ('lead', 'deal'):
        qs = qs.filter(contact_type=contact_type)
    source_options = LeadContact.objects.exclude(lead_source='').values_list('lead_source', flat=True).distinct().order_by('lead_source')
    return render(request, 'leads/leads.html', {
        'leads': qs,
        'q': q,
        'source': src,
        'contact_type': contact_type,
        'source_options': source_options,
    })


def _lead_source_options():
    saved = LeadContact.objects.exclude(lead_source='').values_list('lead_source', flat=True).distinct()
    return sorted(set(LeadContact.SOURCE_SUGGESTIONS) | set(saved))


@login_required
def lead_create(request):
    form = LeadContactForm(request.POST or None)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.added_by = request.user
        obj.save()
        messages.success(request, 'Lead contact added.')
        return redirect('lead_list')
    return render(request, 'leads/lead_form.html', {
        'form': form,
        'action': 'Add',
        'lead_source_options': _lead_source_options(),
    })


@login_required
def lead_edit(request, pk):
    obj = get_object_or_404(LeadContact, pk=pk)
    form = LeadContactForm(request.POST or None, instance=obj)
    if form.is_valid():
        form.save()
        messages.success(request, 'Lead updated.')
        return redirect('lead_list')
    return render(request, 'leads/lead_form.html', {
        'form': form,
        'action': 'Edit',
        'lead': obj,
        'lead_source_options': _lead_source_options(),
    })


@login_required
def lead_detail(request, pk):
    from django.utils import timezone
    lead = get_object_or_404(LeadContact, pk=pk)
    deals = lead.deals.all()
    followups = lead.followups.all().order_by('-created_at')[:10]
    today = timezone.now().date()
    return render(request, 'leads/lead_detail.html', {'lead': lead, 'deals': deals, 'followups': followups, 'today': today})


@login_required
def lead_delete(request, pk):
    get_object_or_404(LeadContact, pk=pk).delete()
    messages.success(request, 'Lead deleted.')
    return redirect('lead_list')


@login_required
def lead_toggle_active(request, pk):
    obj = get_object_or_404(LeadContact, pk=pk)
    if obj.is_converted:
        Client.objects.filter(lead_contact=obj).delete()
        obj.is_converted = False
        obj.save()
        messages.success(request, f'{obj.name} set to active. Client removed.')
    else:
        Client.objects.create(
            name=obj.name,
            email=obj.email,
            phone=obj.phone,
            company=obj.company,
            website=obj.website,
            address=obj.address,
            account_manager=request.user,
            lead_contact=obj,
        )
        obj.is_converted = True
        obj.save()
        messages.success(request, f'{obj.name} converted to client.')
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
        lead_contact=lead,
    )
    lead.is_converted = True
    lead.save()
    messages.success(request, f'{lead.name} converted to client.')
    return redirect('lead_list')


@login_required
def deal_list(request):
    from django.utils import timezone
    today = timezone.now().date()
    qs = Deal.objects.all().order_by('-created_at')
    return render(request, 'leads/deals.html', {'deals': qs, 'today': today})


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


@login_required
def followup_list(request):
    q = request.GET.get('q', '')
    ftype = request.GET.get('type', '')
    upcoming = request.GET.get('upcoming', '')
    from django.utils import timezone
    today = timezone.now().date()
    qs = FollowUp.objects.select_related('lead', 'deal', 'created_by').all()
    if q:
        qs = qs.filter(Q(subject__icontains=q) | Q(lead__name__icontains=q) | Q(deal__deal_name__icontains=q) | Q(notes__icontains=q))
    if ftype in ('call', 'email', 'meeting', 'note', 'other'):
        qs = qs.filter(followup_type=ftype)
    if upcoming == '1':
        qs = qs.filter(next_followup_date__gte=today).order_by('next_followup_date')
    elif upcoming == '0':
        qs = qs.filter(next_followup_date__lt=today).order_by('-next_followup_date')
    else:
        qs = qs.order_by('-created_at')
    return render(request, 'leads/followups.html', {
        'followups': qs,
        'q': q,
        'ftype': ftype,
        'upcoming': upcoming,
        'today': today,
    })


@login_required
def followup_create(request):
    initial = {}
    lead_id = request.GET.get('lead')
    deal_id = request.GET.get('deal')
    if lead_id:
        initial['lead'] = lead_id
    if deal_id:
        initial['deal'] = deal_id
    form = FollowUpForm(request.POST or None, initial=initial)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.created_by = request.user
        obj.save()
        if lead_id:
            return redirect('lead_detail', pk=lead_id)
        messages.success(request, 'Follow-up logged.')
        return redirect('followup_list')
    return render(request, 'leads/followup_form.html', {'form': form, 'action': 'Log'})


@login_required
def followup_delete(request, pk):
    obj = get_object_or_404(FollowUp, pk=pk)
    lead_pk = obj.lead_id
    obj.delete()
    messages.success(request, 'Follow-up deleted.')
    if lead_pk:
        return redirect('lead_detail', pk=lead_pk)
    return redirect('followup_list')
