# Generated by Django 5.2 on 2025-06-09 02:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app_saude", "0021_person_profile_picture_provider_profile_picture"),
    ]

    operations = [
        migrations.AlterField(
            model_name="observation",
            name="value_as_string",
            field=models.CharField(blank=True, db_comment="Free-text value", max_length=1000, null=True),
        ),
    ]
