from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from app_saude.models import *


class Command(BaseCommand):

    def handle(self, *args, **kwargs):

        def vocabulary(id, name, concept_id):
            return Vocabulary.objects.get_or_create(
                vocabulary_id=id,
                defaults={
                    "vocabulary_name": name,
                    "vocabulary_concept": Concept.objects.get_or_create(concept_id=concept_id)[0],
                },
            )

        # vocabulary (IMPORTED FROM ATHENA 14/05/2025)
        vocabulary("DPD", "Drug Product Database (Health Canada)", 231)
        vocabulary("dm+d", "Dictionary of Medicines and Devices (NHS)", 232)
        vocabulary("BDPM", "Public Database of Medications (Social-Sante)", 236)
        vocabulary("AMT", "Australian Medicines Terminology (NEHTA)", 238)
        vocabulary("EphMRA ATC", "Anatomical Classification of Pharmaceutical Products (EphMRA)", 243)
        vocabulary("NFC", "New Form Code (EphMRA)", 245)
        vocabulary("RxNorm Extension", "OMOP RxNorm Extension", 252)
        vocabulary("Cost Type", "OMOP Cost Type", 5029)
        vocabulary(
            "ICD9CM",
            "International Classification of Diseases, Ninth Revision, Clinical Modification, Volume 1 and 2 (NCHS)",
            5046,
        )
        vocabulary("UB04 Typ bill", "UB04 Type of Bill - Institutional (USHIK)", 32044)
        vocabulary("UB04 Point of Origin", "UB04 Claim Source Inpatient Admission Code (CMS)", 32045)
        vocabulary("UB04 Pri Typ of Adm", "UB04 Claim Inpatient Admission Type Code (CMS)", 32046)
        vocabulary("UB04 Pt dis status", "UB04 Patient Discharge Status Code (CMS)", 32047)
        vocabulary("KDC", "Korean Drug Code (HIRA)", 32422)
        vocabulary(
            "SUS",
            "Table of Procedures, Drugs, Orthoses, Protheses and Special Materials (Brazilian Unified Health System)",
            32446,
        )
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
        vocabulary(
            "KCD7",
            "Korean Standard Classfication of Diseases and Causes of Death, 7th Revision (STATISTICS KOREA)",
            32688,
        )
        vocabulary("KNHIS", "Korean Payer (KNHIS)", 32723)
        vocabulary("Korean Revenue Code", "Korean Revenue Code (KNHIS)", 32724)
        vocabulary("CTD", "Comparative Toxicogenomic Database (NCSU)", 32735)
        vocabulary("EDI", "Korean Electronic Data Interchange code system (HIRA)", 32736)
        vocabulary("ICD10CN", "International Classification of Diseases, Tenth Revision, Chinese Edition (CAMS)", 32740)
        vocabulary(
            "ICD9ProcCN",
            "International Classification of Diseases, Ninth Revision, Chinese Edition, Procedures (CAMS)",
            32744,
        )
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
        vocabulary(
            "ICD10CM",
            "International Classification of Diseases, Tenth Revision, Clinical Modification (NCHS)",
            44819098,
        )
        vocabulary(
            "ICD9Proc",
            "International Classification of Diseases, Ninth Revision, Clinical Modification, Volume 3 (NCHS)",
            44819099,
        )
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

        # Custom vocabularies

        self.stdout.write(self.style.SUCCESS("✔️  Vocabulary populated successfully."))
