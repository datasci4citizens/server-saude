from django.core.management.base import BaseCommand
from django.utils.timezone import now
from app_saude.models import Domain, Concept


class Command(BaseCommand):
    help = 'Populate Domain and Concept tables with initial data'

    def handle(self, *args, **kwargs):
        # 1. Create domains
        domain_names = [
            "Biological Sex",
            "Gender Identity",
            "Race",
        ]

        domain_map = {}  # To store created domain instances
        for name in domain_names:
            domain, created = Domain.objects.get_or_create(
                domain_name=name,
                defaults={"created_at": now(), "updated_at": now()}
            )
            domain_map[name] = domain
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created domain: {name}'))
            else:
                self.stdout.write(f'Domain already exists: {name}')

        # 2. Create concepts linked to the domains
        concept_data = {
            "Biological Sex": ["Female", "Male", "Intersex"],
            "Gender Identity": ["Man", "Woman", "Non-binary", "Transgender", "Other", "Rather Not Say"],
            "Race": ["White", "Black", "Asian", "Indigenous", "Mixed"],
        }

        for domain_name, concepts in concept_data.items():
            domain = domain_map.get(domain_name)
            if not domain:
                self.stdout.write(self.style.WARNING(f'Skipping missing domain: {domain_name}'))
                continue

            for concept_name in concepts:
                concept, created = Concept.objects.get_or_create(
                    concept_name=concept_name,
                    domain=domain,
                    defaults={"created_at": now(), "updated_at": now()}
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f'Created concept: {concept_name} (domain: {domain_name})'))
                else:
                    self.stdout.write(f'Concept already exists: {concept_name} (domain: {domain_name})')
