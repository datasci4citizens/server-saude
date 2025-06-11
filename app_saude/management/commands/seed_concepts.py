from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from app_saude.models import *
from django.utils import timezone

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
        add_concept(999005, "Diary interest", "Diary", "diary_interest", None, None, "Alcance do diário")

        # Help
        add_concept(2000100000, "Help", None, "HELP", None, None, "Ajuda")
        add_concept(2000101000, "Active", None, "ACTIVE", None, None, "Ativo")

        # Area of Interest
        add_concept(2000000200, "Interest Area", "Interest", "INTEREST_AREA", None, None, "Área de Interesse")
        add_concept(2000000201, "Custom Interest", "Interest", "CUSTOM_INTEREST", None, None, "Interesse Personalizado")
        add_concept(2000000202, "Patient Interest", "Interest", "PATIENT_INTEREST", None, None, "Interesse do Paciente")
        add_concept(2000000203, "Hypertension", "Interest", "HTN", None, None, "Hipertensão")
        add_concept(2000000204, "Diabetes", "Interest", "DIABETES", None, None, "Diabetes")
        add_concept(2000000205, "Sleep", "Interest", "Sleep", None, None, "Sono")
        add_concept(
            2000000206, "Clinical Examinations", "Interest", "CLINICAL_EXAMS", None, None, "Meus Exames Clínicos"
        )
        add_concept(2000000207, "Pain", "Interest", "PAIN", None, None, "Dores que estou sentindo")
        add_concept(2000000208, "Mental Health", "Interest", "MENTAL_HEALTH", None, None, "Minha Saúde Mental")
        add_concept(2000000209, "Medication", "Interest", "MEDICATION", None, None, "Medicação")
        add_concept(2000000210, "Food", "Interest", "FOOD", None, None, "Alimentação")
        add_concept(
            2000000211, "Substances", "Interest", "SUBSTANCES", None, None, "Uso de álcool ou outras substâncias"
        )
        add_concept(
            2000000212, "Emotional Health", "Interest", "EMOTIONAL_HEALTH", None, None, "Humor e saúde emocional"
        )
        add_concept(
            2000000213, "Daily Activities", "Interest", "DAILY_ACTIVITIES", None, None, "Atividades do dia a dia"
        )
        add_concept(
            2000000214, "Social Security", "Interest", "SOCIAL_SECURITY", None, None, "Segurança e proteção social"
        )
        add_concept(
            2000000215, "Support Network", "Interest", "SUPPORT_NETWORK", None, None, "Rede de apoio e vínculos"
        )

        # Create an Observation for each Interest concept
        for concept_id in range(2000000202, 2000000215):
            concept = Concept.objects.get(concept_id=concept_id)
            pt_synonym = ConceptSynonym.objects.filter(concept=concept, language_concept_id=4180186).first()
            source_value = pt_synonym.concept_synonym_name if pt_synonym else concept.concept_name
            Observation.objects.update_or_create(
                observation_concept_id=concept_id,
                defaults={
                    "observation_date": timezone.now(),
                    "observation_source_value": source_value,
                },
            )

        # AOI Triggers
        add_concept(2000000300, "Trigger", "Trigger", "TRIGGER", None, None, "Gatilho")
        add_concept(2000000301, "Custom Trigger", "Trigger", "CUSTOM_TRIGGER", None, None, "Gatilho Personalizado")
        # AOI Questions as Observations

        AOI_Triggers = [
            # Hypertension
            (2000000202, "Você mediu sua pressão hoje?"),
            (2000000202, "Qual foi o valor?"),
            (2000000202, "Em que horário mediu sua pressão?"),
            (2000000202, "Teve sintomas como dor de cabeça, tontura ou mal-estar?"),
            (2000000202, "Gostaria de compartilhar esta informação com profissionais do CAPS ou da UBS?"),
            # Diabetes
            (2000000203, "Você mediu sua glicemia hoje?"),
            (2000000203, "Qual foi o valor?"),
            (2000000203, "Em que horário mediu sua glicemia?"),
            (2000000203, "Teve sintomas de hipo ou hiperglicemia?"),
            (2000000203, "Gostaria de compartilhar esta informação com profissionais do CAPS ou da UBS?"),
            # Sleep
            (2000000204, "Que horas você dormiu e acordou?"),
            (2000000204, "Dormiu bem esta noite?"),
            (2000000204, "Acordou durante a noite?"),
            (2000000204, "Quantas horas dormiu?"),
            # My clinical exams
            (2000000205, "Você realizou algum exame clínico recentemente?"),
            (2000000205, "Qual exame foi realizado?"),
            (2000000205, "Recebeu o resultado?"),
            (2000000205, "Gostaria de discutir esse exame com alguém do CAPS ou da UBS?"),
            # Pains I am feeling
            (2000000206, "Está sentindo alguma dor hoje?"),
            (2000000206, "Onde é a dor?"),
            (2000000206, "De 0 a 10, qual a intensidade da dor?"),
            (2000000206, "Desde quando está com essa dor?"),
            (2000000206, "Gostaria de relatar isso para seu profissional de saúde?"),
            # Mental health questions
            (2000000207, "Como você está se sentindo agora?"),
            (2000000207, "Teve momentos de ansiedade, tristeza ou irritação hoje?"),
            (2000000207, "Conseguiu se concentrar nas suas atividades?"),
            (2000000207, "Gostaria de compartilhar como está se sentindo com sua equipe de cuidado?"),
            # Medication
            (2000000208, "Você tomou sua medicação hoje?"),
            (2000000208, "Em que horário tomou?"),
            (2000000208, "Teve algum efeito colateral?"),
            (2000000208, "Gostaria de comunicar isso ao CAPS ou à UBS?"),
            # Food
            (2000000209, "Como foi sua alimentação hoje?"),
            (2000000209, "Conseguiu fazer suas refeições principais?"),
            (2000000209, "Teve algum enjoo, vômito ou falta de apetite?"),
            (2000000209, "Bebeu bastante água hoje?"),
            # Use of alcohol or other substances
            (2000000210, "Usou alguma substância hoje (álcool, cigarro, outras)?"),
            (2000000210, "Que horas foi o uso?"),
            (2000000210, "Sentiu vontade de usar e conseguiu evitar?"),
            (2000000210, "Gostaria de apoio para lidar com isso?"),
            # Mood and emotional health
            (2000000211, "Como você está se sentindo neste momento?"),
            (2000000211, "Se sentiu sozinho(a) hoje?"),
            (2000000211, "Teve pensamentos difíceis de controlar?"),
            (2000000211, "Gostaria de conversar com alguém sobre isso?"),
            # Daily activities
            (2000000212, "Conseguiu tomar banho e se alimentar hoje?"),
            (2000000212, "Realizou alguma atividade em casa?"),
            (2000000212, "Saiu de casa hoje?"),
            (2000000212, "Teve dificuldade com alguma atividade cotidiana?"),
            # Safety and social protection
            (2000000213, "Se sentiu seguro(a) no lugar onde dormiu?"),
            (2000000213, "Alguém te tratou mal ou te ameaçou hoje?"),
            (2000000213, "Faltou algo essencial (comida, lugar para dormir)?"),
            (2000000213, "Gostaria que um ACS ou profissional de saúde entrasse em contato com você?"),
            # Support network and bonds
            (2000000214, "Conversou com alguém próximo hoje?"),
            (2000000214, "Participou de alguma atividade em grupo?"),
            (2000000214, "Teve vontade de encontrar alguém?"),
            (2000000214, "Gostaria de participar de atividades com outras pessoas?"),
        ]

        # Fact Relationships
        add_concept(2000000400, "AOI_Trigger", None, "AOI_TRIGGER", None, None, "Gatilho de Área de Interesse")
        add_concept(2000000401, "AOI_Diary", None, "AOI_DIARY", None, None, "Diario area de interesse")
        add_concept(2000000402, "Text_Diary", None, "TEXT_DIARY", None, None, "Diario area de interesse")

        for trigger in AOI_Triggers:
            obs, created = Observation.objects.update_or_create(
                observation_source_value=trigger[1],
                observation_concept_id=2000000200,
                defaults={"observation_date": timezone.now()},
            )

            FactRelationship.objects.update_or_create(
                fact_id_1=Observation.objects.get(observation_concept_id=trigger[0]).observation_id,
                domain_concept_1_id=2000000200,  # Interest Area
                fact_id_2=obs.observation_id,
                domain_concept_2_id=2000000300,  # Trigger
                relationship_concept_id=2000000400,  # AOI_TRIGGER
            )

        # # Link AOI to Trigger

        # relate_concepts(
        #     2000000202, [2000000302, 2000000303, 2000000304], "AOI_Trigger"
        # )  # Hypertension  # Diet, PA, Sleep
        # relate_concepts(
        #     2000000203, [2000000302, 2000000306, 2000000307], "AOI_Trigger"
        # )  # Diabetes  # Diet, Weight, Medication
        # relate_concepts(
        #     2000000204, [2000000305, 2000000308, 2000000307], "AOI_Trigger"
        # )  # Sleep  # Stress, Environment, Medication

        User = get_user_model()
        user, _ = User.objects.get_or_create(
            email="mock-provider@email.com",
            defaults={"username": "mockprovider", "first_name": "Dr. Mock", "last_name": "Provider"},
        )

        Provider.objects.get_or_create(user=user, defaults={"professional_registration": "1111111"})

        provider, _ = Provider.objects.get_or_create(user=user)

        user, _ = User.objects.get_or_create(
            email="mock-person@email.com",
            defaults={"username": "mockperson", "first_name": "Mock", "last_name": "Person"},
        )

        person, _ = Person.objects.get_or_create(user=user)

        FactRelationship.objects.get_or_create(
            fact_id_1=person.person_id,
            domain_concept_1_id=9202,  # Person
            fact_id_2=provider.provider_id,
            domain_concept_2_id=9201,  # Provider
            relationship_concept_id=9200001,
        )

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

        self.stdout.write(self.style.SUCCESS("✔️  Conceitos populados com sucesso."))
