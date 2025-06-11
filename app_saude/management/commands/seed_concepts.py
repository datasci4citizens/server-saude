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
        add_concept(999005, "Diary interest", "Diary", "diary_interest", None, None, "Alcance do diário")

        # Help
        add_concept(2000100, "Help", None, "HELP", None, None, "Ajuda")
        add_concept(2000101, "Active", None, "ACTIVE", None, None, "Ativo")

        # Area of Interest
        add_concept(2000000200, "Interest Area", "Interest", "INTEREST_AREA", None, None, "Área de Interesse")
        add_concept(2000000201, "Custom Interest", "Interest", "CUSTOM_INTEREST", None, None, "Interesse Personalizado")
        add_concept(2000000202, "Hypertension", "Interest", "HTN", None, None, "Hipertensão")
        add_concept(2000000203, "Diabetes", "Interest", "DIABETES", None, None, "Diabetes")
        add_concept(2000000204, "Sleep", "Interest", "SLEEP", None, None, "Sono")
        add_concept(2000000205, "My Clinical Exams", "Interest", "CLINICAL_EXAMS", None, None, "Meus exames clínicos")
        add_concept(2000000206, "Pains I'm Feeling", "Interest", "PAINS", None, None, "Dores que estou sentindo")
        add_concept(
            2000000207, "Mental Health Issues", "Interest", "MENTAL_HEALTH", None, None, "Questões de saúde mental"
        )
        add_concept(2000000208, "Medication", "Interest", "MEDICATION", None, None, "Medicação")
        add_concept(2000000209, "Nutrition", "Interest", "NUTRITION", None, None, "Alimentação")
        add_concept(
            2000000210,
            "Alcohol or Substance Use",
            "Interest",
            "SUBSTANCE_USE",
            None,
            None,
            "Uso de álcool ou outras substâncias",
        )
        add_concept(2000000211, "Mood and Emotional Health", "Interest", "MOOD", None, None, "Humor e saúde emocional")
        add_concept(
            2000000212,
            "Support Network and Bonds",
            "Interest",
            "SUPPORT_NETWORK",
            None,
            None,
            "Rede de apoio e vínculos",
        )
        add_concept(
            2000000213, "Daily Activities", "Interest", "DAILY_ACTIVITIES", None, None, "Atividades do dia a dia"
        )
        add_concept(
            2000000214, "Safety and Social Protection", "Interest", "SAFETY", None, None, "Segurança e proteção social"
        )

        # AOI Triggers
        add_concept(2000000300, "Trigger", "Trigger", "TRIGGER", None, None, "Gatilho")
        add_concept(2000000301, "Custom Trigger", "Trigger", "CUSTOM_TRIGGER", None, None, "Gatilho Personalizado")

        # Triggers for AOI questions
        add_concept(
            2000000403,
            "Did you measure your blood glucose today?",
            "Trigger",
            "BLOOD_GLUCOSE_MEASURED",
            None,
            None,
            "Você mediu sua glicemia hoje?",
        )
        add_concept(
            2000000404,
            "What was the blood glucose value?",
            "Trigger",
            "BLOOD_GLUCOSE_VALUE",
            None,
            None,
            "Qual foi o valor?",
        )
        add_concept(
            2000000405,
            "Blood glucose time",
            "Trigger",
            "BLOOD_GLUCOSE_TIME",
            None,
            None,
            "Em que horário mediu sua glicemia?",
        )
        add_concept(
            2000000406,
            "Hypo/hyperglycemia symptoms",
            "Trigger",
            "HYPO_HYPERGLYCEMIA_SYMPTOMS",
            None,
            None,
            "Teve sintomas de hipo ou hiperglicemia?",
        )
        add_concept(
            2000000407,
            "Share blood glucose",
            "Trigger",
            "SHARE_BLOOD_GLUCOSE",
            None,
            None,
            "Gostaria de compartilhar esta informação com profissionais do CAPS ou da UBS?",
        )

        add_concept(
            2000000408,
            "Did you measure your blood pressure today?",
            "Trigger",
            "BLOOD_PRESSURE_MEASURED",
            None,
            None,
            "Você mediu sua pressão hoje?",
        )
        add_concept(
            2000000409,
            "What was the blood pressure value?",
            "Trigger",
            "BLOOD_PRESSURE_VALUE",
            None,
            None,
            "Qual foi o valor?",
        )
        add_concept(
            2000000410,
            "Blood pressure time",
            "Trigger",
            "BLOOD_PRESSURE_TIME",
            None,
            None,
            "Em que horário mediu sua pressão?",
        )
        add_concept(
            2000000411,
            "Blood pressure symptoms",
            "Trigger",
            "BLOOD_PRESSURE_SYMPTOMS",
            None,
            None,
            "Teve sintomas como dor de cabeça, tontura ou mal-estar?",
        )
        add_concept(
            2000000412,
            "Share blood pressure",
            "Trigger",
            "SHARE_BLOOD_PRESSURE",
            None,
            None,
            "Gostaria de compartilhar esta informação com profissionais do CAPS ou da UBS?",
        )

        add_concept(
            2000000413,
            "Recent clinical exam",
            "Trigger",
            "RECENT_CLINICAL_EXAM",
            None,
            None,
            "Você realizou algum exame clínico recentemente?",
        )
        add_concept(
            2000000414,
            "Which exam was performed?",
            "Trigger",
            "EXAM_PERFORMED",
            None,
            None,
            "Qual exame foi realizado?",
        )
        add_concept(
            2000000415,
            "Received exam result?",
            "Trigger",
            "RECEIVED_EXAM_RESULT",
            None,
            None,
            "Recebeu o resultado?",
        )
        add_concept(
            2000000416,
            "Discuss exam",
            "Trigger",
            "DISCUSS_EXAM",
            None,
            None,
            "Gostaria de discutir esse exame com alguém do CAPS ou da UBS?",
        )

        add_concept(
            2000000417,
            "Are you feeling pain today?",
            "Trigger",
            "PAIN_TODAY",
            None,
            None,
            "Está sentindo alguma dor hoje?",
        )
        add_concept(2000000418, "Pain location", "Trigger", "PAIN_LOCATION", None, None, "Onde é a dor?")
        add_concept(
            2000000419,
            "Pain intensity",
            "Trigger",
            "PAIN_INTENSITY",
            None,
            None,
            "De 0 a 10, qual a intensidade da dor?",
        )
        add_concept(
            2000000420, "Since when pain", "Trigger", "PAIN_SINCE_WHEN", None, None, "Desde quando está com essa dor?"
        )
        add_concept(
            2000000421,
            "Report pain to professional",
            "Trigger",
            "REPORT_PAIN",
            None,
            None,
            "Gostaria de relatar isso para seu profissional de saúde?",
        )

        add_concept(
            2000000422,
            "How are you feeling now?",
            "Trigger",
            "FEELING_NOW",
            None,
            None,
            "Como você está se sentindo agora?",
        )
        add_concept(
            2000000423,
            "Moments of anxiety/sadness/irritation",
            "Trigger",
            "MOMENTS_ANXIETY_SADNESS_IRRITATION",
            None,
            None,
            "Teve momentos de ansiedade, tristeza ou irritação hoje?",
        )
        add_concept(
            2000000424,
            "Concentration on activities",
            "Trigger",
            "CONCENTRATION_ACTIVITIES",
            None,
            None,
            "Conseguiu se concentrar nas suas atividades?",
        )
        add_concept(
            2000000425,
            "Share feelings",
            "Trigger",
            "SHARE_FEELINGS",
            None,
            None,
            "Gostaria de compartilhar como está se sentindo com sua equipe de cuidado?",
        )

        add_concept(
            2000000426,
            "Did you take medication today?",
            "Trigger",
            "TOOK_MEDICATION",
            None,
            None,
            "Você tomou sua medicação hoje?",
        )
        add_concept(2000000427, "Medication time", "Trigger", "MEDICATION_TIME", None, None, "Em que horário tomou?")
        add_concept(2000000428, "Side effect", "Trigger", "SIDE_EFFECT", None, None, "Teve algum efeito colateral?")
        add_concept(
            2000000429,
            "Communicate medication",
            "Trigger",
            "COMMUNICATE_MEDICATION",
            None,
            None,
            "Gostaria de comunicar isso ao CAPS ou à UBS?",
        )

        add_concept(
            2000000430,
            "How was your eating today?",
            "Trigger",
            "EATING_TODAY",
            None,
            None,
            "Como foi sua alimentação hoje?",
        )
        add_concept(
            2000000431,
            "Did you have main meals?",
            "Trigger",
            "MAIN_MEALS",
            None,
            None,
            "Conseguiu fazer suas refeições principais?",
        )
        add_concept(
            2000000432,
            "Nausea/vomiting/loss of appetite",
            "Trigger",
            "NAUSEA_VOMITING_LOSS_APPETITE",
            None,
            None,
            "Teve algum enjoo, vômito ou falta de apetite?",
        )
        add_concept(
            2000000433, "Did you drink water today?", "Trigger", "DRANK_WATER", None, None, "Bebeu bastante água hoje?"
        )

        add_concept(
            2000000434,
            "Sleep/wake time",
            "Trigger",
            "SLEEP_WAKE_TIME",
            None,
            None,
            "Que horas você dormiu e acordou?",
        )
        add_concept(2000000435, "Did you sleep well?", "Trigger", "SLEPT_WELL", None, None, "Dormiu bem esta noite?")
        add_concept(
            2000000436,
            "Did you wake up during the night?",
            "Trigger",
            "WOKE_UP_NIGHT",
            None,
            None,
            "Acordou durante a noite?",
        )
        add_concept(2000000437, "Hours of sleep", "Trigger", "HOURS_SLEEP", None, None, "Quantas horas dormiu?")

        add_concept(
            2000000438,
            "Did you use any substance today?",
            "Trigger",
            "USED_SUBSTANCE",
            None,
            None,
            "Usou alguma substância hoje (álcool, cigarro, outras)?",
        )
        add_concept(
            2000000439,
            "Substance use time",
            "Trigger",
            "SUBSTANCE_USE_TIME",
            None,
            None,
            "Que horas foi o uso?",
        )
        add_concept(
            2000000440,
            "Desire to use substance",
            "Trigger",
            "DESIRE_USE_SUBSTANCE",
            None,
            None,
            "Sentiu vontade de usar e conseguiu evitar?",
        )
        add_concept(
            2000000441,
            "Support to deal with use",
            "Trigger",
            "SUPPORT_DEAL_USE",
            None,
            None,
            "Gostaria de apoio para lidar com isso?",
        )

        add_concept(
            2000000442,
            "How are you feeling at this moment?",
            "Trigger",
            "FEELING_THIS_MOMENT",
            None,
            None,
            "Como você está se sentindo neste momento?",
        )
        add_concept(
            2000000443,
            "Did you feel alone today?",
            "Trigger",
            "FELT_ALONE_TODAY",
            None,
            None,
            "Se sentiu sozinho(a) hoje?",
        )
        add_concept(
            2000000444,
            "Difficult to control thoughts",
            "Trigger",
            "DIFFICULT_CONTROL_THOUGHTS",
            None,
            None,
            "Teve pensamentos difíceis de controlar?",
        )
        add_concept(
            2000000445,
            "Talk about feelings",
            "Trigger",
            "TALK_ABOUT_FEELINGS",
            None,
            None,
            "Gostaria de conversar com alguém sobre isso?",
        )

        add_concept(
            2000000446,
            "Did you talk to someone close today?",
            "Trigger",
            "TALKED_TO_CLOSE_PERSON",
            None,
            None,
            "Conversou com alguém próximo hoje?",
        )
        add_concept(
            2000000447,
            "Did you participate in a group activity?",
            "Trigger",
            "PARTICIPATED_GROUP_ACTIVITY",
            None,
            None,
            "Participou de alguma atividade em grupo?",
        )
        add_concept(
            2000000448,
            "Desire to meet someone?",
            "Trigger",
            "DESIRE_MEET_SOMEONE",
            None,
            None,
            "Teve vontade de encontrar alguém?",
        )
        add_concept(
            2000000449,
            "Participate in activities with others",
            "Trigger",
            "PARTICIPATE_ACTIVITIES_OTHERS",
            None,
            None,
            "Gostaria de participar de atividades com outras pessoas?",
        )

        add_concept(
            2000000450,
            "Did you bathe and eat today?",
            "Trigger",
            "BATHED_AND_ATE_TODAY",
            None,
            None,
            "Conseguiu tomar banho e se alimentar hoje?",
        )
        add_concept(
            2000000451,
            "Did you do any activity at home?",
            "Trigger",
            "DID_ACTIVITY_AT_HOME",
            None,
            None,
            "Realizou alguma atividade em casa?",
        )
        add_concept(
            2000000452,
            "Did you leave the house today?",
            "Trigger",
            "LEFT_HOUSE_TODAY",
            None,
            None,
            "Saiu de casa hoje?",
        )
        add_concept(
            2000000453,
            "Difficulty in daily activity?",
            "Trigger",
            "DIFFICULTY_DAILY_ACTIVITY",
            None,
            None,
            "Teve dificuldade com alguma atividade cotidiana?",
        )

        add_concept(
            2000000454,
            "Did you feel safe where you slept?",
            "Trigger",
            "FELT_SAFE_WHERE_SLEPT",
            None,
            None,
            "Se sentiu seguro(a) no lugar onde dormiu?",
        )
        add_concept(
            2000000455,
            "Were you mistreated or threatened today?",
            "Trigger",
            "MISTREATED_THREATENED_TODAY",
            None,
            None,
            "Alguém te tratou mal ou te ameaçou hoje?",
        )
        add_concept(
            2000000456,
            "Was anything essential missing?",
            "Trigger",
            "ESSENTIAL_MISSING",
            None,
            None,
            "Faltou algo essencial (comida, lugar para dormir)?",
        )
        add_concept(
            2000000457,
            "Contact with CHW or professional?",
            "Trigger",
            "CONTACT_CHW_PROFESSIONAL",
            None,
            None,
            "Gostaria que um ACS ou profissional de saúde entrasse em contato com você?",
        )

        # Fact Relationships
        add_concept(2000000400, "AOI_Trigger", None, "AOI_TRIGGER", None, None, "Gatilho de Área de Interesse")
        add_concept(2000000401, "AOI_Diary", None, "AOI_DIARY", None, None, "Diario area de interesse")
        add_concept(2000000402, "Text_Diary", None, "TEXT_DIARY", None, None, "Diario area de interesse")

        # Link AOI to Trigger

        INTEREST_TO_TRIGGERS = {
            2000000202: [2000000408, 2000000409, 2000000410, 2000000411, 2000000412],  # Hypertension
            2000000203: [2000000403, 2000000404, 2000000405, 2000000406, 2000000407],  # Diabetes
            2000000204: [2000000434, 2000000435, 2000000436, 2000000437],  # Sleep
            2000000205: [2000000413, 2000000414, 2000000415, 2000000416],  # My Clinical Exams
            2000000206: [2000000417, 2000000418, 2000000419, 2000000420, 2000000421],  # Pains I'm Feeling
            2000000207: [2000000422, 2000000423, 2000000424, 2000000425],  # Mental Health Issues
            2000000208: [2000000426, 2000000427, 2000000428, 2000000429],  # Medication
            2000000209: [2000000430, 2000000431, 2000000432, 2000000433],  # Nutrition
            2000000210: [2000000438, 2000000439, 2000000440, 2000000441],  # Alcohol or Substance Use
            2000000211: [2000000442, 2000000443, 2000000444, 2000000445],  # Mood and Emotional Health
            2000000212: [2000000446, 2000000447, 2000000448, 2000000449],  # Support Network and Bonds
            2000000213: [2000000450, 2000000451, 2000000452, 2000000453],  # Daily Activities
            2000000214: [2000000454, 2000000455, 2000000456, 2000000457],  # Safety and Social Protection
        }

        for interest_id, trigger_ids in INTEREST_TO_TRIGGERS.items():
            relate_concepts(interest_id, trigger_ids, "AOI_Trigger")

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
