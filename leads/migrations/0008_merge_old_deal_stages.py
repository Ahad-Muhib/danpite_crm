from django.db import migrations


def forwards(apps, schema_editor):
    Deal = apps.get_model('leads', 'Deal')
    Deal.objects.filter(stage__in=['qualified', 'presentation', 'negotiation']).update(stage='generated')


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('leads', '0007_deal_lost_reason_followup_is_recurring_and_more'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
