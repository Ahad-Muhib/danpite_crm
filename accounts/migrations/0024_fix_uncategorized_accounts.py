from django.db import migrations


def fix_uncategorized(apps, schema_editor):
    AccountCategory = apps.get_model('accounts', 'AccountCategory')
    BankAccount = apps.get_model('accounts', 'BankAccount')
    for name, atype in [('Cash', 'cash'), ('Bank', 'bank'), ('Card', 'bank'),
                        ('bKash', 'mobile'), ('Nagad', 'mobile'), ('Rocket', 'mobile'), ('Upay', 'mobile')]:
        AccountCategory.objects.get_or_create(name=name, defaults={'account_type': atype, 'is_active': True})
    for acct in BankAccount.objects.all():
        if acct.account_category_id is not None:
            continue
        cat = None
        if acct.contact_number:
            cat = AccountCategory.objects.filter(name__iexact='cash').first()
        elif acct.mobile_number:
            cat = AccountCategory.objects.filter(name__iexact=acct.mobile_provider).first() or \
                  AccountCategory.objects.filter(name__iexact='bKash').first()
        elif acct.account_number:
            cat = AccountCategory.objects.filter(name__iexact='bank').first()
        if cat:
            acct.account_category = cat
            acct.save(update_fields=['account_category'])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0023_alter_payment_amount'),
    ]

    operations = [
        migrations.RunPython(fix_uncategorized, noop),
    ]