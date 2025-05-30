# Generated by Django 5.2 on 2025-05-08 23:28

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app_saude", "0015_alter_recurrencerule_weekday_binary"),
    ]

    operations = [
        migrations.RenameField(
            model_name="factrelationship",
            old_name="domain_concept_id_1",
            new_name="domain_concept_1",
        ),
        migrations.RenameField(
            model_name="factrelationship",
            old_name="domain_concept_id_2",
            new_name="domain_concept_2",
        ),
        migrations.RemoveField(
            model_name="drugexposure",
            name="drug_exposure_end_date",
        ),
        migrations.RemoveField(
            model_name="drugexposure",
            name="drug_exposure_start_date",
        ),
        migrations.AddField(
            model_name="visitoccurrence",
            name="recurrence_source_visit",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="recurrence_instances",
                to="app_saude.visitoccurrence",
            ),
        ),
    ]
