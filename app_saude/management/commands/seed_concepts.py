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
            concept, _ = Concept.objects.update_or_create(
                concept_id=cid,
                defaults={
                    "concept_name": name,
                    "concept_class": ConceptClass.objects.get(concept_class_id=class_id),
                    "concept_code": code,
                    "domain": Domain.objects.get(domain_id=domain_id),
                    "vocabulary_id": vocabulary_id,
                },
            )
            if pt_name:
                ConceptSynonym.objects.update_or_create(
                    concept=concept, concept_synonym_name=pt_name, language_concept_id=4181536  # pt
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
        domain("Plan", "Health Plan - contract to administer healthcare transactions by the payer, facilitated by the sponsor", 32475)
        domain("Sponsor", "Sponsor - institution or individual financing healthcare transactions", 32476)
        domain("Payer", "Payer - institution administering healthcare transactions", 32477)
        domain("Plan Stop Reason", "Plan Stop Reason - Reason for termination of the Health Plan", 32478)
        domain("Episode", "Episode", 32527)
        domain("Geography", "Geographical object", 32558)
        domain("Regimen", "Treatment Regimen", 32687)
        domain("Condition Status", "OMOP Condition Status", 32889)
        domain("Language", "Language", 33068)
        domain("Cost", "Cost", 581456)

        # # Domains
        # domain("Domain", "Domain", 1)
        # domain("Gender", "Gender", 2)
        # domain("Race", "Race", 3)
        # domain("Ethnicity", "Ethnicity", 4)
        # domain("Metadata", "Metadata", 7)
        # domain("Provider", "Provider", 33)
        # domain("Geography", "Geography", 32558)
        # domain("Measurement", "Measurement", 2000013)
        # domain("Observation", "Observation", 2000014)
        # domain("Condition", "Condition", 2000015)
        # domain("Drug", "Drug", 2000016)
        # domain("Substance", "Substance", 2000017)
        # domain("Type", "Type", 2000018)
        # domain("Relationship", "Relationship", 2000019)
        # domain("Domain", "Domain", 2000020)

        # concept_class (IMPORTED FROM ATHENA 14/05/2025)
        concept_class("Quant Branded Box", "Quantified Branded Drug Box", 200)
        concept_class("Quant Clinical Box", "Quantified Clinical Drug Box", 201)
        concept_class("Branded Drug Box", "Branded Drug Box", 202)
        concept_class("Clinical Drug Box", "Clinical Drug Box", 203)
        concept_class("Disinfectant", "Non-human drug class Disinfectant", 240)
        concept_class("Imaging Material", "Non-human drug class Imaging Material", 241)
        concept_class("Supplier", "Supplier: Manufacturer, Wholesaler", 244)
        concept_class("Marketed Product", "Marketed Product", 250)
        concept_class("NFC", "New Form Code", 253)
        concept_class("ICD10PCS Hierarchy", "ICD10PCS Hierarchical Code", 259)
        concept_class("ICD10PCS", "ICD10PCS Code", 260)
        concept_class("Gemscript THIN", "Encrypted Gemscript for the THIN database", 5000)
        concept_class("AMP", "Actual Medicinal Product", 5002)
        concept_class("AMPP", "Actual Medicinal Product Pack", 5003)
        concept_class("VMP", "Virtual Medicinal Product", 5004)
        concept_class("VMPP", "Virtual Medicinal Product Pack", 5005)
        concept_class("Form", "dm+d Dose Form", 5006)
        concept_class("VTM", "Virtual Therapeutic Moiety", 5007)
        concept_class("Precise Ingredient", "Precise Ingredient", 5022)
        concept_class("Dose Form Group", "Dose Form Group", 5023)
        concept_class("Clinical Dose Group", "Semantic Clinical Dose Group", 5024)
        concept_class("Branded Dose Group", "Semantic Branded Dose Group", 5025)
        concept_class("Cost Type", "Cost Type", 5030)
        concept_class("AU Substance", "AU Substance (AMT)", 5034)
        concept_class("AU Qualifier", "AU Qualifier (AMT)", 5035)
        concept_class("Med Product Unit", "Medicinal Product Unit of Use (AMT)", 5036)
        concept_class("Med Product Pack", "Medicinal Product Pack (AMT)", 5037)
        concept_class("Medicinal Product", "Medicinal Product (AMT)", 5038)
        concept_class("Trade Product Pack", "Trade Product Pack (AMT)", 5039)
        concept_class("Trade Product", "Trade Product (AMT)", 5040)
        concept_class("Trade Product Unit", "Trade Product Unit of Use (AMT)", 5041)
        concept_class("Containered Pack", "Containered Trade Product Pack (AMT)", 5042)
        concept_class("Clinical Pack Box", "Clinical Pack Box", 5043)
        concept_class("Branded Pack Box", "Branded Pack Box", 5044)
        concept_class("Note Kind", "Kind of Note Attribute", 5048)
        concept_class("Note Service Type", "Service or activity resulting in Note Attribute", 5049)
        concept_class("Note Setting", "Point of Care Setting of Note Attribute", 5050)
        concept_class("Note Domain", "Note Subject Matter Domain Attribute", 5051)
        concept_class("Note Provider Role", "Provider Role of Note Attribute", 5052)
        concept_class("Frequency code", "Frequency code", 32038)
        concept_class("Full", "Full", 32039)
        concept_class("Typ bill 3 digits", "Typ bill 3 digits", 32040)
        concept_class("UB04 Point of Origin", "UB04 Point of Origin", 32041)
        concept_class("UB04 Pri Typ of Adm", "UB04 Pri Typ of Adm", 32042)
        concept_class("UB04 Pt dis status", "UB04 Pt dis status", 32043)
        concept_class("Doc Subject Matter", "LOINC Document Subject Matter Domain", 32449)
        concept_class("Doc Type of Service", "LOINC Document Type of Service", 32450)
        concept_class("Doc Role", "LOINC Document Role", 32451)
        concept_class("Doc Kind", "LOINC Document Kind", 32452)
        concept_class("Doc Setting", "LOINC Document Setting", 32453)
        concept_class("SUS", "SUS", 32464)
        concept_class("Payer", "Payer - institution administering healthcare transactions", 32479)
        concept_class("Sponsor", "Sponsor - institution or individual financing healthcare transactions", 32480)
        concept_class("Plan Stop Reason", "Plan Stop Reason - Reason for termination of the Health Plan", 32481)
        concept_class("Benefit", "Benefit - healthcare items or services covered under a Health Plan", 32482)
        concept_class("Metal level", "Metal level: ratio of split of the healthcare transaction costs between Health Plan and patient", 32483)
        concept_class("LOINC Group", "LOINC Group", 32484)
        concept_class("Table", "OMOP CDM Table", 32486)
        concept_class("Field", "OMOP CDM Table Field", 32487)
        concept_class("CDM", "CDM", 32522)
        concept_class("Disease Extent", "Disease Extent", 32524)
        concept_class("Treatment", "Treatment", 32525)
        concept_class("Episode of Care", "Episode of Care", 32526)
        concept_class("MEDRT Extension", "MEDRT Extension", 32536)
        concept_class("Disposition", "Disposition", 32538)
        concept_class("Episode Type", "Episode Type", 32543)
        concept_class("Life circumstance", "Animal life circumstance", 32550)
        concept_class("10th level", "10th administrative level", 32559)
        concept_class("3rd level", "3rd administrative level", 32560)
        concept_class("8th level", "8th administrative level", 32561)
        concept_class("12th level", "12th administrative level", 32562)
        concept_class("9th level", "9th administrative level", 32563)
        concept_class("5th level", "5th administrative level", 32564)
        concept_class("6th level", "6th administrative level", 32565)
        concept_class("2nd level", "2nd administrative level", 32566)
        concept_class("11th level", "11th administrative level", 32567)
        concept_class("4th level", "4th administrative level", 32568)
        concept_class("7th level", "7th administrative level", 32569)
        concept_class("US Census Region", "United States Census Bureau Region", 32571)
        concept_class("US Census Division", "United States Census Bureau Division", 32572)
        concept_class("Provider", "OMOP Provider", 32575)
        concept_class("Physician Specialty", "OMOP Physician Specialty", 32576)
        concept_class("Regimen type", "Regimen type", 32636)
        concept_class("Component", "Component", 32637)
        concept_class("Route", "Route", 32638)
        concept_class("Regimen", "Regimen", 32639)
        concept_class("Component Class", "Component Class", 32640)
        concept_class("Context", "Context", 32641)
        concept_class("NAACCR Proc Schema", "NAACCR Procedure Schema", 32651)
        concept_class("NAACCR Procedure", "NAACCR Procedure", 32652)
        concept_class("NAACCR Value", "NAACCR Value", 32653)
        concept_class("NAACCR Schema", "NAACCR Schema", 32654)
        concept_class("NAACCR Variable", "NAACCR Variable", 32655)
        concept_class("Permissible Range", "Permissible Range", 32663)
        concept_class("Metadata", "Metadata", 32674)
        concept_class("BioCondition", "BioCondition", 32689)
        concept_class("Modality", "Modality", 32690)
        concept_class("KCD7 code", "KCD7 code", 32694)
        concept_class("LOINC System", "LOINC System", 32717)
        concept_class("LOINC Component", "LOINC Component", 32718)
        concept_class("LOINC Scale", "LOINC Scale", 32719)
        concept_class("LOINC Time", "LOINC Time", 32720)
        concept_class("LOINC Method", "LOINC Method", 32721)
        concept_class("LOINC Property", "LOINC Property", 32722)
        concept_class("Proc Hierarchy", "Procedure Hierarchy", 32737)
        concept_class("ICD10 Histology", "ICD10 Histology", 32741)
        concept_class("ICD10 Chapter", "ICD10 Chapter", 32742)
        concept_class("ICD10 SubChapter", "ICD10 SubChapter", 32743)
        concept_class("6-dig billing code", "6-dig billing code", 32745)
        concept_class("ICD9Proc Chapter", "ICD9Proc Chapter", 32746)
        concept_class("CAP Value", "CAP Value", 32772)
        concept_class("CAP Variable", "CAP Variable", 32773)
        concept_class("CAP Header", "CAP Header", 32774)
        concept_class("CAP Protocol", "CAP Protocol", 32775)
        concept_class("Regimen Class", "Regimen Class", 32794)
        concept_class("Question source", "Question source", 32805)
        concept_class("Condition Status", "OMOP Condition Status", 32888)
        concept_class("RNA Variant", "RNA Variant", 32923)
        concept_class("DNA Variant", "DNA Variant", 32924)
        concept_class("Genetic Variation", "Genetic Variation", 32925)
        concept_class("Variant", "Variant", 32926)
        concept_class("Protein Variant", "Protein Variant", 32927)
        concept_class("Topography", "Cancer topography and anatomical site", 32930)
        concept_class("Margin", "Tumor resection margins and involvement by cancer cells", 32931)
        concept_class("Nodes", "Lymph node metastases", 32932)
        concept_class("Staging/Grading", "Official Grade or Stage System", 32933)
        concept_class("Extension/Invasion", "Local cancer growth and invasion into adjacent tissue and organs", 32934)
        concept_class("Dimension", "Tumor size and dimension", 32935)
        concept_class("Histopattern", "Histological patterns of cancer tissue", 32936)
        concept_class("Metastasis", "Distant metastases", 32937)
        concept_class("Disease Dynamic", "Disease Dynamic", 32938)
        concept_class("AJCC Chapter", "AJCC Chapter", 32950)
        concept_class("AJCC Category", "AJCC Category", 32951)
        concept_class("Proc Group", "Procedure Group", 32958)
        concept_class("Category", "Category", 32966)
        concept_class("Variable", "Variable", 32967)
        concept_class("Value", "Value", 32968)
        concept_class("Precoordinated pair", "Precoordinated (Question-Answer/Variable-Value) pair ", 32969)
        concept_class("Multiple Ingredients", "Multiple Ingredients", 33001)
        concept_class("Language", "Language", 33070)
        concept_class("Vaccine Group", "Vaccine Group", 33094)
        concept_class("Disorder", "Disorder", 33099)
        concept_class("Structural Variant", "Variant at the DNA level not attributable to a single gene, including a karyotype", 33106)
        concept_class("Gene Protein Variant", "Variant at the protein level for a gene", 33107)
        concept_class("Gene Variant", "Variant of unspecified modality at the gene level", 33108)
        concept_class("Gene DNA Variant", "Variant at the DNA level attributable to a gene", 33109)
        concept_class("Gene RNA Variant", "Variant at the transcript (RNA) level for a gene", 33110)
        concept_class("Core", "Core questionnaire", 33120)
        concept_class("Standalone", "Standalone questionnaire", 33121)
        concept_class("CAT", "Сomputerised adaptive testing questionnaire", 33122)
        concept_class("CAT Short", "Short version of Сomputerised adaptive testing questionnaire", 33123)
        concept_class("Previous", "Historical version of questionnaire", 33124)
        concept_class("Direction", "Direction of question", 33125)
        concept_class("Issue", "Issue associated with question", 33126)
        concept_class("Response Scale", "Response scale in questionnaire", 33127)
        concept_class("Time Scale", "Time scale in questionnaire", 33128)
        concept_class("Symptom Scale", "Symptom scale in questionnaire", 33129)
        concept_class("LOINC Document Type", "LOINC Document Type", 581372)
        concept_class("Specimen Type", "OMOP Specimen Type", 581377)
        concept_class("CVX", "CVX vaccine", 581401)
        concept_class("Topic", "Topic", 581407)
        concept_class("Module", "Module", 581408)
        concept_class("PPI Modifier", "PPI Modifier", 581409)
        concept_class("ICDO Topography", "ICDO Topography", 581433)
        concept_class("ICDO Histology", "ICDO Histology", 581434)
        concept_class("ICDO Condition", "ICDO Condition", 581435)
        concept_class("CDT Hierarchy", "CDT Hierarchy", 581439)
        concept_class("CDT", "CDT", 581440)
        concept_class("ISBT Product", "ISBT Product", 581443)
        concept_class("ISBT Class", "ISBT Class", 581444)
        concept_class("ISBT Modifier", "ISBT Modifier", 581445)
        concept_class("ISBT Attrib value", "ISBT Attrib value", 581446)
        concept_class("ISBT Attrib group", "ISBT Attrib group", 581447)
        concept_class("ISBT Attrib cat", "ISBT Attrib cat", 581448)
        concept_class("ISBT Category", "ISBT Category", 581449)
        concept_class("Type Concept", "Type Concept", 581453)
        concept_class("Summary", "Summary", 581454)
        concept_class("Detail", "Detail", 581455)
        concept_class("Ingredient", "Ingredient", 44818981)
        concept_class("Branded Pack", "Brand Name Pack", 44818982)
        concept_class("Pharma Preparation", "Pharmaceutical Preparations", 44818983)
        concept_class("Pharmacokinetics", "Pharmacokinetics", 44818984)
        concept_class("Place of Service", "Place Of Service", 44818985)
        concept_class("Admin Concept", "Administrative Concept", 44818986)
        concept_class("HLGT", "High Level Group Term", 44818990)
        concept_class("Chart Availability", "Chart Availability", 44818991)
        concept_class("Clinical Pack", "Generic Pack", 44818992)
        concept_class("Drug Class", "Drug Class", 44818993)
        concept_class("Therapeutic Class", "Therapeutic Class", 44818995)
        concept_class("Body Structure", "Body Structure", 44818996)
        concept_class("Clinical Finding", "Clinical Finding", 44818997)
        concept_class("Record Artifact", "Record Artifact", 44818999)
        concept_class("Death Type", "Death Type", 44819000)
        concept_class("Meas Type", "Measurement Type", 44819001)
        concept_class("Admitting Source", "Admitting Source", 44819002)
        concept_class("Discharge Dispo", "Discharge Disposition", 44819003)
        concept_class("Branded Drug Comp", "Semantic Branded Drug Component", 44819004)
        concept_class("Mechanism of Action", "Mechanism of Action", 44819005)
        concept_class("Pharmacologic Class", "Pharmacologic Class", 44819006)
        concept_class("Pharma/Biol Product", "Pharmaceutical / Biologic Product", 44819007)
        concept_class("Morph Abnormality", "Morphologic Abnormality", 44819008)
        concept_class("Physical Object", "Physical Object", 44819009)
        concept_class("Staging / Scales", "Staging And Scales", 44819010)
        concept_class("Location", "Environment or Geographical Location", 44819011)
        concept_class("Condition Occur Type", "Condition Occurrence Type", 44819012)
        concept_class("Procedure Occur Type", "Procedure Occurrence Type", 44819013)
        concept_class("Provider Specialty", "Health Care Provider Specialty", 44819014)
        concept_class("Specialty", "Specialty", 44819016)
        concept_class("PT", "Preferred Term", 44819017)
        concept_class("HLT", "High Level Term", 44819018)
        concept_class("Biobank Flag", "Biobank Flag", 44819019)
        concept_class("Clinical Drug Form", "Semantic Clinical Drug Form", 44819020)
        concept_class("Qualifier Value", "Qualifier Value", 44819021)
        concept_class("Social Context", "Social Context", 44819022)
        concept_class("Visit", "OMOP Visit", 44819023)
        concept_class("Drug Cohort", "Drug Cohort", 44819024)
        concept_class("Domain", "Domain", 44819025)
        concept_class("Concept Relationship", "Concept Relationship", 44819026)
        concept_class("Device Type", "Device Type", 44819027)
        concept_class("Clinical Drug", "Semantic Clinical Drug", 44819028)
        concept_class("Observable Entity", "Observable Entity", 44819029)
        concept_class("Race", "Race", 44819030)
        concept_class("Condition Cohort", "Condition Cohort", 44819034)
        concept_class("Ethnicity", "Ethnicity", 44819035)
        concept_class("SOC", "System Organ Class", 44819037)
        concept_class("Enrollment Basis", "Enrollment Basis", 44819038)
        concept_class("Visit Type", "Visit Type", 44819039)
        concept_class("Drug Product", "Drug Product", 44819040)
        concept_class("Branded Drug Form", "Semantic Branded Drug Form", 44819041)
        concept_class("Ind / CI", "Indication or Contra-Indication", 44819042)
        concept_class("Organism", "Organism", 44819043)
        concept_class("Undefined", "Undefined", 44819044)
        concept_class("Special Concept", "Special Concept", 44819046)
        concept_class("Biological Function", "Biological Function", 44819047)
        concept_class("Condition", "Condition", 44819048)
        concept_class("Currency", "Currency", 44819049)
        concept_class("Substance", "Substance", 44819050)
        concept_class("Context-dependent", "Situation with explicit context", 44819051)
        concept_class("Physical Force", "Physical Force", 44819052)
        concept_class("Canonical", "Canonical Unit", 44819053)
        concept_class("ATC", "Anatomical Therapeutic Chemical Classification", 44819054)
        concept_class("Specimen", "Specimen", 44819055)
        concept_class("Event", "Event", 44819056)
        concept_class("Namespace Concept", "Namespace Concept", 44819057)
        concept_class("Model Comp", "Model Component", 44819058)
        concept_class("Meas Class", "Measurement Class", 44819059)
        concept_class("SMQ", "Standardized Meddra Query", 44819060)
        concept_class("Note Type", "Note Type", 44819061)
        concept_class("Obs Period Type", "Observation Period Type", 44819062)
        concept_class("Branded Drug", "Semantic Branded Drug", 44819063)
        concept_class("Clinical Drug Comp", "Semantic Clinical Drug Component", 44819064)
        concept_class("Brand Name", "Brand Name", 44819065)
        concept_class("Dose Form", "Dose Form", 44819066)
        concept_class("Physiologic Effect", "Physiologic Effect", 44819067)
        concept_class("Chemical Structure", "Chemical Structure", 44819068)
        concept_class("Drug Interaction", "Drug Interaction", 44819069)
        concept_class("Attribute", "Attribute", 44819070)
        concept_class("Measurement", "Measurement", 44819071)
        concept_class("Unit", "Unit", 44819072)
        concept_class("Standard Unit", "Standard Unit", 44819073)
        concept_class("Custom Unit", "Custom Unit", 44819074)
        concept_class("Revenue Code", "Revenue Code", 44819075)
        concept_class("Observation Type", "Observation Type", 44819076)
        concept_class("Diagnostic Category", "Diagnostic Category", 44819077)
        concept_class("Drug Exposure Type", "Drug Exposure Type", 44819078)
        concept_class("Patient Status", "Patient Status", 44819079)
        concept_class("Procedure", "Procedure", 44819080)
        concept_class("LLT", "Lowest Level Term", 44819081)
        concept_class("ETC", "Enhanced Therapeutic Classification", 44819082)
        concept_class("Discharge Status", "Discharge Status", 44819083)
        concept_class("Encounter Type", "Encounter Type", 44819084)
        concept_class("Hispanic", "Hispanic", 44819085)
        concept_class("Gender", "Gender", 44819086)
        concept_class("Anatom Main Group", "1st Level - Anatomical Main Group", 44819087)
        concept_class("Therap Subgroup", "2nd Level - Therapeutic Subgroup", 44819088)
        concept_class("Pharma Subgroup", "3rd Level - Pharmacological Subgroup", 44819089)
        concept_class("Chem Subgroup", "4th Level - Chemical Subgroup", 44819090)
        concept_class("Chem Substance", "5th Level - Chemical Substance", 44819091)
        concept_class("Quality Metric", "Quality Metric", 44819092)
        concept_class("Observation", "Observation", 44819093)
        concept_class("Device", "Device", 44819094)
        concept_class("Procedure Drug", "Procedure Drug", 44819095)
        concept_class("Neoplasm", "Neoplasms", 44819168)
        concept_class("Blood/Immune Disease", "Diseases of the blood and blood-forming organs and certain disorders involving the immune mechanism", 44819169)
        concept_class("Endocrine Disease", "Endocrine, nutritional and metabolic diseases", 44819170)
        concept_class("Mental Disease", "Mental, Behavioral and Neurodevelopmental disorders", 44819171)
        concept_class("Nervous Disease", "Diseases of the nervous system", 44819172)
        concept_class("Eye Disease", "Diseases of the eye and adnexa", 44819173)
        concept_class("Ear Disease", "Diseases of the ear and mastoid process", 44819174)
        concept_class("Circulatory Disease", "Diseases of the circulatory system", 44819175)
        concept_class("Respiratory Disease", "Diseases of the respiratory system", 44819176)
        concept_class("Digestive Disease", "Diseases of the digestive system", 44819177)
        concept_class("Skin Disease", "Diseases of the skin and subcutaneous tissue", 44819178)
        concept_class("Soft Tissue Disease", "Diseases of the musculoskeletal system and connective tissue", 44819179)
        concept_class("Genitourinary Dis", "Diseases of the genitourinary system", 44819180)
        concept_class("Pregnancy", "Pregnancy, childbirth and the puerperium", 44819181)
        concept_class("Perinatal Disease", "Certain conditions originating in the perinatal period", 44819182)
        concept_class("Congenital Disease", "Congenital malformations, deformations and chromosomal abnormalities", 44819183)
        concept_class("Symptom", "Symptom", 44819184)
        concept_class("Injury", "Injury, poisoning and certain other consequences of external causes", 44819185)
        concept_class("External Cause", "External causes of morbidity", 44819186)
        concept_class("Health Service", "Factors influencing health status and contact with health services", 44819187)
        concept_class("Infectious Disease", "Certain infectious and parasitic diseases", 44819188)
        concept_class("Special Code", "Codes for special purposes", 44819236)
        concept_class("11-digit NDC", "11-digit NDC code", 44819243)
        concept_class("9-digit NDC", "9-digit NDC code", 44819244)
        concept_class("APC", "Ambulatory Patient Classification", 44819245)
        concept_class("Cohort", "Cohort", 44819246)
        concept_class("Concept Class", "OMOP Concept Class", 44819247)
        concept_class("Condition Type", "Condition Type", 44819248)
        concept_class("CPT4", "Current Procedural Terminology version 4", 44819249)
        concept_class("DRG", "Disease-related Group", 44819250)
        concept_class("Drug", "Drug", 44819251)
        concept_class("Drug Type", "Drug Type", 44819252)
        concept_class("Gemscript", "Gemscript", 44819253)
        concept_class("GCN_SEQNO", "GCN_SEQNO", 44819254)
        concept_class("GPI", "Generic Product Identifier", 44819255)
        concept_class("HCPCS", "Healthcare Common Procedure Coding System", 44819256)
        concept_class("HES Specialty", "HES Specialty", 44819257)
        concept_class("ICD10 code", "ICD10 code", 44819258)
        concept_class("ICD9CM code", "ICD9CM code", 44819259)
        concept_class("ICD9CM E code", "ICD9CM E code", 44819260)
        concept_class("ICD9CM V code", "ICD9CM V code", 44819261)
        concept_class("Indication", "Indication", 44819262)
        concept_class("LOINC", "Logical Observation Identifiers Names and Codes", 44819263)
        concept_class("LOINC Hierarchy", "LOINC Hierarchy", 44819264)
        concept_class("MDC", "Major Diagnostic Category", 44819265)
        concept_class("MedDRA", "Medical Dictionary for Regulatory Activities", 44819266)
        concept_class("Multilex", "Multilex", 44819267)
        concept_class("Multum", "Multum", 44819268)
        concept_class("NUCC", "National Uniform Claim Committee Specialty", 44819269)
        concept_class("OXMIS", "Oxford Medical Information System", 44819271)
        concept_class("Procedure Type", "Procedure Type", 44819272)
        concept_class("Read", "Read", 44819273)
        concept_class("Relationship", "OMOP Relationship", 44819274)
        concept_class("SPL", "SPL", 44819276)
        concept_class("VA Class", "VA Class", 44819277)
        concept_class("VA Product", "VA Product", 44819278)
        concept_class("Vocabulary", "OMOP Vocabulary", 44819279)
        concept_class("ATC 3rd", "ATC 3rd Level", 44819280)
        concept_class("ATC 1st", "ATC 1st Level", 44819281)
        concept_class("Canonical Unit", "Canonical Unit", 44819282)
        concept_class("ATC 2nd", "ATC 2nd Level", 44819283)
        concept_class("ATC 5th", "ATC 5th Level", 44819284)
        concept_class("ATC 4th", "ATC 4th Level", 44819285)
        concept_class("LOINC Class", "LOINC Class", 45754677)
        concept_class("Lab Test", "Laboratory Class", 45754678)
        concept_class("Clinical Observation", "Clinical Class", 45754679)
        concept_class("Claims Attachment", "Claims Attachments", 45754680)
        concept_class("Survey", "Surveys", 45754681)
        concept_class("Answer", "Answers", 45754682)
        concept_class("CPT4 Modifier", "CPT4 Modifier", 45754685)
        concept_class("CPT4 Hierarchy", "CPT4 Hierarchy", 45754686)
        concept_class("HCPCS Modifier", "HCPCS Modifier", 45754687)
        concept_class("HCPCS Class", "HCPCS Class", 45754688)
        concept_class("Navi Concept", "Navigational Concept", 45754795)
        concept_class("Inactive Concept", "Inactive Concept", 45754796)
        concept_class("Linkage Concept", "Linkage Concept", 45754797)
        concept_class("Link Assertion", "Link Assertion", 45754798)
        concept_class("DRG Type", "Disease Related Group Type", 45754799)
        concept_class("Diagnosis Code Type", "Diagnosis Code Type", 45754800)
        concept_class("Diagnosis Type", "Diagnosis Type", 45754801)
        concept_class("Procedure Code Type", "Procedure Code Type", 45754802)
        concept_class("Vital Source", "Vital Source", 45754803)
        concept_class("Blood Pressure Pos", "Blood Pressure Position", 45754804)
        concept_class("Linkage Assertion", "Linkage Assertion", 45754822)
        concept_class("ICD9CM non-bill code", "ICD9CM non-billable code", 45754823)
        concept_class("ICD9Proc non-bill", "ICD9Proc non-billable code", 45754824)
        concept_class("Vaccine", "Human drug class Vaccine", 45754855)
        concept_class("Standard Allergenic", "Human drug class Standardized Allergenic", 45754856)
        concept_class("Prescription Drug", "Human drug class Human Prescription Drug", 45754857)
        concept_class("OTC Drug", "Human drug class Human OTC Drug", 45754858)
        concept_class("Plasma Derivative", "Human drug class Plasma Derivative", 45754859)
        concept_class("Non-Stand Allergenic", "Human drug class Non-Standardized Allergenic", 45754860)
        concept_class("Cellular Therapy", "Human drug class Cellular Therapy", 45754861)
        concept_class("Quant Clinical Drug", "Quantified Clinical Drug", 45754862)
        concept_class("Quant Branded Drug", "Quantified Branded Drug", 45754863)
        concept_class("3-dig billing code", "3-digit billing code", 45754868)
        concept_class("4-dig billing code", "4-digit billing code", 45754869)
        concept_class("5-dig billing code", "5-digit billing code", 45754870)
        concept_class("4-dig billing E code", "4-digit billing E code", 45754871)
        concept_class("5-dig billing E code", "5-digit billing E code", 45754872)
        concept_class("3-dig billing V code", "3-digit billing V code", 45754873)
        concept_class("4-dig billing V code", "4-digit billing V code", 45754874)
        concept_class("5-dig billing V code", "5-digit billing V code", 45754875)
        concept_class("3-dig nonbill code", "3-digit non-billing code", 45754876)
        concept_class("4-dig nonbill code", "4-digit non-billing code", 45754877)
        concept_class("3-dig nonbill V code", "3-digit non-billing V code", 45754878)
        concept_class("3-dig nonbill E code", "3-digit non-billing E code", 45754879)
        concept_class("4-dig nonbill E code", "4-digit non-billing E code", 45754880)
        concept_class("2-dig nonbill code", "2-digit non-billing code", 45754881)
        concept_class("ICD10 Hierarchy", "ICD10 Hierarchy", 45754906)
        concept_class("4-dig nonbill V code", "4-digit non-billing V code", 45756722)
        concept_class("MS-DRG", "Medicare Severity Disease-related Group", 45757047)
        concept_class("Test", "Test", 45905711)
        concept_class("Diagnosis", "Diagnosis", 45905712)
        concept_class("Finding", "Finding", 45905713)
        concept_class("Anatomy", "Anatomy", 45905714)
        concept_class("Question", "Question", 45905715)
        concept_class("LabSet", "LabSet", 45905716)
        concept_class("MedSet", "MedSet", 45905717)
        concept_class("ConvSet", "ConvSet", 45905718)
        concept_class("Misc", "Misc", 45905719)
        concept_class("Symptom/Finding", "Symptom/Finding", 45905721)
        concept_class("Misc Order", "Misc Order", 45905722)
        concept_class("Workflow", "Workflow", 45905723)
        concept_class("State", "State", 45905724)
        concept_class("Program", "Program", 45905725)
        concept_class("Aggregate Meas", "Aggregate Measurement", 45905726)
        concept_class("Indicator", "Indicator", 45905727)
        concept_class("Monitoring", "Health Care Monitoring Topics", 45905728)
        concept_class("Radiology", "Radiology/Imaging Procedure", 45905729)
        concept_class("Frequency", "Frequency", 45905730)
        concept_class("Units of Measure", "Units of Measure", 45905732)
        concept_class("Drug form", "Drug form", 45905734)
        concept_class("Medical supply", "Medical supply", 45905735)
        concept_class("Main Heading", "Main Heading or Descriptor", 46233638)
        concept_class("Suppl Concept", "Supplementary Concept", 46233639)
        concept_class("3-char nonbill code", "3-character non-billing code", 46233658)
        concept_class("4-char nonbill code", "4-character non-billing code", 46233659)
        concept_class("5-char nonbill code", "5-character non-billing code", 46233660)
        concept_class("6-char nonbill code", "6-character non-billing code", 46233661)
        concept_class("7-char nonbill code", "7-character non-billing code", 46233662)
        concept_class("3-char billing code", "3-character billing code", 46233663)
        concept_class("4-char billing code", "4-character billing code", 46233664)
        concept_class("5-char billing code", "5-character billing code", 46233665)
        concept_class("6-char billing code", "6-character billing code", 46233666)
        concept_class("7-char billing code", "7-character billing code", 46233667)
        concept_class("3-dig billing E code", "3-digit billing E code", 46233669)
        concept_class("Food", "Non-human drug class Food", 46274137)
        concept_class("Supplement", "Non-human drug class Supplement", 46274138)
        concept_class("Cosmetic", "Non-human drug class Cosmetic", 46274139)
        concept_class("Animal Drug", "Non-human drug class Animal Drug", 46277305)

        # # Concept Classes
        # concept_class("Vocabulary", "Vocabulary", 11111)
        # concept_class("Domain", "Domain", 11112)
        # concept_class("Gender", "Gender", 11113)
        # concept_class("Race", "Race", 11114)
        # concept_class("Ethnicity", "Ethnicity", 11115)
        # concept_class("Provider", "Provider", 11116)
        # concept_class("Physician Specialty", "Physician Specialty", 11117)
        # concept_class("Brazil States", "Brazil States", 2000042)
        # concept_class("Measurement", "Measurement", 2000043)
        # concept_class("Observation", "Observation", 2000044)
        # concept_class("Quality", "Quality", 2000045)
        # concept_class("Frequency", "Frequency", 2000046)
        # concept_class("Comorbidity", "Comorbidity", 2000047)
        # concept_class("Medication", "Medication", 2000048)
        # concept_class("Substance", "Substance", 2000049)
        # concept_class("Type", "Type", 2000041)
        # concept_class("Recurrence", "Recurrence", 2000050)
        # concept_class("Relationship", "Relationship", 2000051)
        # concept_class("Observation Type", "Observation Type", 2000052)
        # concept_class("Metadata", "Metadata", 2000053)

        # vocabulary (IMPORTED FROM ATHENA 14/05/2025)
        vocabulary("DPD", "Drug Product Database (Health Canada)", 231)
        vocabulary("dm+d", "Dictionary of Medicines and Devices (NHS)", 232)
        vocabulary("BDPM", "Public Database of Medications (Social-Sante)", 236)
        vocabulary("AMT", "Australian Medicines Terminology (NEHTA)", 238)
        vocabulary("EphMRA ATC", "Anatomical Classification of Pharmaceutical Products (EphMRA)", 243)
        vocabulary("NFC", "New Form Code (EphMRA)", 245)
        vocabulary("RxNorm Extension", "OMOP RxNorm Extension", 252)
        vocabulary("Cost Type", "OMOP Cost Type", 5029)
        vocabulary("ICD9CM", "International Classification of Diseases, Ninth Revision, Clinical Modification, Volume 1 and 2 (NCHS)", 5046)
        vocabulary("UB04 Typ bill", "UB04 Type of Bill - Institutional (USHIK)", 32044)
        vocabulary("UB04 Point of Origin", "UB04 Claim Source Inpatient Admission Code (CMS)", 32045)
        vocabulary("UB04 Pri Typ of Adm", "UB04 Claim Inpatient Admission Type Code (CMS)", 32046)
        vocabulary("UB04 Pt dis status", "UB04 Patient Discharge Status Code (CMS)", 32047)
        vocabulary("KDC", "Korean Drug Code (HIRA)", 32422)
        vocabulary("SUS", "Table of Procedures, Drugs, Orthoses, Protheses and Special Materials (Brazilian Unified Health System)", 32446)
        vocabulary("Plan", "OMOP Health Plan", 32471)
        vocabulary("Sponsor", "OMOP Sponsor", 32472)
        vocabulary("SOPT", "Source of Payment Typology (PHDSC)", 32473)
        vocabulary("Plan Stop Reason", "OMOP Plan Stop Reason", 32474)
        vocabulary("CDM", "OMOP Common DataModel", 32485)
        vocabulary("Episode", "OMOP Episode", 32523)
        vocabulary("OSM", "OpenStreetMap (OSMF)", 32541)
        vocabulary("Episode Type", "OMOP Episode Type", 32542)
        vocabulary("SNOMED Veterinary", "SNOMED Veterinary Extension (VTSL)", 32549)
        vocabulary("JMDC", "Japan Medical Data Center Drug Code (JMDC)", 32557)
        vocabulary("US Census", "Census regions of the United States (USCB)", 32570)
        vocabulary("Provider", "OMOP Provider", 32573)
        vocabulary("Supplier", "OMOP Supplier", 32574)
        vocabulary("HemOnc", "HemOnc", 32613)
        vocabulary("NAACCR", "Data Standards & Data Dictionary Volume II (NAACCR)", 32642)
        vocabulary("Metadata", "OMOP Metadata", 32675)
        vocabulary("KCD7", "Korean Standard Classfication of Diseases and Causes of Death, 7th Revision (STATISTICS KOREA)", 32688)
        vocabulary("KNHIS", "Korean Payer (KNHIS)", 32723)
        vocabulary("Korean Revenue Code", "Korean Revenue Code (KNHIS)", 32724)
        vocabulary("CTD", "Comparative Toxicogenomic Database (NCSU)", 32735)
        vocabulary("EDI", "Korean Electronic Data Interchange code system (HIRA)", 32736)
        vocabulary("ICD10CN", "International Classification of Diseases, Tenth Revision, Chinese Edition (CAMS)", 32740)
        vocabulary("ICD9ProcCN", "International Classification of Diseases, Ninth Revision, Chinese Edition, Procedures (CAMS)", 32744)
        vocabulary("Nebraska Lexicon", "Nebraska Lexicon (UNMC)", 32757)
        vocabulary("OMOP Extension", "OMOP Extension (OHDSI)", 32758)
        vocabulary("CIM10", "International Classification of Diseases, Tenth Revision, French Edition (ATIH)", 32806)
        vocabulary("NCCD", "Normalized Chinese Clinical Drug knowledge base (UTHealth)", 32807)
        vocabulary("Type Concept", "OMOP Type Concept", 32808)
        vocabulary("Condition Status", "OMOP Condition Status", 32887)
        vocabulary("CIViC", "Clinical Interpretation of Variants in Cancer (civicdb.org)", 32913)
        vocabulary("CGI", "Cancer Genome Interpreter (Pompeu Fabra University)", 32914)
        vocabulary("ClinVar", "ClinVar (NCBI)", 32915)
        vocabulary("JAX", "The Clinical Knowledgebase (The Jackson Laboratory)", 32916)
        vocabulary("NCIt", "NCI Thesaurus (National Cancer Institute)", 32917)
        vocabulary("ICD10GM", "International Classification of Diseases, Tenth Revision, German Edition", 32928)
        vocabulary("Cancer Modifier", "Diagnostic Modifiers of Cancer (OMOP)", 32929)
        vocabulary("OPS", "Operations and Procedures Classification (OPS)", 32956)
        vocabulary("CCAM", "Common Classification of Medical Acts (ATIH)", 32957)
        vocabulary("UK Biobank", "UK Biobank (UK Biobank)", 32976)
        vocabulary("OncoKB", "Oncology Knowledge Base (MSK)", 32999)
        vocabulary("OMOP Genomic", "OMOP Genomic vocabulary of known variants involved in disease", 33002)
        vocabulary("OncoTree", "OncoTree (MSK)", 33008)
        vocabulary("OMOP Invest Drug", "OMOP Investigational Drugs", 33051)
        vocabulary("Language", "OMOP Language", 33069)
        vocabulary("CO-CONNECT", "CO-CONNECT (University of Nottingham)", 33091)
        vocabulary("CO-CONNECT MIABIS", "CO-CONNECT MIABIS (University of Nottingham)", 33092)
        vocabulary("CO-CONNECT TWINS", "CO-CONNECT TWINS (University of Nottingham)", 33093)
        vocabulary("NHS Ethnic Category", "NHS Ethnic Category", 33095)
        vocabulary("NHS Place of Service", "NHS Admission Source and Discharge Destination", 33096)
        vocabulary("CDISC", "Clinical Data Interchange Standards Consortium", 33116)
        vocabulary("EORTC QLQ", "EORTC Quality of Life questionnaires", 33119)
        vocabulary("MMI", "Modernizing Medicine (MMI)", 581367)
        vocabulary("Specimen Type", "OMOP Specimen Type", 581376)
        vocabulary("CVX", "CDC Vaccine Administered CVX (NCIRD)", 581400)
        vocabulary("PPI", "AllOfUs_PPI (Columbia)", 581404)
        vocabulary("ICDO3", "International Classification of Diseases for Oncology, Third Edition (WHO)", 581426)
        vocabulary("GGR", "Commented Drug Directory (BCFI)", 581450)
        vocabulary("Cost", "OMOP Cost", 581457)
        vocabulary("None", "OMOP Standardized Vocabularies", 44819096)
        vocabulary("SNOMED", "Systematic Nomenclature of Medicine - Clinical Terms (IHTSDO)", 44819097)
        vocabulary("ICD10CM", "International Classification of Diseases, Tenth Revision, Clinical Modification (NCHS)", 44819098)
        vocabulary("ICD9Proc", "International Classification of Diseases, Ninth Revision, Clinical Modification, Volume 3 (NCHS)", 44819099)
        vocabulary("HCPCS", "Healthcare Common Procedure Coding System (CMS)", 44819101)
        vocabulary("LOINC", "Logical Observation Identifiers Names and Codes (Regenstrief Institute)", 44819102)
        vocabulary("NDFRT", "National Drug File - Reference Terminology (VA)", 44819103)
        vocabulary("RxNorm", "RxNorm (NLM)", 44819104)
        vocabulary("NDC", "National Drug Code (FDA and manufacturers)", 44819105)
        vocabulary("UCUM", "Unified Code for Units of Measure (Regenstrief Institute)", 44819107)
        vocabulary("Gender", "OMOP Gender", 44819108)
        vocabulary("Race", "Race and Ethnicity Code Set (USBC)", 44819109)
        vocabulary("CMS Place of Service", "Place of Service Codes for Professional Claims (CMS)", 44819110)
        vocabulary("Multum", "Cerner Multum (Cerner)", 44819112)
        vocabulary("Read", "NHS UK Read Codes Version 2 (HSCIC)", 44819113)
        vocabulary("OXMIS", "Oxford Medical Information System (OCHP)", 44819114)
        vocabulary("ATC", "WHO Anatomic Therapeutic Chemical Classification", 44819117)
        vocabulary("Visit", "OMOP Visit", 44819119)
        vocabulary("VANDF", "Veterans Health Administration National Drug File (VA))", 44819120)
        vocabulary("SMQ", "Standardised MedDRA Queries (MSSO)", 44819121)
        vocabulary("VA Class", "VA National Drug File Class (VA)", 44819122)
        vocabulary("Cohort", "Legacy OMOP HOI or DOI cohort", 44819123)
        vocabulary("ICD10", "International Classification of Diseases, Tenth Revision (WHO)", 44819124)
        vocabulary("ICD10PCS", "ICD-10 Procedure Coding System (CMS)", 44819125)
        vocabulary("Drug Type", "OMOP Drug Exposure Type", 44819126)
        vocabulary("Condition Type", "OMOP Condition Occurrence Type", 44819127)
        vocabulary("Procedure Type", "OMOP Procedure Occurrence Type", 44819128)
        vocabulary("Observation Type", "OMOP Observation Type", 44819129)
        vocabulary("DRG", "Diagnosis-related group (CMS)", 44819130)
        vocabulary("MDC", "Major Diagnostic Categories (CMS)", 44819131)
        vocabulary("APC", "Ambulatory Payment Classification (CMS)", 44819132)
        vocabulary("Revenue Code", "UB04/CMS1450 Revenue Codes (CMS)", 44819133)
        vocabulary("Ethnicity", "OMOP Ethnicity", 44819134)
        vocabulary("Death Type", "OMOP Death Type", 44819135)
        vocabulary("MeSH", "Medical Subject Headings (NLM)", 44819136)
        vocabulary("NUCC", "National Uniform Claim Committee Health Care Provider Taxonomy Code Set (NUCC)", 44819137)
        vocabulary("Medicare Specialty", "Medicare provider/supplier specialty codes (CMS)", 44819138)
        vocabulary("SPL", "Structured Product Labeling (FDA)", 44819140)
        vocabulary("GCN_SEQNO", "Clinical Formulation ID (FDB)", 44819141)
        vocabulary("OPCS4", "OPCS Classification of Interventions and Procedures version 4 (NHS)", 44819143)
        vocabulary("HES Specialty", "Hospital Episode Statistics Specialty (NHS)", 44819145)
        vocabulary("Note Type", "OMOP Note Type", 44819146)
        vocabulary("Domain", "OMOP Domain", 44819147)
        vocabulary("PCORNet", "National Patient-Centered Clinical Research Network (PCORI)", 44819148)
        vocabulary("Obs Period Type", "OMOP Observation Period Type", 44819149)
        vocabulary("Visit Type", "OMOP Visit Type", 44819150)
        vocabulary("Device Type", "OMOP Device Type", 44819151)
        vocabulary("Meas Type", "OMOP Measurement Type", 44819152)
        vocabulary("Currency", "International Currency Symbol (ISO 4217)", 44819153)
        vocabulary("Vocabulary", "OMOP Vocabulary", 44819232)
        vocabulary("Concept Class", "OMOP Concept Class", 44819233)
        vocabulary("Cohort Type", "OMOP Cohort Type", 44819234)
        vocabulary("Relationship", "OMOP Relationship", 44819235)
        vocabulary("ABMS", "Provider Specialty (American Board of Medical Specialties)", 45756746)
        vocabulary("CIEL", "Columbia International eHealth Laboratory (Columbia University)", 45905710)

        # # Vocabularies
        # vocabulary("OSM", "OpenStreetMap (OSM)", 32541)
        # vocabulary("Provider", "OMOP Provider", 32573)
        # vocabulary("Metadata", "OMOP Metadata", 32675)
        # vocabulary("None", "OMOP Standardized Vocabularies", 44819096)
        # vocabulary("Gender", "OMOP Gender", 44819108)
        # vocabulary("Race", "Race and Ethnicity Code Set (USBC)", 44819109)
        # vocabulary("Ethnicity", "OMOP Ethnicity", 44819134)
        # vocabulary("Vocabulary", "OMOP Vocabulary", 44819232)
        # vocabulary("BR_STATES", "Brazil States", 2000001)
        # vocabulary("Measurement", "OMOP Measurement", 2000003)
        # vocabulary("Observation", "OMOP Observation", 2000004)
        # vocabulary("Condition", "OMOP Condition", 2000005)
        # vocabulary("Drug", "OMOP Drug", 2000006)
        # vocabulary("Substance", "OMOP Substance", 2000007)
        # vocabulary("Observation Type", "OMOP Observation Type", 2000008)
        # vocabulary("Relationship", "OMOP Relationship", 2000009)
        # vocabulary("Domain", "OMOP Domain", 2000010)

        # Língua Portuguesa
        # add_concept(4181536, "Portuguese language", "Qualifier Value", "297504001", "Language", "SNOMED", "Língua Portuguesa")
        Concept.objects.update_or_create(
            concept_id=4181536,
            defaults={
                "concept_name": "Portuguese language",
                "concept_class_id": "Qualifier Value",
                "concept_code": "297504001",
                "vocabulary_id": "SNOMED",
                "domain": Domain.objects.get(domain_id="Language"),
            },
        )
        ConceptSynonym.objects.update_or_create(
            concept=4181536, concept_synonym_name="Língua Portuguesa", language_concept_id=4181536  # pt
        )


        ##############################################################

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
        add_concept(32675, "OMOP Metadata", "Vocabulary", "OMOP geassim como nos Checkpoints, a ordem de apresentação será aleatória.nerated", "Metadata", "Vocabulary", "Metadata OMOP")
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

        # Comentei por enquanto por que n tem vocabulários para esses ainda
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
        add_concept(9000030, "Hypertension", "Comorbidity", "HTN", "Condition", "Condition", "Hipertensão")
        add_concept(9000031, "Diabetes", "Comorbidity", "DM", "Condition", "Condition", "Diabetes")

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

        User = get_user_model()
        user, _ = User.objects.get_or_create(
            email="mock-provider@email.com",
            defaults={"username": "mockprovider", "first_name": "Dr. Mock", "last_name": "Provider"},
        )

        Provider.objects.get_or_create(user=user)
        self.stdout.write(self.style.SUCCESS("✔️  Conceitos populados com sucesso."))
