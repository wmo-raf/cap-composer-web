# Generated by Django 5.0.6 on 2024-06-19 08:34

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('cap', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='capalertpage',
            old_name='identifier',
            new_name='guid'
        ),
    ]
