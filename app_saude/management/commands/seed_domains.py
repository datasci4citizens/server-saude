from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import connection

from app_saude.models import *


class Command(BaseCommand):

    def handle(self, *args, **kwargs):

        def domain(id, name, concept_id):
            return Domain.objects.get_or_create(
                domain_id=id,
                defaults={
                    "domain_name": name,
                    "domain_concept": Concept.objects.get_or_create(concept_id=concept_id)[0],
                },
            )

        self.stdout.write("🧹 Truncating all tables...")
        with connection.cursor() as cursor:
            # Disable triggers temporarily to avoid constraint violations
            cursor.execute("SET session_replication_role = 'replica';")

            # Get all table names (excluding Django migrations)
            cursor.execute(
                """
                SELECT tablename 
                FROM pg_tables 
                WHERE schemaname = 'public'
                AND tablename NOT LIKE 'django_migrations'
            """
            )
            tables = [row[0] for row in cursor.fetchall()]

            # Truncate each table
            for table in tables:
                self.stdout.write(f"  → Clearing {table}")
                cursor.execute(f'TRUNCATE TABLE "{table}" CASCADE;')

            # Re-enable triggers
            cursor.execute("SET session_replication_role = 'origin';")

        # domains (IMPORTED FROM ATHENA 14/05/2025)
        domain("Gender", "Gender", 2)
        domain("Race", "Race", 3)
        domain("Ethnicity", "Ethnicity", 4)
        domain("Metadata", "Metadata", 7)
        domain("Visit", "Visit", 8)
        domain("Procedure", "Procedure", 10)
        domain("Modifier", "Modifier", 12)
        domain("Drug", "Drug", 13)
        domain("Route", "Route Of Administration", 15)
        domain("Unit", "Unit", 16)
        domain("Device", "Device", 17)
        domain("Condition", "Condition", 19)
        domain("Measurement", "Measurement", 21)
        domain("Meas Value Operator", "Measurement Value Operator", 23)
        domain("Meas Value", "Measurement Value", 24)
        domain("Observation", "Observation", 27)
        domain("Relationship", "Relationship", 31)
        domain("Place of Service", "Place of Service", 32)
        domain("Provider", "Provider Specialty", 33)
        domain("Currency", "Currency", 34)
        domain("Revenue Code", "Revenue Code", 35)
        domain("Specimen", "Specimen", 36)
        domain("Spec Anatomic Site", "Specimen Anatomic Site", 38)
        domain("Spec Disease Status", "Specimen Disease Status", 39)
        domain("Device/Procedure", "Device/Procedure", 41)
        domain("Obs/Procedure", "Observation/Procedure", 42)
        domain("Meas/Procedure", "Measurement/Procedure", 43)
        domain("Measurement/Obs", "Measurement/Observation", 44)
        domain("Device/Obs", "Device/Observation", 45)
        domain("Condition/Meas", "Condition/Measurement", 47)
        domain("Condition/Obs", "Condition/Observation", 48)
        domain("Condition/Procedure", "Condition/Procedure", 49)
        domain("Device/Drug", "Device/Drug", 50)
        domain("Drug/Measurement", "Drug/Measurement", 51)
        domain("Drug/Obs", "Drug/Observation", 52)
        domain("Condition/Drug", "Condition/Drug", 53)
        domain("Drug/Procedure", "Drug/Procedure", 54)
        domain("Type Concept", "Type Concept", 58)
        domain("Condition/Device", "Condition/Device", 235)
        domain("Note", "Note", 5085)
        domain(
            "Plan",
            "Health Plan - contract to administer healthcare transactions by the payer, facilitated by the sponsor",
            32475,
        )
        domain("Sponsor", "Sponsor - institution or individual financing healthcare transactions", 32476)
        domain("Payer", "Payer - institution administering healthcare transactions", 32477)
        domain("Plan Stop Reason", "Plan Stop Reason - Reason for termination of the Health Plan", 32478)
        domain("Episode", "Episode", 32527)
        domain("Geography", "Geographical object", 32558)
        domain("Regimen", "Treatment Regimen", 32687)
        domain("Condition Status", "OMOP Condition Status", 32889)
        domain("Language", "Language", 33068)
        domain("Cost", "Cost", 581456)

        # Custom domains

        self.stdout.write(self.style.SUCCESS("✔️  Domain classes populated successfully."))
