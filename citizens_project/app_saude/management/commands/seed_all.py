from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Executa todos os comandos de seed em sequência."

    def handle(self, *args, **options):
        seeds = [
            "seed_domains",
            "seed_concept_classes",
            "seed_vocabularies",
            "seed_concepts",
            "seed_interests",
        ]
        for seed in seeds:
            self.stdout.write(self.style.NOTICE(f"Executando {seed}..."))
            try:
                call_command(seed)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Erro ao executar {seed}: {e}"))
                raise CommandError(f"Erro ao executar {seed}")
        self.stdout.write(self.style.SUCCESS("Todos os seeds executados com sucesso!"))
