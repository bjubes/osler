# Generated by Django 3.1.2 on 2020-12-24 01:45

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('prescriptions', '0002_auto_20201222_1723'),
    ]

    operations = [
        migrations.RenameField(
            model_name='prescription',
            old_name='name',
            new_name='drug_name',
        ),
    ]