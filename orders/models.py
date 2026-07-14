from django.contrib.auth.models import User
from django.db import models

from clients.models import Client


class Order(models.Model):
    STATUS = [('pending', 'Pending'), ('processing', 'Processing'), ('shipped', 'Shipped'), ('delivered', 'Delivered'), ('cancelled', 'Cancelled')]
    order_number = models.CharField(max_length=50, unique=True, blank=True)
    client = models.ForeignKey(Client, null=True, blank=True, on_delete=models.SET_NULL, related_name='orders')
    status = models.CharField(max_length=20, choices=STATUS, default='pending')
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    assigned_to = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    order_date = models.DateField(auto_now_add=True)
    delivery_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.order_number

    def save(self, *args, **kwargs):
        if not self.order_number:
            last = Order.objects.order_by('id').last()
            self.order_number = f"ORD-{(last.id + 1 if last else 1):04d}"
        super().save(*args, **kwargs)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product_name = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        self.total = self.quantity * self.unit_price
        super().save(*args, **kwargs)

