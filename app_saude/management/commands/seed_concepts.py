from django.core.management.base import BaseCommand

from app_saude.models import *

# app_saude/management/commands/seed_concepts.py


class Command(BaseCommand):
    help = "Popula os principais conceitos OMOP customizados e traduzidos"

    def handle(self, *args, **kwargs):
        def domain(id, name, concept_id):
            return Domain.objects.get_or_create(
                domain_id=id, 
                defaults={"domain_name": name,
                          "domain_concept": Concept.objects.get_or_create(concept_id=concept_id)[0]

                })
        def vocabulary(id, name, concept_id):
            return Vocabulary.objects.get_or_create(
                vocabulary_id=id, 
                defaults={"vocabulary_name": name, 
                          "vocabulary_concept": Concept.objects.get_or_create(concept_id=concept_id)[0]
                })

        def add_concept(cid, name, class_id, code, domain_id, vocabulary_id, pt_name=None):
            concept, _ = Concept.objects.update_or_create(
                concept_id=cid,
                defaults={
                    "concept_name": name,
                    "concept_class_id": class_id,
                    "concept_code": code,
                    "domain": Domain.objects.get(domain_id=domain_id),
                    "vocabulary_id": Vocabulary.objects.get(vocabulary_id=vocabulary_id),
                },
            )
            if pt_name:
                ConceptSynonym.objects.update_or_create(
                    concept=concept, concept_synonym_name=pt_name, language_concept_id=4180186  # pt
                )

        def dummy_person(year_of_birth=None, gender_concept=None, ethnicity_concept=None, race_concept=None, location=None):
            person = Person.objects.create(
                year_of_birth = year_of_birth,
                gender_concept = Concept.objects.get(concept_id=gender_concept),
                # ethnicity_concept = Concept.objects.get(concept_id=ethnicity_concept),
                race_concept = Concept.objects.get(concept_id=race_concept),
                #location
                #ethnicity
            )
            return person

        # Idioma pt
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

        # Domains
        domain("Domain", "Domain", 1)
        domain("Gender", "Gender", 2)
        domain("Race", "Race", 3)
        domain("Ethnicity", "Ethnicity", 4)
        domain("Metadata", "Metadata", 7)
        domain("Provider", "Provider", 33)
        domain("Geography", "Geography", 32558)

        # Vocabularies concepts
        add_concept(32541, "OpenStreetMap (OSMF)", "Vocabulary", "OMOP generated", "Metadata", "Vocabulary", "OpenStreetMap (OSMF)")
        add_concept(32573, "OMOP Provider", "Vocabulary", "OMOP generated", "Metadata", "Vocabulary", "Provedor OMOP")
        add_concept(32675,	"OMOP Metadata", "Vocabulary", "OMOP generated", "Metadata", "Vocabulary", "Metadata OMOP")
        add_concept(44819096, "OMOP Standardized Vocabularies", "Vocabulary", "OMOP generated", "Metadata","Vocabulary", "Vocabulários Padronizados OMOP")
        add_concept(44819108, "OMOP Gender", "Vocabulary", "OMOP generated", "Metadata", "Vocabulary", "Gênero OMOP")
        add_concept(44819109, "Race and Ethnicity Code Set (USBC)", "Vocabulary", "OMOP generated", "Metadata", "Vocabulary", "Conjunto de Códigos de Raça e Etnia (USBC)")
        add_concept(44819134, "OMOP Ethnicity", "Vocabulary", "OMOP generated", "Metadata", "Vocabulary", "Etnia OMOP")
        add_concept(44819232, "OMOP Vocabulary", "Vocabulary", "OMOP generated", "Metadata", "Vocabulary", "Vocabulário OMOP")

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
        add_concept(32580, "Allied Health Professional", "Provider", "OMOP4822445", "Provider", "Provider", "Profissional de Saúde Aliado")
        add_concept(32581, "Nurse", "Provider", "OMOP4822446", "Provider", "Provider", "Enfermeiro")
        add_concept(33003, "Service Provider", "Provider", "OMOP5117445", "Provider", "Provider", "Prestador de Serviço")
        add_concept(33005, "Psychiatry or Neurology", "Physician Specialty", "OMOP5117448", "Provider", "Provider", "Psiquiatria ou Neurologia")

        dummy_person(year_of_birth=1990, gender_concept=8507, race_concept=8527)
        dummy_person(year_of_birth=1999, gender_concept=8532, race_concept=8657)
        dummy_person(year_of_birth=1981, gender_concept=8551, race_concept=8516)

        #Comentei por enquanto por que n tem vocabulários para esses ainda
        # # Measurements
        # add_concept(3025315, "Body Weight", "Measurement", "BW", "Measurement", "Peso corporal")
        # add_concept(3023540, "Body Height", "Measurement", "BH", "Measurement", "Altura corporal")

        # # SleepHealth
        # add_concept(9000001, "Sleep Quality: Good", "SleepHealth", "SLEEP_GOOD", "Observation", "Sono bom")
        # add_concept(9000002, "Sleep Quality: Poor", "SleepHealth", "SLEEP_POOR", "Observation", "Sono ruim")

        # # PhysicalExercise
        # add_concept(9000010, "Exercises Regularly", "PhysicalExercise", "EX_REG", "Observation", "Exercício regular")
        # add_concept(9000011, "Sedentary", "PhysicalExercise", "EX_NONE", "Observation", "Sedentário")

        # # EatingHabits
        # add_concept(9000020, "Healthy Diet", "EatingHabits", "DIET_HEALTHY", "Observation", "Dieta saudável")
        # add_concept(9000021, "Unhealthy Diet", "EatingHabits", "DIET_POOR", "Observation", "Dieta ruim")

        # # Comorbidities
        # add_concept(9000030, "Hypertension", "Comorbidity", "HTN", "Condition", "Hipertensão")
        # add_concept(9000031, "Diabetes", "Comorbidity", "DM", "Condition", "Diabetes")

        # # Medications
        # add_concept(9000040, "Fluoxetine", "Medication", "FLX", "Drug", "Fluoxetina")
        # add_concept(9000041, "Ibuprofen", "Medication", "IBU", "Drug", "Ibuprofeno")

        # # SubstanceUse
        # add_concept(9000050, "Alcohol Use", "SubstanceUse", "ALC", "Observation", "Uso de álcool")
        # add_concept(9000051, "Tobacco Use", "SubstanceUse", "TOB", "Observation", "Uso de tabaco")



        self.stdout.write(self.style.SUCCESS("✔️  Conceitos populados com sucesso."))
