from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from app_saude.models import *


class Command(BaseCommand):

    def handle(self, *args, **kwargs):

        def add_concept(cid, name, class_id, code, domain_id, vocabulary_id, pt_name=None):
            defaults = {
                "concept_name": name,
                "concept_code": code,
            }

            if class_id is not None:
                defaults["concept_class"] = ConceptClass.objects.get(concept_class_id=class_id)

            if domain_id is not None:
                defaults["domain"] = Domain.objects.get(domain_id=domain_id)

            if vocabulary_id is not None:
                defaults["vocabulary_id"] = vocabulary_id

            concept, _ = Concept.objects.update_or_create(
                concept_id=cid,
                defaults=defaults,
            )

            if pt_name:
                ConceptSynonym.objects.update_or_create(
                    concept=concept,
                    language_concept_id=4181536,
                    defaults={
                        "concept_synonym_name": pt_name,
                    },
                )

        # Portuguese concept
        add_concept(4181536, "Portuguese language", "Qualifier Value", "297504001", "Language", "SNOMED", "Português")

        # None concept (IMPORTED FROM ATHENA 03/05/2025)
        add_concept(0, None, None, None, "Metadata", None, "Sem conceito correspondente")

        # Gender (IMPORTED FROM ATHENA 02/05/2025)
        add_concept(8507, "MALE", "Gender", "M", "Gender", "Gender", "Masculino")
        add_concept(8532, "FEMALE", "Gender", "F", "Gender", "Gender", "Feminino")
        add_concept(8551, "UNKNOWN", "Gender", "U", "Gender", "Gender", "Outro")

        # Race (IMPORTED FROM ATHENA 02/05/2025)Add commentMore actions
        add_concept(8515, "Asian", "Race", "2", "Race", "Race", "Asiático")
        add_concept(8527, "White", "Race", "5", "Race", "Race", "Branco")
        add_concept(38003572, "American Indian", "Race", "1.01", "Race", "Race", "Indígena Americano")
        add_concept(38003598, "Black", "Race", "3.01", "Race", "Race", "Preto")

        # Speciality (IMPORTED FROM ATHENA 03/05/2025)Add commentMore actions
        add_concept(32577, "Physician", "Physician Specialty", "OMOP4822444", "Provider", "Provider", "Médica(o)")
        add_concept(32578, "Counselor", "Provider", "OMOP4822447", "Provider", "Provider", "Terapeuta")
        add_concept(32580, "Allied Health Professional", "Provider", "OMOP4822445", "Provider", "Provider", "ACS")
        add_concept(32581, "Nurse", "Provider", "OMOP4822446", "Provider", "Provider", "Enfermeira(o)")
        add_concept(33003, "Service Provider", "Provider", "OMOP5117445", "Provider", "Provider", "Provedor de Serviço")
        add_concept(
            33005,
            "Psychiatry or Neurology",
            "Physician Specialty",
            "OMOP5117448",
            "Provider",
            "Provider",
            "Psiquiatra ou Neurologista",
        )

        # ==========================
        # Custom Concepts
        # ==========================

        # States
        add_concept(2000001000, "AC", "Brazil States", None, "Geography", None, "AC")
        add_concept(2000001001, "AL", "Brazil States", None, "Geography", None, "AL")
        add_concept(2000001002, "AP", "Brazil States", None, "Geography", None, "AP")
        add_concept(2000001003, "AM", "Brazil States", None, "Geography", None, "AM")
        add_concept(2000001004, "BA", "Brazil States", None, "Geography", None, "BA")
        add_concept(2000001005, "CE", "Brazil States", None, "Geography", None, "CE")
        add_concept(2000001006, "DF", "Brazil States", None, "Geography", None, "DF")
        add_concept(2000001007, "ES", "Brazil States", None, "Geography", None, "ES")
        add_concept(2000001008, "GO", "Brazil States", None, "Geography", None, "GO")
        add_concept(2000001009, "MA", "Brazil States", None, "Geography", None, "MA")
        add_concept(2000001010, "MT", "Brazil States", None, "Geography", None, "MT")
        add_concept(2000001011, "MS", "Brazil States", None, "Geography", None, "MS")
        add_concept(2000001012, "MG", "Brazil States", None, "Geography", None, "MG")
        add_concept(2000001013, "PA", "Brazil States", None, "Geography", None, "PA")
        add_concept(2000001014, "PB", "Brazil States", None, "Geography", None, "PB")
        add_concept(2000001015, "PR", "Brazil States", None, "Geography", None, "PR")
        add_concept(2000001016, "PE", "Brazil States", None, "Geography", None, "PE")
        add_concept(2000001017, "PI", "Brazil States", None, "Geography", None, "PI")
        add_concept(2000001018, "RJ", "Brazil States", None, "Geography", None, "RJ")
        add_concept(2000001019, "RN", "Brazil States", None, "Geography", None, "RN")
        add_concept(2000001020, "RS", "Brazil States", None, "Geography", None, "RS")
        add_concept(2000001021, "RO", "Brazil States", None, "Geography", None, "RO")
        add_concept(2000001022, "RR", "Brazil States", None, "Geography", None, "RR")
        add_concept(2000001023, "SC", "Brazil States", None, "Geography", None, "SC")
        add_concept(2000001024, "SP", "Brazil States", None, "Geography", None, "SP")
        add_concept(2000001025, "SE", "Brazil States", None, "Geography", None, "SE")
        add_concept(2000001026, "TO", "Brazil States", None, "Geography", None, "TO")

        # Measurements
        add_concept(2000002000, "Body Weight", "Measurement", "BW", None, None, "Peso corporal")
        add_concept(2000002001, "Body Height", "Measurement", "BH", None, None, "Altura corporal")

        # Observation Type
        add_concept(2000003000, "Self Reported", "Observation", "SR", None, None, "Auto-relatado")

        # Relationship
        add_concept(
            2000004000, "Provider Link Code", "Observation", "PROVIDER_LINK_CODE", None, None, "Código de vínculo"
        )
        add_concept(
            2000004001,
            "Clinician Generated",
            None,
            "CLINICIAN_GENERATED",
            None,
            "Observation Type",
            "Gerado pelo profissional",
        )
        add_concept(2000004002, "Person to Provider", None, "PERSON_PROVIDER", None, "Relationship", "Pessoa associada")

        # User Role
        add_concept(2000005001, "Provider", None, "PERSON", None, None, "Profissional de saúde")
        add_concept(2000005002, "Person", None, "PROVIDER", None, None, "Indivíduo")

        # Diary
        add_concept(2000006000, "Diary Entry", None, "diary_entry", None, None, "Entrada de diário")
        add_concept(2000006001, "Diary Text", None, "diary_text", None, None, "Texto livre do diário")
        add_concept(2000006002, "Diary Scope", None, "diary_scope", None, None, "Alcance do diário")
        add_concept(2000006003, "Diary Entry Type", None, "diary_entry_type", None, None, "Tipo de entrada")
        add_concept(2000006004, "Diary interest", None, "diary_interest", None, None, "Alcance do diário")

        # Help
        add_concept(2000007000, "Help", None, "HELP", None, None, "Ajuda")
        add_concept(2000007001, "Active", None, "ACTIVE", None, None, "Ativo")
        add_concept(2000007002, "Resolved", None, "RESOLVED", None, None, "Resolvido")

        # Area of Interest
        add_concept(2000008000, "Interest Area", None, "INTEREST_AREA", None, None, "Área de Interesse")
        add_concept(2000008001, "Trigger", None, "TRIGGER", None, None, "Gatilho")

        # Fact Relationships
        add_concept(2000009000, "AOI_Trigger", None, "AOI_TRIGGER", None, None, "Gatilho de Área de Interesse")
        add_concept(2000009001, "AOI_Diary", None, "AOI_DIARY", None, None, "Diario area de interesse")
        add_concept(2000009002, "Text_Diary", None, "TEXT_DIARY", None, None, "Diario area de interesse")

        self.stdout.write(self.style.SUCCESS("✔️  Concepts populated successfully."))
