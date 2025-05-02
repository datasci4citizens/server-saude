from django.core.management.base import BaseCommand

from app_saude.models import Concept, ConceptSynonym, Domain

# app_saude/management/commands/seed_concepts.py


class Command(BaseCommand):
    help = "Popula os principais conceitos OMOP customizados e traduzidos"

    def handle(self, *args, **kwargs):
        def domain(id_nome):
            return Domain.objects.get_or_create(domain_id=id_nome, defaults={"domain_name": id_nome})[0]

        def add_concept(cid, name, class_id, code, domain_id, pt_name=None):
            d = domain(domain_id)
            concept, _ = Concept.objects.update_or_create(
                concept_id=cid,
                defaults={
                    "concept_name": name,
                    "concept_class_id": class_id,
                    "concept_code": code,
                    "domain": d,
                },
            )
            if pt_name:
                ConceptSynonym.objects.update_or_create(
                    concept=concept, concept_synonym_name=pt_name, language_concept_id=4180186  # pt
                )

        # Idioma pt
        domain("Language")
        Concept.objects.update_or_create(
            concept_id=4180186,
            defaults={
                "concept_name": "Portuguese",
                "concept_class_id": "Language",
                "concept_code": "pt",
                "domain": Domain.objects.get(domain_id="Language"),
            },
        )

        # Gênero
        add_concept(8507, "MALE", "Gender", "M", "Gender", "Masculino")
        add_concept(8532, "FEMALE", "Gender", "F", "Gender", "Feminino")
        add_concept(8551, "UNKNOWN", "Gender", "U", "Gender", "Desconhecido")

        # Etnias
        add_concept(8527, "WHITE", "Race", "W", "Race", "Branco")
        add_concept(8516, "BLACK OR AFRICAN AMERICAN", "Race", "B", "Race", "Preto")
        add_concept(8657, "ASIAN", "Race", "A", "Race", "Asiático")

        # Measurements
        add_concept(3025315, "Body Weight", "Measurement", "BW", "Measurement", "Peso corporal")
        add_concept(3023540, "Body Height", "Measurement", "BH", "Measurement", "Altura corporal")

        # SleepHealth
        add_concept(9000001, "Sleep Quality: Good", "SleepHealth", "SLEEP_GOOD", "Observation", "Sono bom")
        add_concept(9000002, "Sleep Quality: Poor", "SleepHealth", "SLEEP_POOR", "Observation", "Sono ruim")

        # PhysicalExercise
        add_concept(9000010, "Exercises Regularly", "PhysicalExercise", "EX_REG", "Observation", "Exercício regular")
        add_concept(9000011, "Sedentary", "PhysicalExercise", "EX_NONE", "Observation", "Sedentário")

        # EatingHabits
        add_concept(9000020, "Healthy Diet", "EatingHabits", "DIET_HEALTHY", "Observation", "Dieta saudável")
        add_concept(9000021, "Unhealthy Diet", "EatingHabits", "DIET_POOR", "Observation", "Dieta ruim")

        # Comorbidities
        add_concept(9000030, "Hypertension", "Comorbidity", "HTN", "Condition", "Hipertensão")
        add_concept(9000031, "Diabetes", "Comorbidity", "DM", "Condition", "Diabetes")

        # Medications
        add_concept(9000040, "Fluoxetine", "Medication", "FLX", "Drug", "Fluoxetina")
        add_concept(9000041, "Ibuprofen", "Medication", "IBU", "Drug", "Ibuprofeno")

        # SubstanceUse
        add_concept(9000050, "Alcohol Use", "SubstanceUse", "ALC", "Observation", "Uso de álcool")
        add_concept(9000051, "Tobacco Use", "SubstanceUse", "TOB", "Observation", "Uso de tabaco")

        self.stdout.write(self.style.SUCCESS("✔️  Conceitos populados com sucesso."))
