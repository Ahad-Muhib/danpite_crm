from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from core.models import log_action
from .forms import OrderForm
from .models import Order


@login_required
def order_list(request):
    if request.method == 'POST' and 'bulk_action' in request.POST:
        selected_ids = request.POST.getlist('selected_orders')
        if not selected_ids:
            messages.error(request, 'Select at least one order first.')
            return redirect('order_list')
        if not request.user.is_superuser:
            messages.error(request, 'Only superusers can delete orders.')
            return redirect('order_list')
        for o in Order.objects.filter(pk__in=selected_ids):
            log_action(request, 'delete', 'Order', o, description=o.order_number)
            o.delete()
        messages.success(request, f'{len(selected_ids)} order(s) deleted.')
        return redirect('order_list')
    q = request.GET.get('q', '')
    status = request.GET.get('status', '')
    qs = Order.objects.all().order_by('-id')
    if q:
        qs = qs.filter(Q(order_number__icontains=q))
    if status:
        qs = qs.filter(status=status)
    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'orders/orders.html', {'orders': page, 'q': q, 'status': status})


@login_required
def order_create(request):
    form = OrderForm(request.POST or None)
    if form.is_valid():
        obj = form.save()
        log_action(request, 'create', 'Order', obj)
        messages.success(request, 'Order created.')
        return redirect('order_list')
    return render(request, 'orders/order_form.html', {'form': form, 'action': 'Create'})


@login_required
def order_edit(request, pk):
    obj = get_object_or_404(Order, pk=pk)
    form = OrderForm(request.POST or None, instance=obj)
    if form.is_valid():
        obj = form.save()
        log_action(request, 'update', 'Order', obj)
        messages.success(request, 'Order updated.')
        return redirect('order_list')
    return render(request, 'orders/order_form.html', {'form': form, 'action': 'Edit'})


@login_required
def order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk)
    items = order.items.all()
    return render(request, 'orders/order_detail.html', {'order': order, 'items': items})


@login_required
def order_delete(request, pk):
    if not request.user.is_superuser:
        messages.error(request, 'Only superusers can delete orders.')
        return redirect('order_list')
    obj = get_object_or_404(Order, pk=pk)
    log_action(request, 'delete', 'Order', obj)
    obj.delete()
    messages.success(request, 'Order deleted.')
    return redirect('order_list')
