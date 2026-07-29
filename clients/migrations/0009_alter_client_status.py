from django.db import migrations, models


def migrate_state_values(apps, schema_editor):
    Client = apps.get_model('clients', 'Client')
    Client.objects.filter(status='open').update(status='active')
    Client.objects.filter(status='closed').update(status='inactive')


def reverse_migrate_state_values(apps, schema_editor):
    Client = apps.get_model('clients', 'Client')
    Client.objects.filter(status='active').update(status='open')
    Client.objects.filter(status='inactive').update(status='closed')


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0008_migrate_client_state'),
    ]

    operations = [
        migrations.RunPython(migrate_state_values, reverse_migrate_state_values),
        migrations.AlterField(
            model_name='client',
            name='status',
            field=models.CharField(choices=[('active', 'Active'), ('inactive', 'Inactive')], default='active', max_length=20),
        ),
    ]
