from django.db import migrations


def clear_cash_holder_names(apps, schema_editor):
    BankAccount = apps.get_model('accounts', 'BankAccount')
    BankAccount.objects.filter(account_category__account_type='cash').update(holder_name='')


def reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0021_seed_expense_categories'),
    ]

    operations = [
        migrations.RunPython(clear_cash_holder_names, reverse),
    ]