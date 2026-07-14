from django.contrib import admin

from .models import Client


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'mobile', 'category', 'status']
    list_filter = ['category', 'status']
    search_fields = ['name', 'email', 'company']

