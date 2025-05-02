from django.conf import settings
from django.db import models


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_comment="Creation timestamp")
    updated_at = models.DateTimeField(auto_now=True, db_comment="Update timestamp")

    class Meta:
        abstract = True


class MyAbstractUser(TimestampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, blank=True, null=True)
    social_name = models.CharField(max_length=255, blank=True, null=True)
    birth_datetime = models.DateTimeField(blank=True, null=True, db_comment="Date and time of birth")

    class Meta:
        abstract = True


class Vocabulary(TimestampedModel):
    vocabulary_id = models.CharField(max_length=20, primary_key=True, db_comment="Primary key of Vocabulary")
    vocabulary_name = models.CharField(max_length=255, blank=True, null=True, db_comment="Name of the vocabulary")
    vocabulary_concept = models.ForeignKey(
        "Concept",
        on_delete=models.DO_NOTHING,
        blank=True,
        null=True,
        db_comment="Reference to Concept representing the vocabulary",
    )

    class Meta:
        db_table = "vocabulary"
        db_table_comment = "Vocabulary definitions in OMOP."


class ConceptClass(TimestampedModel):
    concept_class_id = models.CharField(max_length=20, primary_key=True, db_comment="Primary key of Concept Class")
    concept_class_name = models.CharField(max_length=255, blank=True, null=True, db_comment="Name of the Concept Class")
    concept_class_concept = models.ForeignKey(
        "Concept",
        on_delete=models.DO_NOTHING,
        blank=True,
        null=True,
        db_comment="Reference to Concept representing the Concept Class",
    )

    class Meta:
        db_table = "concept_class"
        db_table_comment = "Concept class categorization in OMOP."


class Concept(TimestampedModel):
    concept_id = models.AutoField(primary_key=True, db_comment="Primary key of Concept")
    concept_name = models.CharField(max_length=255, blank=True, null=True, db_comment="Name of the concept")
    domain = models.ForeignKey(
        "Domain",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="concept_domain_set",
        db_comment="Reference to Domain",
    )
    concept_class_id = models.CharField(max_length=20, blank=True, null=True, db_comment="Class of the concept")
    concept_code = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        db_comment="Code of the concept in source vocabulary",
    )
    valid_start_date = models.DateField(blank=True, null=True, db_comment="Start date of concept validity")
    valide_end_date = models.DateField(blank=True, null=True, db_comment="End date of concept validity")

    class Meta:
        db_table = "concept"
        db_table_comment = "OMOP-compliant table for standardized concepts."


class ConceptSynonym(TimestampedModel):
    concept = models.ForeignKey(
        Concept,
        on_delete=models.CASCADE,
        related_name="concept_synonym_concept_set",
        db_comment="Reference to Concept",
    )
    concept_synonym_name = models.CharField(max_length=1000, blank=True, null=True, db_comment="Synonym name")
    language_concept = models.ForeignKey(
        Concept,
        on_delete=models.DO_NOTHING,
        blank=True,
        null=True,
        related_name="concept_synonym_language_concept_set",
        db_comment="Language Concept of the synonym",
    )

    class Meta:
        db_table = "concept_synonym"
        db_table_comment = "Synonyms for concepts in OMOP."
        indexes = [models.Index(fields=["concept"], name="idx_concept_synonym_id")]


class Domain(TimestampedModel):
    domain_id = models.CharField(max_length=100, primary_key=True, db_comment="Primary key of Domain Class")
    domain_name = models.CharField(max_length=255, blank=True, null=True, db_comment="Name of the domain")
    domain_concept = models.ForeignKey(
        Concept,
        on_delete=models.DO_NOTHING,
        blank=True,
        null=True,
        related_name="domain_concept_set",
        db_comment="Reference to Concept representing the domain",
    )

    class Meta:
        db_table = "domain"
        db_table_comment = "Domain definitions grouping concepts."


class Location(TimestampedModel):
    location_id = models.AutoField(primary_key=True, db_comment="Primary key of Location")
    address_1 = models.CharField(max_length=50, blank=True, null=True, db_comment="Street and number")
    address_2 = models.CharField(max_length=50, blank=True, null=True, db_comment="Complement")
    city = models.CharField(max_length=255, blank=True, null=True, db_comment="City")
    state = models.CharField(max_length=255, blank=True, null=True, db_comment="State")
    zip = models.CharField(max_length=20, blank=True, null=True, db_comment="Postal code")
    country_concept = models.ForeignKey(
        Concept,
        on_delete=models.DO_NOTHING,
        blank=True,
        null=True,
        db_comment="Country Concept",
    )

    class Meta:
        db_table = "location"
        db_table_comment = "Stores geographical locations (address information)."


class Person(MyAbstractUser):
    person_id = models.AutoField(primary_key=True, db_comment="Primary key of Person")
    year_of_birth = models.IntegerField(blank=True, null=True, db_comment="Year of birth")
    gender_concept = models.ForeignKey(
        Concept,
        on_delete=models.DO_NOTHING,
        blank=True,
        null=True,
        related_name="person_gender_concept_set",
        db_comment="Gender Concept",
    )
    ethnicity_concept = models.ForeignKey(
        Concept,
        on_delete=models.DO_NOTHING,
        blank=True,
        null=True,
        related_name="person_ethnicity_concept_set",
        db_comment="Ethnicity Concept",
    )
    race_concept = models.ForeignKey(
        Concept,
        on_delete=models.DO_NOTHING,
        blank=True,
        null=True,
        related_name="person_racer_concept_set",
        db_comment="Race Concept",
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.DO_NOTHING,
        blank=True,
        null=True,
        db_comment="Location of residence",
    )

    class Meta:
        db_table = "person"
        db_table_comment = "Represents an individual user who is a patient."


class Provider(MyAbstractUser):
    provider_id = models.AutoField(primary_key=True, db_comment="Primary key of Provider")
    professional_registration = models.IntegerField(
        blank=True, null=True, db_comment="Professional registration number"
    )
    specialty_concept = models.ForeignKey(
        Concept,
        on_delete=models.DO_NOTHING,
        blank=True,
        null=True,
        db_comment="Specialty Concept",
    )
    care_site = models.ForeignKey(
        "CareSite",
        on_delete=models.DO_NOTHING,
        blank=True,
        null=True,
        db_comment="Reference to Care Site",
    )

    class Meta:
        db_table = "provider"
        db_table_comment = "Healthcare providers in OMOP."


class CareSite(TimestampedModel):
    care_site_id = models.AutoField(primary_key=True, db_comment="Primary key of Care Site")
    care_site_name = models.CharField(max_length=255, blank=True, null=True, db_comment="Name of the Care Site")
    location = models.ForeignKey(
        Location,
        on_delete=models.DO_NOTHING,
        blank=True,
        null=True,
        db_comment="Location of Care Site",
    )
    place_of_service_concept = models.ForeignKey(
        Concept,
        on_delete=models.DO_NOTHING,
        blank=True,
        null=True,
        db_comment="Place of Service Concept",
    )

    class Meta:
        db_table = "care_site"
        db_table_comment = "Facilities where care is provided."


class DrugExposure(TimestampedModel):
    drug_exposure_id = models.AutoField(primary_key=True, db_comment="Primary key of Drug Exposure")
    person = models.ForeignKey(
        Person,
        on_delete=models.DO_NOTHING,
        blank=True,
        null=True,
        db_comment="Patient receiving the drug",
    )
    drug_concept = models.ForeignKey(
        Concept,
        on_delete=models.DO_NOTHING,
        blank=True,
        null=True,
        related_name="drug_concept_set",
        db_comment="Drug Concept",
    )
    drug_type_concept = models.ForeignKey(
        Concept,
        on_delete=models.DO_NOTHING,
        blank=True,
        null=True,
        related_name="drug_type_concept_set",
        db_comment="Drug Type Concept",
    )
    drug_exposure_start_date = models.DateField(blank=True, null=True, db_comment="Start date of drug exposure")
    drug_exposure_end_date = models.DateField(blank=True, null=True, db_comment="End date of drug exposure")
    stop_reason = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        db_comment="Reason for stopping medication",
    )
    quantity = models.IntegerField(blank=True, null=True, db_comment="Quantity administered")
    interval_hours = models.IntegerField(blank=True, null=True, db_comment="Interval between doses in hours")
    dose_times = models.TextField(blank=True, null=True, db_comment="Scheduled dose times")
    sig = models.TextField(blank=True, null=True, db_comment="Free-text dosage instructions")

    class Meta:
        db_table = "drug_exposure"
        db_table_comment = "Records of drug prescriptions or administration."


class Observation(TimestampedModel):
    observation_id = models.AutoField(primary_key=True, db_comment="Primary key of Observation")
    person = models.ForeignKey(
        Person,
        on_delete=models.DO_NOTHING,
        blank=True,
        null=True,
        db_comment="Patient linked to the observation",
    )
    provider = models.ForeignKey(
        Provider,
        on_delete=models.DO_NOTHING,
        blank=True,
        null=True,
        db_comment="Provider attending the visit",
    )
    observation_concept = models.ForeignKey(
        Concept,
        on_delete=models.DO_NOTHING,
        blank=True,
        null=True,
        related_name="observation_concept_set",
        db_comment="Observation Concept",
    )
    value_as_concept = models.ForeignKey(
        Concept,
        on_delete=models.DO_NOTHING,
        blank=True,
        null=True,
        related_name="observation_value_as_concept_set",
        db_comment="Value as Concept",
    )
    value_as_string = models.CharField(max_length=60, blank=True, null=True, db_comment="Free-text value")
    observation_date = models.DateTimeField(blank=True, null=True, db_comment="Date and time of observation")
    observation_type_concept = models.ForeignKey(
        Concept,
        on_delete=models.DO_NOTHING,
        blank=True,
        null=True,
        related_name="observation_type_concept_set",
        db_comment="Observation Type Concept",
    )
    shared_with_provider = models.BooleanField(blank=True, null=True, db_comment="Visibility to assigned provider")

    class Meta:
        db_table = "observation"
        db_table_comment = "Captured patient-reported observations."


class VisitOccurrence(TimestampedModel):
    visit_occurrence_id = models.AutoField(primary_key=True, db_comment="Primary key of Visit Occurrence")
    person = models.ForeignKey(
        Person,
        on_delete=models.DO_NOTHING,
        blank=True,
        null=True,
        db_comment="Patient involved in the visit",
    )
    provider = models.ForeignKey(
        Provider,
        on_delete=models.DO_NOTHING,
        blank=True,
        null=True,
        db_comment="Provider attending the visit",
    )
    care_site = models.ForeignKey(
        CareSite,
        on_delete=models.DO_NOTHING,
        blank=True,
        null=True,
        db_comment="Care Site location",
    )
    visit_concept = models.ForeignKey(
        Concept,
        on_delete=models.DO_NOTHING,
        blank=True,
        null=True,
        related_name="vistit_concept_set",
        db_comment="Visit Concept",
    )
    visit_start_date = models.DateTimeField(blank=True, null=True, db_comment="Visit start date and time")
    visit_end_date = models.DateTimeField(blank=True, null=True, db_comment="Visit end date and time")
    visit_type_concept = models.ForeignKey(
        Concept,
        on_delete=models.DO_NOTHING,
        blank=True,
        null=True,
        related_name="visit_type_concept_set",
        db_comment="Visit Type Concept",
    )
    observations = models.TextField(blank=True, null=True, db_comment="Summary notes of the visit")

    class Meta:
        db_table = "visit_occurrence"
        db_table_comment = "Interactions between patients and healthcare providers."


class Measurement(TimestampedModel):
    measurement_id = models.AutoField(primary_key=True, db_comment="Primary key of Measurement")
    person = models.ForeignKey(
        Person,
        on_delete=models.DO_NOTHING,
        blank=True,
        null=True,
        db_comment="Patient linked to the measurement",
    )
    measurement_concept = models.ForeignKey(
        Concept,
        on_delete=models.DO_NOTHING,
        blank=True,
        null=True,
        related_name="measurement_concept_set",
        db_comment="Measurement Concept",
    )
    measurement_date = models.DateTimeField(blank=True, null=True, db_comment="Date and time of measurement")
    measurement_type_concept = models.ForeignKey(
        Concept,
        on_delete=models.DO_NOTHING,
        blank=True,
        null=True,
        related_name="measurement_type_concept_set",
        db_comment="Measurement Type Concept",
    )

    class Meta:
        db_table = "measurement"
        db_table_comment = "Measurements taken on persons (e.g., height, weight, labs)."


class FactRelationship(TimestampedModel):
    domain_concept_id_1 = models.ForeignKey(
        Concept,
        related_name="factrel_domain_concept_1_set",
        on_delete=models.DO_NOTHING,
        db_comment="Domain Concept of first fact",
    )
    fact_id_1 = models.IntegerField(db_comment="ID of first fact")
    domain_concept_id_2 = models.ForeignKey(
        Concept,
        related_name="factrel_domain_concept_2_set",
        on_delete=models.DO_NOTHING,
        db_comment="Domain Concept of second fact",
    )
    fact_id_2 = models.IntegerField(db_comment="ID of second fact")
    relationship_concept = models.ForeignKey(
        Concept,
        related_name="factrel_relationship_concept_set",
        on_delete=models.DO_NOTHING,
        db_comment="Type of relationship Concept",
    )

    class Meta:
        db_table = "fact_relationship"
        db_table_comment = "Relates different entities (facts) within OMOP."
        unique_together = ("fact_id_1", "fact_id_2", "relationship_concept_id")
