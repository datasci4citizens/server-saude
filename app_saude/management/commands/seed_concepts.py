from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from app_saude.models import *

# app_saude/management/commands/seed_concepts.py


class Command(BaseCommand):
    help = "Popula os principais conceitos OMOP customizados e traduzidos"

    def handle(self, *args, **kwargs):
        def domain(id, name, concept_id):
            return Domain.objects.get_or_create(
                domain_id=id,
                defaults={
                    "domain_name": name,
                    "domain_concept": Concept.objects.get_or_create(concept_id=concept_id)[0],
                },
            )

        def vocabulary(id, name, concept_id):
            return Vocabulary.objects.get_or_create(
                vocabulary_id=id,
                defaults={
                    "vocabulary_name": name,
                    "vocabulary_concept": Concept.objects.get_or_create(concept_id=concept_id)[0],
                },
            )

        def concept_class(id, name, concept_id):
            return ConceptClass.objects.get_or_create(
                concept_class_id=id,
                defaults={
                    "concept_class_name": name,
                    "concept_class_concept": Concept.objects.get_or_create(concept_id=concept_id)[0],
                },
            )

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
                    concept=concept, concept_synonym_name=pt_name, language_concept_id=4180186  # pt
                )

        def dummy_person(
            name, year_of_birth=None, gender_concept=None, ethnicity_concept=None, race_concept=None, location=None
        ):
            user, _ = get_user_model().objects.get_or_create(
                username=name, password="dummy_password", first_name=name, last_name="User", email=f"{name}@email.com"
            )
            person, _ = Person.objects.get_or_create(
                user_id=user.id,
                year_of_birth=year_of_birth,
                gender_concept=Concept.objects.get(concept_id=gender_concept),
                # ethnicity_concept = Concept.objects.get(concept_id=ethnicity_concept),
                race_concept=Concept.objects.get(concept_id=race_concept),
                # location
                # ethnicity
            )
            return person

        def relate_concepts(interest_id, trigger_ids, relationship_id):
            for trigger_id in trigger_ids:
                ConceptRelationship.objects.update_or_create(
                    concept_1_id=interest_id, concept_2_id=trigger_id, relationship_id=relationship_id
                )

        # Idioma pt
        concept_class("Language", "Language", 11118)
        domain("Language", "Language", 4180186)
        Concept.objects.update_or_create(
            concept_id=4180186,
            defaults={
                "concept_name": "Portuguese",
                "concept_class_id": "Language",
                "concept_code": "pt",
                "domain": Domain.objects.get(domain_id="Language"),
            },
        )

        # Vocabularies
        vocabulary("OSM", "OpenStreetMap (OSM)", 32541)
        vocabulary("Provider", "OMOP Provider", 32573)
        vocabulary("Metadata", "OMOP Metadata", 32675)
        vocabulary("None", "OMOP Standardized Vocabularies", 44819096)
        vocabulary("Gender", "OMOP Gender", 44819108)
        vocabulary("Race", "Race and Ethnicity Code Set (USBC)", 44819109)
        vocabulary("Ethnicity", "OMOP Ethnicity", 44819134)
        vocabulary("Vocabulary", "OMOP Vocabulary", 44819232)
        vocabulary("BR_STATES", "Brazil States", 2000001)
        vocabulary("Measurement", "OMOP Measurement", 2000003)
        vocabulary("Observation", "OMOP Observation", 2000004)
        vocabulary("Condition", "OMOP Condition", 2000005)
        vocabulary("Drug", "OMOP Drug", 2000006)
        vocabulary("Substance", "OMOP Substance", 2000007)
        vocabulary("Observation Type", "OMOP Observation Type", 2000008)
        vocabulary("Relationship", "OMOP Relationship", 2000009)
        vocabulary("Domain", "OMOP Domain", 2000010)

        # Domains
        domain("Domain", "Domain", 1)
        domain("Gender", "Gender", 2)
        domain("Race", "Race", 3)
        domain("Ethnicity", "Ethnicity", 4)
        domain("Metadata", "Metadata", 7)
        domain("Provider", "Provider", 33)
        domain("Geography", "Geography", 32558)
        domain("Measurement", "Measurement", 2000013)
        domain("Observation", "Observation", 2000014)
        domain("Condition", "Condition", 2000015)
        domain("Drug", "Drug", 2000016)
        domain("Substance", "Substance", 2000017)
        domain("Type", "Type", 2000018)
        domain("Relationship", "Relationship", 2000019)
        domain("Domain", "Domain", 2000020)

        # Concept Classes
        concept_class("Vocabulary", "Vocabulary", 11111)
        concept_class("Domain", "Domain", 11112)
        concept_class("Gender", "Gender", 11113)
        concept_class("Race", "Race", 11114)
        concept_class("Ethnicity", "Ethnicity", 11115)
        concept_class("Provider", "Provider", 11116)
        concept_class("Physician Specialty", "Physician Specialty", 11117)
        concept_class("Brazil States", "Brazil States", 2000042)
        concept_class("Measurement", "Measurement", 2000043)
        concept_class("Observation", "Observation", 2000044)
        concept_class("Quality", "Quality", 2000045)
        concept_class("Frequency", "Frequency", 2000046)
        concept_class("Comorbidity", "Comorbidity", 2000047)
        concept_class("Medication", "Medication", 2000048)
        concept_class("Substance", "Substance", 2000049)
        concept_class("Type", "Type", 2000041)
        concept_class("Recurrence", "Recurrence", 2000050)
        concept_class("Relationship", "Relationship", 2000051)
        concept_class("Observation Type", "Observation Type", 2000052)
        concept_class("Metadata", "Metadata", 2000053)
        concept_class("Interest", "Interest", 2000011)
        concept_class("Trigger", "Trigger", 2000012)

        # Vocabularies concepts
        add_concept(
            32541,
            "OpenStreetMap (OSMF)",
            "Vocabulary",
            "OMOP generated",
            "Metadata",
            "Vocabulary",
            "OpenStreetMap (OSMF)",
        )
        add_concept(32573, "OMOP Provider", "Vocabulary", "OMOP generated", "Metadata", "Vocabulary", "Provedor OMOP")
        add_concept(32675, "OMOP Metadata", "Vocabulary", "OMOP generated", "Metadata", "Vocabulary", "Metadata OMOP")
        add_concept(
            44819096,
            "OMOP Standardized Vocabularies",
            "Vocabulary",
            "OMOP generated",
            "Metadata",
            "Vocabulary",
            "Vocabulários Padronizados OMOP",
        )
        add_concept(44819108, "OMOP Gender", "Vocabulary", "OMOP generated", "Metadata", "Vocabulary", "Gênero OMOP")
        add_concept(
            44819109,
            "Race and Ethnicity Code Set (USBC)",
            "Vocabulary",
            "OMOP generated",
            "Metadata",
            "Vocabulary",
            "Conjunto de Códigos de Raça e Etnia (USBC)",
        )
        add_concept(44819134, "OMOP Ethnicity", "Vocabulary", "OMOP generated", "Metadata", "Vocabulary", "Etnia OMOP")
        add_concept(
            44819232, "OMOP Vocabulary", "Vocabulary", "OMOP generated", "Metadata", "Vocabulary", "Vocabulário OMOP"
        )

        # Domains concepts
        add_concept(1, "Domain", "Domain", "OMOP generated", "Domain", "Metadata", "Domínio")
        add_concept(2, "Gender", "Domain", "OMOP generated", "Domain", "Metadata", "Gênero")
        add_concept(3, "Race", "Domain", "OMOP generated", "Domain", "Metadata", "Raça")
        add_concept(4, "Ethnicity", "Domain", "OMOP generated", "Domain", "Metadata", "Etnia")
        add_concept(7, "Metadata", "Domain", "OMOP generated", "Domain", "Metadata", "Metadados")
        add_concept(33, "Provider", "Domain", "OMOP generated", "Domain", "Metadata", "Provedor")
        add_concept(32558, "Geographical object", "Domain", "OMOP generated", "Domain", "Metadata", "Objeto Geográfico")

        # Gender
        add_concept(8507, "MALE", "Gender", "M", "Gender", "Gender", "Masculino")
        add_concept(8532, "FEMALE", "Gender", "F", "Gender", "Gender", "Feminino")
        add_concept(8551, "UNKNOWN", "Gender", "U", "Gender", "Gender", "Desconhecido")

        # Race
        add_concept(8527, "WHITE", "Race", "W", "Race", "Race", "Branco")
        add_concept(8516, "BLACK OR AFRICAN AMERICAN", "Race", "B", "Race", "Race", "Preto")
        add_concept(8657, "ASIAN", "Race", "A", "Race", "Race", "Asiático")

        # Specialities
        add_concept(32577, "Physician", "Physician Specialty", "OMOP4822444", "Provider", "Provider", "Médico")
        add_concept(32578, "Counselor", "Provider", "OMOP4822447", "Provider", "Provider", "Conselheiro")
        add_concept(32580, "Allied Health Professional", "Provider", "OMOP4822445", "Provider", "Provider", "ACS")
        add_concept(32581, "Nurse", "Provider", "OMOP4822446", "Provider", "Provider", "Enfermeiro")
        add_concept(
            33003, "Service Provider", "Provider", "OMOP5117445", "Provider", "Provider", "Prestador de Serviço"
        )
        add_concept(
            33005,
            "Psychiatry or Neurology",
            "Physician Specialty",
            "OMOP5117448",
            "Provider",
            "Provider",
            "Psiquiatria ou Neurologia",
        )

        # States
        add_concept(2000053, "SP", "Brazil States", "BR", "Geography", "BR_STATES", "SP")
        add_concept(2000054, "RJ", "Brazil States", "BR", "Geography", "BR_STATES", "RJ")
        add_concept(2000055, "MG", "Brazil States", "BR", "Geography", "BR_STATES", "MG")
        add_concept(2000056, "BA", "Brazil States", "BR", "Geography", "BR_STATES", "BA")
        add_concept(2000057, "PR", "Brazil States", "BR", "Geography", "BR_STATES", "PR")
        add_concept(2000058, "RS", "Brazil States", "BR", "Geography", "BR_STATES", "RS")
        add_concept(2000051, "GO", "Brazil States", "BR", "Geography", "BR_STATES", "GO")
        add_concept(2000053, "CE", "Brazil States", "BR", "Geography", "BR_STATES", "CE")
        add_concept(2000054, "AM", "Brazil States", "BR", "Geography", "BR_STATES", "AM")

        dummy_person("Dummy", year_of_birth=1990, gender_concept=8507, race_concept=8527)
        dummy_person("Gummy", year_of_birth=1999, gender_concept=8532, race_concept=8657)
        dummy_person("Sunny", year_of_birth=1981, gender_concept=8551, race_concept=8516)

        # Measurements
        add_concept(3025315, "Body Weight", "Measurement", "BW", "Measurement", "Measurement", "Peso corporal")
        add_concept(3023540, "Body Height", "Measurement", "BH", "Measurement", "Measurement", "Altura corporal")

        # Concept Types
        add_concept(9000020, "Sleep Quality", "Type", "SLEEPQ", "Observation", "Observation", "Qualidade do sono")
        add_concept(
            9000025, "Exercise Frequency", "Type", "EXERFREQ", "Observation", "Observation", "Frequência de Exercício"
        )
        add_concept(9000026, "Eating Habits", "Type", "EATHAB", "Observation", "Observation", "Hábitos Alimentares")
        add_concept(9000027, "Comorbity", "Type", "COMORB", "Condition", "Condition", "Comorbidade")
        add_concept(9000028, "Medication", "Type", "MED", "Drug", "Drug", "Medicação")
        add_concept(9000029, "Substance Use", "Type", "SUBUSE", "Substance", "Substance", "Uso de Substâncias")

        # Quality
        add_concept(9000001, "Good", "Quality", "GOOD", "Observation", "Observation", "Bom")
        add_concept(9000002, "Bad", "Quality", "BAD", "Observation", "Observation", "Ruim")
        add_concept(9000003, "Ok", "Quality", "OK", "Observation", "Observation", "Razoável")

        # Frequency
        add_concept(9000010, "Regularly", "Frequency", "REG", "Observation", "Observation", "Regularmente")
        add_concept(9000011, "Occasionally", "Frequency", "OCC", "Observation", "Observation", "Ocasionalmente")
        add_concept(9000012, "Rarely", "Frequency", "RARE", "Observation", "Observation", "Raramente")
        add_concept(9000013, "Never", "Frequency", "NEVER", "Observation", "Observation", "Nunca")

        # Comorbidities

        # Medications
        add_concept(9000040, "Fluoxetine", "Medication", "FLX", "Drug", "Drug", "Fluoxetina")
        add_concept(9000041, "Ibuprofen", "Medication", "IBU", "Drug", "Drug", "Ibuprofeno")

        # SubstanceUse
        add_concept(9000050, "Alcohol", "Substance", "ALC", "Substance", "Substance", "Álcool")
        add_concept(9000051, "Tobacco", "Substance", "TOB", "Substance", "Substance", "Tabaco")

        # Observation Type
        add_concept(38000280, "Self Reported", "Observation", "SR", "Observation", "Observation", "Auto-relatado")

        # Recurrence
        add_concept(9000100, "Daily", "Recurrence", "DAILY", "Observation", "Observation", "Diariamente")
        add_concept(9000101, "Weekly", "Recurrence", "WEEKLY", "Observation", "Observation", "Semanalmente")
        add_concept(9000102, "Monthly", "Recurrence", "MONTHLY", "Observation", "Observation", "Mensalmente")
        add_concept(9000103, "Yearly", "Recurrence", "YEARLY", "Observation", "Observation", "Anualmente")
        add_concept(9000104, "Hourly", "Recurrence", "HOURLY", "Observation", "Observation", "A cada hora")
        add_concept(9000105, "Once", "Recurrence", "ONCE", "Observation", "Observation", "Apenas uma vez")

        # Relationship
        add_concept(
            9200010,
            "Provider Link Code",
            "Observation",
            "PROVIDER_LINK_CODE",
            "Observation",
            "Observation",
            "Código de vínculo entre pessoa e profissional",
        )
        add_concept(
            9200011,
            "Clinician Generated",
            "Observation Type",
            "CLINICIAN_GENERATED",
            "Type",
            "Observation Type",
            "Gerado pelo profissional de saúde",
        )
        add_concept(
            9200001,
            "Person to Provider",
            "Relationship",
            "PERSON_PROVIDER",
            "Relationship",
            "Relationship",
            "Pessoa associada ao profissional de saúde",
        )

        add_concept(
            9201, "Provider", "Metadata", "PROVIDER", "Domain", "Domain", "Profissional de saúde (domínio provider)"
        )
        add_concept(9202, "Person", "Metadata", "PERSON", "Domain", "Domain", "Indivíduo (domínio pessoa)")

        # Tipos principais
        vocabulary("Value", "Value", 999900)
        domain("Diary", "Diary", 999901)
        domain("Value", "Value", 999902)
        concept_class("Diary", "Diary", 999903)

        add_concept(999001, "Diary Entry", "Diary", "diary_entry", "Observation", "Observation", "Entrada de diário")
        add_concept(999002, "Diary Text", "Diary", "diary_text", "Observation", "Observation", "Texto livre do diário")
        add_concept(999003, "Diary Scope", "Diary", "diary_scope", "Observation", "Observation", "Alcance do diário")
        add_concept(
            999004, "Diary Entry Type", "Diary", "diary_entry_type", "Observation", "Observation", "Tipo de entrada"
        )

        # Help
        add_concept(2000100, "Help", None, "HELP", None, None, "Ajuda")
        add_concept(2000101, "Active", None, "ACTIVE", None, None, "Ativo")

        # Area of Interest
        add_concept(2000200, "Interest Area", "Interest", "INTEREST_AREA", None, None, "Área de Interesse")
        add_concept(2000201, "Custom Interest", "Interest", "CUSTOM_INTEREST", None, None, "Interesse Personalizado")
        add_concept(2000202, "Hypertension", "Interest", "HTN", None, None, "Hipertensão")
        add_concept(2000203, "Diabetes", "Interest", "DIABETES", None, None, "Diabetes")
        add_concept(2000204, "Sleep", "Interest", "Sleep", None, None, "Sono")

        # AOI Triggers
        add_concept(2000300, "Trigger", "Trigger", "TRIGGER", None, None, "Gatilho")
        add_concept(2000301, "Custom Trigger", "Trigger", "CUSTOM_TRIGGER", None, None, "Gatilho Personalizado")
        add_concept(2000302, "Diet", "Trigger", "DIET", None, None, "Alimentação")
        add_concept(2000303, "Physical Activity", "Trigger", "PHYSICAL_ACTIVITY", None, None, "Atividade Física")
        add_concept(2000304, "Sleep", "Trigger", "SLEEP", None, None, "Sono")
        add_concept(2000305, "Stress", "Trigger", "STRESS", None, None, "Estresse")
        add_concept(2000306, "Weight", "Trigger", "WEIGHT", None, None, "Peso")
        add_concept(2000307, "Medication", "Trigger", "MEDICATION", None, None, "Medicação")
        add_concept(2000308, "Environment", "Trigger", "ENVIRONMENT", None, None, "Ambiente")

        # Fact Relationships
        add_concept(2000400, "AOI_Trigger", None, "AOI_TRIGGER", None, None, "Gatilho de Área de Interesse")

        # Link AOI to Trigger

        relate_concepts(2000202, [2000302, 2000303, 2000304], "AOI_Trigger")  # Hypertension  # Diet, PA, Sleep
        relate_concepts(2000203, [2000302, 2000306, 2000307], "AOI_Trigger")  # Diabetes  # Diet, Weight, Medication
        relate_concepts(2000204, [2000305, 2000308, 2000307], "AOI_Trigger")  # Sleep  # Stress, Environment, Medication

        User = get_user_model()
        user, _ = User.objects.get_or_create(
            email="mock-provider@email.com",
            defaults={"username": "mockprovider", "first_name": "Dr. Mock", "last_name": "Provider"},
        )

        # Provider.objects.get_or_create(user=user)
        self.stdout.write(self.style.SUCCESS("✔️  Conceitos populados com sucesso."))

        # Sintomas predefinidos
        concept_class("Wellness", "Wellness", 999100)

        # Tipos de valores
        concept_class("Value Type", "Value Type", 999200)

        add_concept(999201, "Yes/No", "Value Type", "yes_no", "Value", "Value", "Sim/Não")
        add_concept(999202, "Free Text", "Value Type", "free_text", "Value", "Value", "Texto livre")
        add_concept(999203, "Scale", "Value Type", "scale", "Value", "Value", "Escala")
        add_concept(999204, "Hours", "Value Type", "hours", "Value", "Value", "Horas")
        add_concept(999205, "Times", "Value Type", "times", "Value", "Value", "Vezes")

        concept_class("Yes/No", "Yes/No", 999201)
        concept_class("Free Text", "Free Text", 999202)
        concept_class("Scale", "Scale", 999203)
        concept_class("Hours", "Hours", 999204)
        concept_class("Times", "Times", 999205)

        # Valores possíveis
        add_concept(999501, "Yes", "Yes/No", "value_yes", "Value", "Value", "Sim")
        add_concept(999502, "No", "Yes/No", "value_no", "Value", "Value", "Não")

        WELLBEING = [
            ("sleep", "Qualidade do sono", "scale"),
            ("medicine", "Tomar medicamentos", "yesno"),
            ("medication_effects", "Efeitos da medicação", "scale"),
            ("side_effects", "Efeitos colaterais da medicação", "yesno"),
            ("physical_symptoms", "Sintomas físicos", "yesno"),
            ("thoughts", "Pensamentos", "scale"),
            ("triggers", "Exposição a gatilhos", "times"),
            ("work", "Trabalho", "scale"),
            ("chores", "Tarefas domésticas", "scale"),
            ("food", "Alimentação", "scale"),
            ("hobbies", "Hobbies", "scale"),
            ("exercise", "Exercício físico", "hours"),
            ("water", "Consumo de água", "scale"),
            ("social", "Socialização", "scale"),
            ("self_harm", "Auto mutilação", "times"),
            ("intrusive_thoughts", "Pensamentos intrusivos", "scale"),
            ("suicidal_ideation", "Ideação suicida", "yesno"),
            ("dissociation", "Disassociação", "scale"),
            ("paranoia", "Paranóia", "scale"),
        ]

        VALUE_TYPE_CODE_TO_ID = {
            "scale": 999203,
            "yesno": 999201,
            "freetext": 999202,
            "times": 999205,
            "hours": 999204,
        }

        for i, (code, pt_name, value_type_code) in enumerate(WELLBEING):
            concept_id = 999300 + i
            add_concept(concept_id, pt_name, "Wellness", code, "Observation", "Observation", pt_name)

            # Cria a relação has_value_type
            value_type_concept_id = VALUE_TYPE_CODE_TO_ID[value_type_code]
            ConceptRelationship.objects.update_or_create(
                concept_1_id=concept_id, concept_2_id=value_type_concept_id, relationship_id="has_value_type"
            )
