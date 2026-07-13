from django.contrib import admin

from .models import AccountEntry, Client, Expense, Invoice, Payment, StaffProfile

admin.site.register(StaffProfile)
admin.site.register(Client)
admin.site.register(Invoice)
admin.site.register(Payment)
admin.site.register(Expense)
admin.site.register(AccountEntry)
