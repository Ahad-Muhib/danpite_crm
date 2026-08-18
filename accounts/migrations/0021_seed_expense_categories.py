from django.db import migrations

PREDEFINED_CATEGORIES = ['Office Supplies', 'Marketing', 'Travel', 'Utilities', 'Rent', 'Salary', 'Equipment', 'Other']


def seed(apps, schema_editor):
    ExpenseCategory = apps.get_model('accounts', 'ExpenseCategory')
    for name in PREDEFINED_CATEGORIES:
        ExpenseCategory.objects.get_or_create(name=name)


def unseed(apps, schema_editor):
    ExpenseCategory = apps.get_model('accounts', 'ExpenseCategory')
    ExpenseCategory.objects.filter(name__in=PREDEFINED_CATEGORIES).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0020_alter_expense_method_alter_payment_method'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]