from django.db import migrations, models
import django.db.models.deletion


CATEGORY_MAP = {
    'bank': ('Bank', 'bank'),
    'bkash': ('bKash', 'mobile'),
    'nagad': ('Nagad', 'mobile'),
    'rocket': ('Rocket', 'mobile'),
    'card': ('Card', 'bank'),
}


def populate_account_categories(apps, schema_editor):
    AccountCategory = apps.get_model('accounts', 'AccountCategory')
    for key, (name, atype) in CATEGORY_MAP.items():
        AccountCategory.objects.get_or_create(name=name, account_type=atype)


def migrate_bank_account_categories(apps, schema_editor):
    AccountCategory = apps.get_model('accounts', 'AccountCategory')
    BankAccount = apps.get_model('accounts', 'BankAccount')

    for acct in BankAccount.objects.all():
        old_cat = acct.category
        if old_cat in CATEGORY_MAP:
            name, atype = CATEGORY_MAP[old_cat]
            cat = AccountCategory.objects.filter(name=name, account_type=atype).first()
            if cat:
                acct.account_category = cat

        if old_cat in ('bkash', 'nagad', 'rocket'):
            acct.mobile_provider = old_cat
            # preserve card info in details
        elif old_cat == 'card':
            parts = []
            if acct.card_holder:
                parts.append(f'Card Holder: {acct.card_holder}')
            if acct.card_number:
                parts.append(f'Card Number: {acct.card_number}')
            if acct.card_bank:
                parts.append(f'Card Bank: {acct.card_bank}')
            if parts:
                card_detail = ' | '.join(parts)
                if acct.details:
                    acct.details = card_detail + '\n' + acct.details
                else:
                    acct.details = card_detail

        acct.save()


def reverse_migrate(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0013_transfer'),
    ]

    operations = [
        migrations.CreateModel(
            name='AccountCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True)),
                ('account_type', models.CharField(choices=[('bank', 'Bank'), ('mobile', 'Mobile Banking'), ('cash', 'Cash')], max_length=20)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name_plural': 'Account Categories',
                'ordering': ['account_type', 'name'],
            },
        ),
        migrations.AddField(
            model_name='BankAccount',
            name='account_category',
            field=models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL, related_name='accounts', to='accounts.AccountCategory'),
        ),
        migrations.AddField(
            model_name='BankAccount',
            name='mobile_provider',
            field=models.CharField(blank=True, choices=[('bkash', 'bKash'), ('nagad', 'Nagad'), ('upay', 'Upay'), ('rocket', 'Rocket')], max_length=20),
        ),
        migrations.AddField(
            model_name='BankAccount',
            name='contact_number',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name='BankAccount',
            name='currency',
            field=models.CharField(blank=True, default='BDT', max_length=5),
        ),
        migrations.RunPython(populate_account_categories, reverse_migrate),
        migrations.RunPython(migrate_bank_account_categories, reverse_migrate),
        migrations.RemoveField(
            model_name='BankAccount',
            name='category',
        ),
        migrations.RemoveField(
            model_name='BankAccount',
            name='card_number',
        ),
        migrations.RemoveField(
            model_name='BankAccount',
            name='card_holder',
        ),
        migrations.RemoveField(
            model_name='BankAccount',
            name='card_type',
        ),
        migrations.RemoveField(
            model_name='BankAccount',
            name='card_bank',
        ),
        migrations.AlterField(
            model_name='BankAccount',
            name='account_type',
            field=models.CharField(blank=True, choices=[('savings', 'Savings'), ('current', 'Current'), ('fixed', 'Fixed Deposit'), ('other', 'Other')], default='current', max_length=20),
        ),
    ]
