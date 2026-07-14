from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import OrderForm
from .models import Order


@login_required
def order_list(request):
    q = request.GET.get('q', '')
    status = request.GET.get('status', '')
    qs = Order.objects.all()
    if q:
        qs = qs.filter(Q(order_number__icontains=q))
    if status:
        qs = qs.filter(status=status)
    return render(request, 'orders/orders.html', {'orders': qs, 'q': q, 'status': status})


@login_required
def order_create(request):
    form = OrderForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Order created.')
        return redirect('order_list')
    return render(request, 'orders/order_form.html', {'form': form, 'action': 'Create'})


@login_required
def order_edit(request, pk):
    obj = get_object_or_404(Order, pk=pk)
    form = OrderForm(request.POST or None, instance=obj)
    if form.is_valid():
        form.save()
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
    get_object_or_404(Order, pk=pk).delete()
    messages.success(request, 'Order deleted.')
    return redirect('order_list')
