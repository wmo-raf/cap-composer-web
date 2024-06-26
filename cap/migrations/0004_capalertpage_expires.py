# Generated by Django 5.0.6 on 2024-06-19 09:00

from django.db import migrations, models

from cap.models import CapAlertPage


def add_expiry_dates(apps, schema_editor):
    alerts = CapAlertPage.objects.all()

    print(f"Found {len(alerts)} alerts")

    for i, cap_alert_page in enumerate(alerts):
        print(f"Updating alert {i + 1} of {len(alerts)}")
        alert_infos = cap_alert_page.info
        for info in alert_infos:
            expires = info.value.get("expires")
            if expires:
                cap_alert_page.expires = expires
                cap_alert_page.save()


def backwards(apps, schema_editor):
    """nothing to do"""
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('cap', '0003_alter_capalertpage_options_alter_capalertpage_guid_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='capalertpage',
            name='expires',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(add_expiry_dates, backwards),
    ]
