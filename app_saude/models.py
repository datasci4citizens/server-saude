from django.db import models


class Address(models.Model):
    address_id = models.AutoField(primary_key=True)
    person = models.ForeignKey("Person", models.DO_NOTHING, blank=True, null=True)
    street = models.CharField(max_length=255, blank=True, null=True)
    number = models.CharField(max_length=10, blank=True, null=True)
    complement = models.CharField(max_length=255, blank=True, null=True)
    neighborhood = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=50, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "Address"
        db_table_comment = "Stores residential address for a person."


class Caresite(models.Model):
    caresite_id = models.AutoField(db_column="careSite_id", primary_key=True)  # Field name made lowercase.
    care_site_name = models.CharField(max_length=255, blank=True, null=True)
    location_id = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "CareSite"
        db_table_comment = "Healthcare facility or unit where a provider may be associated. Currently not used in UI, but useful for future multi-site features."


class Concept(models.Model):
    concept_id = models.AutoField(primary_key=True)
    concept_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        db_comment="Name of the concept (e.g. 'Feminino', 'Tomar remÚdio')",
    )
    domain_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        db_comment="Categorization of concept purpose (e.g. 'gender', 'observation_type')",
    )
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "Concept"
        db_table_comment = "OMOP-compliant table for storing standardized values and custom entries such as habits, tasks, and symptoms."


class Domain(models.Model):
    domain_id = models.AutoField(primary_key=True)
    domain_name = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "Domain"
        db_table_comment = "Reference table for organizing types of concepts."


class Drugexposure(models.Model):
    drugexposure_id = models.AutoField(
        db_column="drugExposure_id",
        primary_key=True,
        db_comment="Primary key of the drug exposure record",
    )  # Field name made lowercase.
    person = models.ForeignKey(
        "Person",
        models.DO_NOTHING,
        blank=True,
        null=True,
        db_comment="The patient using the medication",
    )
    drug_concept = models.ForeignKey(
        Concept,
        models.DO_NOTHING,
        blank=True,
        null=True,
        db_comment="The prescribed or used drug (mapped to a concept)",
    )
    drug_exposure_start_date = models.DateField(
        blank=True, null=True, db_comment="Date when the medication regimen begins"
    )
    drug_exposure_end_date = models.DateField(
        blank=True, null=True, db_comment="Optional end date for the medication regimen"
    )
    stop_reason = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        db_comment="Optional reason for stopping the medication",
    )
    quantity = models.IntegerField(
        blank=True,
        null=True,
        db_comment="Total number of units prescribed or dispensed (e.g., 30 pills)",
    )
    interval_hours = models.IntegerField(
        blank=True,
        null=True,
        db_comment="Interval between doses in hours (e.g. 8 = every 8 hours)",
    )
    dose_times = models.TextField(
        blank=True, null=True, db_comment="Fixed intake times (e.g. ['08:00', '20:00'])"
    )  # This field type is a guess.
    sig = models.TextField(
        blank=True,
        null=True,
        db_comment="Free-text instructions for the patient (e.g. '1x ao dia em jejum')",
    )
    created_at = models.DateTimeField(blank=True, null=True, db_comment="Record creation timestamp")
    updated_at = models.DateTimeField(blank=True, null=True, db_comment="Record update timestamp")

    class Meta:
        managed = False
        db_table = "DrugExposure"
        db_table_comment = "Captures medication prescriptions or usage. Supports structured tracking for reminders, notifications, and clinical follow-up. Aligned with OMOP, with local extensions for real-time alerts based on dosage schedule."


class Emergencymessage(models.Model):
    emergency_message_id = models.AutoField(primary_key=True, db_comment="Primary key for the emergency message")
    person = models.ForeignKey(
        "Person",
        models.DO_NOTHING,
        blank=True,
        null=True,
        db_comment="Patient who triggered the emergency alert",
    )
    message = models.TextField(
        blank=True,
        null=True,
        db_comment="Free-text description of the emergency situation",
    )
    created_at = models.DateTimeField(blank=True, null=True, db_comment="Timestamp when the emergency was reported")
    updated_at = models.DateTimeField(
        blank=True,
        null=True,
        db_comment="Last update time (optional edits or resolutions)",
    )

    class Meta:
        managed = False
        db_table = "EmergencyMessage"
        db_table_comment = "Represents an urgent message initiated by the patient to signal psychological distress or critical situations. Can be shared with one or more providers."


class EmergencyProvider(models.Model):
    provider = models.ForeignKey(
        "Provider",
        models.DO_NOTHING,
        blank=True,
        null=True,
        db_comment="Professional assigned to respond to the emergency",
    )
    emergency_message = models.ForeignKey(
        Emergencymessage,
        models.DO_NOTHING,
        blank=True,
        null=True,
        db_comment="Emergency message associated with the provider",
    )
    acknowledged = models.BooleanField(
        blank=True,
        null=True,
        db_comment="Whether the provider acknowledged the emergency",
    )
    response_note = models.TextField(
        blank=True,
        null=True,
        db_comment="Optional note or summary written by the provider in response",
    )

    class Meta:
        managed = False
        db_table = "Emergency_Provider"
        db_table_comment = "Many-to-many relationship linking emergency alerts to responsible or notified healthcare professionals. Tracks acknowledgment and responses to urgent cases."


class Linkedprovider(models.Model):
    linkedprovider_id = models.AutoField(db_column="linkedProvider_id", primary_key=True)  # Field name made lowercase.
    person = models.ForeignKey("Person", models.DO_NOTHING, blank=True, null=True)
    provider = models.ForeignKey("Provider", models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "LinkedProvider"
        db_table_comment = "Links patients to providers. Enables shared visibility of patient data."


class Observation(models.Model):
    observation_id = models.AutoField(primary_key=True)
    person = models.ForeignKey(
        "Person",
        models.DO_NOTHING,
        blank=True,
        null=True,
        db_comment="Patient who made or received the observation",
    )
    observation_concept = models.ForeignKey(
        Concept,
        models.DO_NOTHING,
        blank=True,
        null=True,
        db_comment="What is being observed (e.g., mood, symptom, task)",
    )
    value_as_concept = models.ForeignKey(
        Concept,
        models.DO_NOTHING,
        related_name="observation_value_as_concept_set",
        blank=True,
        null=True,
        db_comment="Recorded answer, when categorical (e.g., 'Sad', '4 times')",
    )
    value_as_text = models.TextField(blank=True, null=True, db_comment="Free-text input (e.g. diary, thought, notes)")
    observation_date = models.DateTimeField(blank=True, null=True, db_comment="When the observation occurred")
    shared_with_provider = models.BooleanField(
        blank=True,
        null=True,
        db_comment="Whether this data is visible to the assigned provider",
    )
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "Observation"
        db_table_comment = "Core table for capturing all patient-reported or observed data, including symptoms, habits, notes, tasks, etc. OMOP-aligned and extensible."


class Person(models.Model):
    person_id = models.IntegerField(primary_key=True, db_comment="Primary key of the Person table")
    user = models.ForeignKey(
        "User",
        models.DO_NOTHING,
        blank=True,
        null=True,
        db_comment="Reference to the base User entity",
    )
    social_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        db_comment="Optional name used by the person in social or preferred contexts",
    )
    birth = models.DateField(blank=True, null=True, db_comment="Date of birth")
    height = models.FloatField(blank=True, null=True, db_comment="Height in meters (or preferred unit)")
    weight = models.FloatField(blank=True, null=True, db_comment="Weight in kilograms (or preferred unit)")
    biological_sex = models.ForeignKey(
        Concept,
        models.DO_NOTHING,
        blank=True,
        null=True,
        db_comment="Biological sex as a reference to Concept (e.g. Male, Female)",
    )
    gender_identity = models.ForeignKey(
        Concept,
        models.DO_NOTHING,
        related_name="person_gender_identity_set",
        blank=True,
        null=True,
        db_comment="Self-declared gender identity as Concept (e.g. Non-binary)",
    )
    race_concept = models.ForeignKey(
        Concept,
        models.DO_NOTHING,
        related_name="person_race_concept_set",
        blank=True,
        null=True,
        db_comment="Self-declared race/ethnicity as Concept",
    )
    created_at = models.DateTimeField(blank=True, null=True, db_comment="Record creation timestamp")
    updated_at = models.DateTimeField(blank=True, null=True, db_comment="Last update timestamp")

    class Meta:
        managed = False
        db_table = "Person"
        db_table_comment = "Represents an individual user who is a patient in the system. Each person is linked to a base User account and may optionally declare social identifiers, demographics, and physical attributes. Compatible with OMOP conventions for population-based data."


class Provider(models.Model):
    provider_id = models.IntegerField(primary_key=True, db_comment="Primary key of the Provider table")
    user = models.ForeignKey(
        "User",
        models.DO_NOTHING,
        blank=True,
        null=True,
        db_comment="Reference to the base User entity",
    )
    social_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        db_comment="Optional name used in social or professional contexts",
    )
    professional_email = models.CharField(
        unique=True,
        blank=True,
        null=True,
        db_comment="Official work email address of the provider",
    )
    professional_registration = models.IntegerField(
        blank=True,
        null=True,
        db_comment="Registration number in official professional board (e.g. CRM, CRP, COREN)",
    )
    created_at = models.DateTimeField(blank=True, null=True, db_comment="Record creation timestamp")
    updated_at = models.DateTimeField(blank=True, null=True, db_comment="Last update timestamp")

    class Meta:
        managed = False
        db_table = "Provider"
        db_table_comment = "Represents a healthcare professional, such as a Community Health Agent (ACS), psychologist, or psychiatrist. Each provider is linked to a User account and may interact with multiple patients through LinkedProvider."


class ProviderCaresite(models.Model):
    provider = models.ForeignKey(Provider, models.DO_NOTHING, blank=True, null=True)
    caresite = models.ForeignKey(
        Caresite, models.DO_NOTHING, db_column="careSite_id", blank=True, null=True
    )  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = "Provider_CareSite"
        db_table_comment = "Many-to-many relation between providers and care sites."


class ProviderConcept(models.Model):
    provider = models.ForeignKey(Provider, models.DO_NOTHING, blank=True, null=True)
    concept = models.ForeignKey(Concept, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "Provider_Concept"
        db_table_comment = "Represents provider specialities or roles via concepts (e.g. 'Psic¾logo')."


class User(models.Model):
    user_id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=255, blank=True, null=True, db_comment="User's given name")
    last_name = models.CharField(max_length=255, blank=True, null=True, db_comment="User's family name")
    email = models.CharField(unique=True, blank=True, null=True, db_comment="Login email, must be unique")
    is_active = models.BooleanField(blank=True, null=True, db_comment="Indicates if the user account is active")

    class Meta:
        managed = False
        db_table = "User"
        db_table_comment = "Generic authentication table, used by both patients (Person) and professionals (Provider)."


class Visitoccurrence(models.Model):
    visitoccurrence_id = models.AutoField(
        db_column="visitOccurrence_id",
        primary_key=True,
        db_comment="Primary key for the visit record",
    )  # Field name made lowercase.
    person = models.ForeignKey(
        Person,
        models.DO_NOTHING,
        blank=True,
        null=True,
        db_comment="The patient involved in the visit",
    )
    provider = models.ForeignKey(
        Provider,
        models.DO_NOTHING,
        blank=True,
        null=True,
        db_comment="The healthcare professional attending the visit (optional)",
    )
    caresite = models.ForeignKey(
        Caresite,
        models.DO_NOTHING,
        db_column="careSite_id",
        blank=True,
        null=True,
        db_comment="Healthcare location where the visit occurred (optional)",
    )  # Field name made lowercase.
    visit_date = models.DateTimeField(blank=True, null=True, db_comment="Start date and time of the visit")
    visit_end_date = models.DateTimeField(blank=True, null=True, db_comment="End date and time of the visit (optional)")
    observations = models.TextField(
        blank=True,
        null=True,
        db_comment="Free-text field for summarizing key points or outcomes of the visit",
    )
    created_at = models.DateTimeField(blank=True, null=True, db_comment="Timestamp of record creation")
    updated_at = models.DateTimeField(blank=True, null=True, db_comment="Timestamp of last update")

    class Meta:
        managed = False
        db_table = "VisitOccurrence"
        db_table_comment = "Stores scheduled or completed interactions between a patient and a healthcare professional. Can be used for consultations, check-ins, or assessments. Extensible to multiple providers and care sites."
