from django.contrib.auth import get_user_model
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import *
from .utils.concept import get_concept_by_code

User = get_user_model()


######## AUTH SERIALIZERS ########
class AuthSerializer(serializers.Serializer):
    token = serializers.CharField(required=False, allow_null=False, allow_blank=False)
    code = serializers.CharField(required=False, allow_null=False, allow_blank=False)


class AuthTokenResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    role = serializers.CharField()
    user_id = serializers.IntegerField()
    provider_id = serializers.IntegerField(allow_null=True)
    person_id = serializers.IntegerField(allow_null=True)


class AdminLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()


########## API SERIALIZERS ########
class BaseCreateSerializer(serializers.ModelSerializer):
    class Meta:
        abstract = True


class BaseUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        abstract = True


class BaseRetrieveSerializer(serializers.ModelSerializer):
    class Meta:
        abstract = True
        read_only_fields = "__all__"


# RecurrenceRule
class RecurrenceRuleCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecurrenceRule
        fields = ["frequency_concept", "interval", "weekday_binary", "valid_start_date", "valid_end_date"]


class RecurrenceRuleUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecurrenceRule
        fields = "__all__"


class RecurrenceRuleRetrieveSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecurrenceRule
        fields = "__all__"


# DrugExposure
class DrugExposureCreateSerializer(BaseCreateSerializer):
    recurrence_rule = RecurrenceRuleCreateSerializer(required=False)

    class Meta:
        model = DrugExposure
        exclude = ["drug_exposure_id", "created_at", "updated_at"]

    def create(self, validated_data):
        recurrence_data = validated_data.pop("recurrence_rule", None)

        recurrence_rule = None
        if recurrence_data:
            recurrence_rule, _ = RecurrenceRule.objects.get_or_create(
                frequency_concept_id=recurrence_data["frequency_concept"].concept_id,
                interval=recurrence_data.get("interval"),
                weekday_binary=recurrence_data.get("weekday_binary", None),
            )

        return DrugExposure.objects.create(recurrence_rule=recurrence_rule, **validated_data)


class DrugExposureUpdateSerializer(BaseUpdateSerializer):
    recurrence_rule = RecurrenceRuleUpdateSerializer(required=False)

    class Meta:
        model = DrugExposure
        exclude = ["created_at", "updated_at"]

    def update(self, instance, validated_data):
        recurrence_data = validated_data.pop("recurrence_rule", None)

        if recurrence_data:
            recurrence_rule, _ = RecurrenceRule.objects.get_or_create(
                frequency_concept=recurrence_data["frequency_concept"],
                interval=recurrence_data.get("interval"),
                weekday_binary=recurrence_data.get("weekday_binary", None),
            )
            instance.recurrence_rule = recurrence_rule

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance


class DrugExposureRetrieveSerializer(BaseRetrieveSerializer):
    recurrence_rule = RecurrenceRuleRetrieveSerializer(required=False)

    class Meta:
        model = DrugExposure
        fields = "__all__"


# Observation
class ObservationCreateSerializer(BaseCreateSerializer):
    class Meta:
        model = Observation
        exclude = ["observation_id", "created_at", "updated_at"]


class ObservationUpdateSerializer(BaseUpdateSerializer):
    class Meta:
        model = Observation
        exclude = ["created_at", "updated_at"]


class ObservationRetrieveSerializer(BaseRetrieveSerializer):
    class Meta:
        model = Observation
        fields = "__all__"


# VisitOccurrence
class VisitOccurrenceCreateSerializer(BaseCreateSerializer):
    recurrence_rule = RecurrenceRuleCreateSerializer(required=False)

    class Meta:
        model = VisitOccurrence
        exclude = ["visit_occurrence_id", "created_at", "updated_at"]

    def create(self, validated_data):
        recurrence_data = validated_data.pop("recurrence_rule", None)

        recurrence_rule = None
        if recurrence_data:
            recurrence_rule, _ = RecurrenceRule.objects.get_or_create(
                frequency_concept_id=recurrence_data["frequency_concept"].concept_id,
                interval=recurrence_data.get("interval"),
                weekday_binary=recurrence_data.get("weekday_binary", None),
            )

        return VisitOccurrence.objects.create(recurrence_rule=recurrence_rule, **validated_data)


class VisitOccurrenceUpdateSerializer(BaseUpdateSerializer):
    recurrence_rule = RecurrenceRuleUpdateSerializer(required=False)

    class Meta:
        model = VisitOccurrence
        exclude = ["created_at", "updated_at"]

    def update(self, instance, validated_data):
        recurrence_data = validated_data.pop("recurrence_rule", None)

        if recurrence_data:
            recurrence_rule, _ = RecurrenceRule.objects.get_or_create(
                frequency_concept=recurrence_data["frequency_concept"],
                interval=recurrence_data.get("interval"),
                weekday_binary=recurrence_data.get("weekday_binary", None),
            )
            instance.recurrence_rule = recurrence_rule

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance


class VisitOccurrenceRetrieveSerializer(BaseRetrieveSerializer):
    recurrence_rule = RecurrenceRuleRetrieveSerializer(required=False)

    class Meta:
        model = VisitOccurrence
        fields = "__all__"


# Measurement
class MeasurementCreateSerializer(BaseCreateSerializer):
    class Meta:
        model = Measurement
        exclude = ["measurement_id", "created_at", "updated_at"]


class MeasurementUpdateSerializer(BaseUpdateSerializer):
    class Meta:
        model = Measurement
        exclude = ["created_at", "updated_at"]


class MeasurementRetrieveSerializer(BaseRetrieveSerializer):
    class Meta:
        model = Measurement
        fields = "__all__"


# Vocabulary
class VocabularyCreateSerializer(BaseCreateSerializer):
    class Meta:
        model = Vocabulary
        exclude = ["vocabulary_id", "created_at", "updated_at"]


class VocabularyUpdateSerializer(BaseUpdateSerializer):
    class Meta:
        model = Vocabulary
        exclude = ["created_at", "updated_at"]


class VocabularyRetrieveSerializer(BaseRetrieveSerializer):
    class Meta:
        model = Vocabulary
        fields = "__all__"


# ConceptClass
class ConceptClassCreateSerializer(BaseCreateSerializer):
    class Meta:
        model = ConceptClass
        exclude = ["concept_class_id", "created_at", "updated_at"]


class ConceptClassUpdateSerializer(BaseUpdateSerializer):
    class Meta:
        model = ConceptClass
        exclude = ["created_at", "updated_at"]


class ConceptClassRetrieveSerializer(BaseRetrieveSerializer):
    class Meta:
        model = ConceptClass
        fields = "__all__"


# Concept
class ConceptCreateSerializer(BaseCreateSerializer):
    class Meta:
        model = Concept
        exclude = ["concept_id", "created_at", "updated_at"]


class ConceptUpdateSerializer(BaseUpdateSerializer):
    class Meta:
        model = Concept
        exclude = ["created_at", "updated_at"]


class ConceptRelatedSerializer(BaseRetrieveSerializer):
    translated_name = serializers.SerializerMethodField()

    class Meta:
        model = Concept
        fields = [
            "concept_id",
            "concept_name",
            "concept_class",
            "vocabulary",
            "domain",
            "concept_code",
            "translated_name",
        ]

    def get_translated_name(self, obj):
        if hasattr(obj, "translated_synonyms") and obj.translated_synonyms:
            return obj.translated_synonyms[0].concept_synonym_name
        return obj.concept_name


class ConceptRetrieveSerializer(BaseRetrieveSerializer):
    translated_name = serializers.SerializerMethodField()
    related_concept = serializers.SerializerMethodField()

    class Meta:
        model = Concept
        fields = [
            "concept_id",
            "concept_name",
            "translated_name",
            "concept_class",
            "vocabulary",
            "domain",
            "concept_code",
            "related_concept",
        ]

    def get_translated_name(self, obj):
        if hasattr(obj, "translated_synonyms") and obj.translated_synonyms:
            return obj.translated_synonyms[0].concept_synonym_name
        return obj.concept_name

    @extend_schema_field(ConceptRelatedSerializer)
    def get_related_concept(self, obj):
        relationship_id = self.context.get("relationship_id")
        lang = self.context.get("lang")

        if not relationship_id or not lang:
            return None

        rel = (
            ConceptRelationship.objects.select_related("concept_2")
            .prefetch_related(
                Prefetch(
                    "concept_2__concept_synonym_concept_set",
                    queryset=ConceptSynonym.objects.filter(language_concept__concept_code=lang),
                    to_attr="translated_synonyms",
                )
            )
            .filter(relationship_id=relationship_id)
            .first()
        )

        if rel:
            return ConceptRetrieveSerializer(rel.concept_2, context=self.context).data

        return None


# ConceptSynonym
class ConceptSynonymCreateSerializer(BaseCreateSerializer):
    class Meta:
        model = ConceptSynonym
        exclude = ["id", "created_at", "updated_at"]


class ConceptSynonymUpdateSerializer(BaseUpdateSerializer):
    class Meta:
        model = ConceptSynonym
        exclude = ["created_at", "updated_at"]


class ConceptSynonymRetrieveSerializer(BaseRetrieveSerializer):
    class Meta:
        model = ConceptSynonym
        fields = "__all__"


# Domain
class DomainCreateSerializer(BaseCreateSerializer):
    class Meta:
        model = Domain
        exclude = ["domain_id", "created_at", "updated_at"]


class DomainUpdateSerializer(BaseUpdateSerializer):
    class Meta:
        model = Domain
        exclude = ["created_at", "updated_at"]


class DomainRetrieveSerializer(BaseRetrieveSerializer):
    class Meta:
        model = Domain
        fields = "__all__"


# Location
class LocationCreateSerializer(BaseCreateSerializer):
    class Meta:
        model = Location
        exclude = ["location_id", "created_at", "updated_at"]


class LocationUpdateSerializer(BaseUpdateSerializer):
    class Meta:
        model = Location
        exclude = ["created_at", "updated_at"]


class LocationRetrieveSerializer(BaseRetrieveSerializer):
    class Meta:
        model = Location
        fields = "__all__"


# Person
class PersonCreateSerializer(BaseCreateSerializer):
    class Meta:
        model = Person
        exclude = ["person_id", "created_at", "updated_at", "location", "user"]

    def create(self, validated_data):
        user = self.context.get("request").user
        if not user:
            print("Error: User not found in the request context.")
            raise serializers.ValidationError("User not found in the request context.")

        if Person.objects.filter(user=user).exists():
            print(f"Error: Person with user {user} already exists.")
            raise serializers.ValidationError("A provider with this user already exists.")

        validated_data["user"] = user
        return super().create(validated_data)


class PersonUpdateSerializer(BaseUpdateSerializer):
    class Meta:
        model = Person
        exclude = ["created_at", "updated_at", "user"]


class PersonRetrieveSerializer(BaseRetrieveSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)

    class Meta:
        model = Person
        fields = "__all__"


# Provider
class ProviderCreateSerializer(BaseCreateSerializer):
    class Meta:
        model = Provider
        exclude = ["provider_id", "created_at", "updated_at", "user"]

    def create(self, validated_data):
        user = self.context.get("request").user
        if not user:
            print("Error: User not found in the request context.")
            raise serializers.ValidationError("User not found in the request context.")

        if Provider.objects.filter(user=user).exists():
            print(f"Error: Provider with user {user} already exists.")
            raise serializers.ValidationError("A provider with this user already exists.")

        validated_data["user"] = user
        return super().create(validated_data)


class ProviderUpdateSerializer(BaseUpdateSerializer):
    class Meta:
        model = Provider
        exclude = ["created_at", "updated_at", "user"]


class ProviderRetrieveSerializer(BaseRetrieveSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)

    class Meta:
        model = Provider
        fields = "__all__"


# CareSite
class CareSiteCreateSerializer(BaseCreateSerializer):
    class Meta:
        model = CareSite
        exclude = ["care_site_id", "created_at", "updated_at"]


class CareSiteUpdateSerializer(BaseUpdateSerializer):
    class Meta:
        model = CareSite
        exclude = ["created_at", "updated_at"]


class CareSiteRetrieveSerializer(BaseRetrieveSerializer):
    class Meta:
        model = CareSite
        fields = "__all__"


# FactRelationship
class FactRelationshipCreateSerializer(BaseCreateSerializer):
    class Meta:
        model = FactRelationship
        exclude = ["created_at", "updated_at"]


class FactRelationshipUpdateSerializer(BaseUpdateSerializer):
    class Meta:
        model = FactRelationship
        exclude = ["created_at", "updated_at"]


class FactRelationshipRetrieveSerializer(BaseRetrieveSerializer):
    class Meta:
        model = FactRelationship
        fields = "__all__"


# FullPerson
class FullPersonCreateSerializer(serializers.Serializer):
    person = PersonCreateSerializer()
    location = LocationCreateSerializer()
    observations = ObservationCreateSerializer(many=True)
    drug_exposures = DrugExposureCreateSerializer(many=True)

    def create(self, validated_data):
        person_data = validated_data.pop("person")
        location_data = validated_data.pop("location")
        observations_data = validated_data.pop("observations", [])
        drug_exposures_data = validated_data.pop("drug_exposures", [])

        # Create Location
        location = Location.objects.create(**location_data)

        # Convert concept objects to their IDs for the serializer
        person_data["gender_concept"] = person_data.get("gender_concept").concept_id
        person_data["ethnicity_concept"] = person_data.get("ethnicity_concept").concept_id
        person_data["race_concept"] = person_data.get("race_concept").concept_id

        # Add the Location instance to person_data
        person_data["location"] = location

        # Validate and create the Person
        person_serializer = PersonCreateSerializer(data=person_data, context=self.context)
        person_serializer.is_valid(raise_exception=True)
        person = person_serializer.save()

        # Create Observations and DrugExposures
        for obs in observations_data:
            obs.pop("person", None)  # remove if exists
            Observation.objects.create(person=person, **obs)

        for drug_data in drug_exposures_data:
            drug_data.pop("person", None)  # remove if exists
            DrugExposure.objects.create(person=person, **drug_data)

        return {
            "person": person,
            "location": location,
            "observations": observations_data,
            "drug_exposures": drug_exposures_data,
        }


class FullPersonRetrieveSerializer(serializers.Serializer):
    person = PersonRetrieveSerializer()
    location = LocationRetrieveSerializer()
    observations = ObservationRetrieveSerializer(many=True)
    drug_exposures = DrugExposureRetrieveSerializer(many=True)


class FullProviderCreateSerializer(serializers.Serializer):
    provider = ProviderCreateSerializer()

    def create(self, validated_data):
        provider_data = validated_data.pop("provider")

        # Check if specialty_concept is an object and extract the ID
        specialty_concept = provider_data.get("specialty_concept")
        if isinstance(specialty_concept, Concept):  # Check if it's a Concept model instance
            provider_data["specialty_concept"] = specialty_concept.concept_id

        # Validate and create the provider using ProviderCreateSerializer
        provider_serializer = ProviderCreateSerializer(data=provider_data, context=self.context)
        provider_serializer.is_valid(raise_exception=True)
        provider = provider_serializer.save()

        return {"provider": provider}


class FullProviderRetrieveSerializer(serializers.Serializer):
    provider = ProviderRetrieveSerializer()


class ProviderLinkCodeResponseSerializer(serializers.Serializer):
    code = serializers.CharField(
        max_length=6, help_text="Code generated to link a person to this provider (ex: 'A1B2C3')"
    )


class PersonLinkProviderRequestSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=16, help_text="Link code provided by the provider")


class PersonLinkProviderResponseSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["linked"], help_text="Linking result")
    already_existed = serializers.BooleanField(help_text="Indicates if the relationship already existed")


class PersonProviderUnlinkRequestSerializer(serializers.Serializer):
    pass


class PersonProviderUnlinkResponseSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["unlinked"], help_text="Unlinking result")


class HelpCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Observation
        fields = [
            "provider",
            "value_as_string",
            "shared_with_provider",
        ]


class HelpRetrieveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Observation
        fields = [
            "person",
            "value_as_string",
            "observation_date",
        ]


# Observações específicas (paranoia etc)
def build_observations_from_list(obs_list, now, person, shared_flag):
    obs_instances = []
    for obs in obs_list:
        concept_id = obs["concept_id"]
        value = obs.get("value")

        observation = Observation(
            person=person,
            observation_concept_id=concept_id,
            shared_with_provider=shared_flag,
            observation_date=now,
            observation_type_concept=get_concept_by_code("diary_entry_type"),
        )

        print(f"Processing observation: {obs}")

        if isinstance(value, int) or (isinstance(value, str) and value.isdigit()):
            observation.value_as_string = str(value)
        else:
            observation.value_as_concept = get_concept_by_code(value)

        obs_instances.append(observation)

    return obs_instances


class ProviderPersonSummarySerializer(serializers.Serializer):
    person_id = serializers.IntegerField()
    name = serializers.CharField()
    age = serializers.IntegerField(allow_null=True)
    last_visit_date = serializers.DateTimeField(allow_null=True)
    last_visit_notes = serializers.CharField(allow_null=True, required=False)
    last_help_date = serializers.DateTimeField(allow_null=True)


class HelpCountSerializer(serializers.Serializer):
    help_count = serializers.IntegerField()


class VisitDetailsSerializer(serializers.Serializer):
    person_name = serializers.CharField()
    visit_date = serializers.DateTimeField()


class NextVisitSerializer(serializers.Serializer):
    next_visit = VisitDetailsSerializer(allow_null=True)


class InterestAreaTriggerCreateSerializer(serializers.Serializer):
    observation_concept_id = serializers.IntegerField(required=False, allow_null=True)
    trigger_name = serializers.CharField(required=False, allow_null=True)
    value_as_string = serializers.CharField(required=False, allow_null=True)
    concept_name = serializers.CharField(required=False, allow_null=True)

    def validate(self, data):
        if not data.get("observation_concept_id") and not data.get("trigger_name"):
            raise serializers.ValidationError("You must provide observation_concept_id or trigger_name")
        return data

    def to_representation(self, instance):
        representation = {
            "trigger_name": instance.observation_source_value,
            "trigger_id": instance.observation_id,
            "observation_concept_id": instance.observation_concept_id,
            "value_as_string": instance.value_as_string,
        }

        return representation


class InterestAreaTriggerUpdateSerializer(serializers.Serializer):
    trigger_id = serializers.IntegerField(required=True, help_text="ID of the trigger observation to update")
    value_as_string = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, help_text="New value for the trigger observation"
    )


class InterestAreaSerializer(serializers.Serializer):
    observation_concept_id = serializers.IntegerField(required=False, allow_null=True)
    interest_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    value_as_string = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    triggers = InterestAreaTriggerCreateSerializer(many=True, required=False)

    def validate(self, data):
        if not data.get("observation_concept_id") and not data.get("interest_name"):
            raise serializers.ValidationError("You must provide observation_concept_id or interest_name")
        return data

    def create(self, validated_data):
        user = self.context.get("request").user
        person = get_object_or_404(Person, user=user)

        CUSTOM_INTEREST_ID = get_concept_by_code("CUSTOM_INTEREST").concept_id
        CUSTOM_TRIGGER_ID = get_concept_by_code("CUSTOM_TRIGGER").concept_id

        # Interest Area
        defaults = {
            "observation_date": timezone.now(),
            "observation_concept_id": validated_data.get("observation_concept_id"),
            "observation_type_concept_id": get_concept_by_code("INTEREST_AREA").concept_id,
        }

        filters = {}
        if validated_data.get("observation_concept_id") == CUSTOM_INTEREST_ID:
            filters["observation_source_value"] = validated_data["interest_name"]
        else:
            filters["observation_concept_id"] = validated_data.get("observation_concept_id")
            defaults["observation_source_value"] = (
                ConceptSynonym.objects.filter(
                    concept_id=validated_data.get("observation_concept_id"),
                )
                .first()
                .concept_synonym_name
            )

        interest_area, created = Observation.objects.update_or_create(person=person, **filters, defaults=defaults)

        if created:
            interest_area.value_as_concept = get_concept_by_code("value_no")
            interest_area.shared_with_provider = validated_data.get("shared_with_provider", False)
            interest_area.save()

        # Triggers
        if "triggers" not in validated_data:
            validated_data["triggers"] = []

        if created and validated_data.get("observation_concept_id") != CUSTOM_INTEREST_ID:
            # Search for relationships for this concept
            related_triggers = ConceptRelationship.objects.filter(
                concept_1_id=validated_data["observation_concept_id"], relationship_id="AOI_Trigger"
            )

            # For each related trigger, create a new trigger observation
            for relationship in related_triggers:
                trigger_concept_id = relationship.concept_2_id

                validated_data["triggers"].append(
                    {"observation_concept_id": trigger_concept_id, "trigger_name": None, "value_as_string": None}
                )

        # Get all current triggers for this interest area
        current_relationships = FactRelationship.objects.filter(
            domain_concept_1_id=get_concept_by_code("INTEREST_AREA").concept_id,
            fact_id_1=interest_area.observation_id,
            relationship_concept_id=get_concept_by_code("AOI_TRIGGER").concept_id,
        )

        # Get all trigger observation IDs
        trigger_ids = current_relationships.values_list("fact_id_2", flat=True)

        # Fetch all trigger observations
        trigger_observations = Observation.objects.filter(observation_id__in=trigger_ids)

        # Create a mapping of existing triggers
        existing_triggers = {}
        for trigger in trigger_observations:
            key = (trigger.observation_concept_id, trigger.observation_source_value)
            existing_triggers[key] = trigger

        # Process new triggers
        for trigger_data in validated_data.get("triggers"):

            key = (
                trigger_data.get("observation_concept_id"),
                trigger_data.get("trigger_name"),
            )

            # Check if we already have this trigger for this interest area
            if key in existing_triggers:
                # Update existing trigger
                trigger = existing_triggers[key]
                trigger.observation_date = timezone.now()
                trigger.save()
                # Remove from dict so we know it's been processed
                del existing_triggers[key]
            else:
                # Create new trigger
                trigger_kwargs = {
                    "person": person,
                    "observation_date": timezone.now(),
                    "observation_type_concept_id": get_concept_by_code("TRIGGER").concept_id,
                    "observation_concept_id": trigger_data.get("observation_concept_id"),
                }

                specific_kwargs = {}
                if trigger_data.get("observation_concept_id") == CUSTOM_TRIGGER_ID:
                    specific_kwargs = {
                        "observation_source_value": trigger_data["trigger_name"],
                    }
                else:
                    specific_kwargs = {
                        "observation_source_value": (
                            ConceptSynonym.objects.filter(
                                concept_id=trigger_data.get("observation_concept_id"),
                            )
                            .first()
                            .concept_synonym_name
                        ),
                    }

                trigger = Observation.objects.create(**trigger_kwargs, **specific_kwargs)

                # Create relationship
                FactRelationship.objects.create(
                    domain_concept_1_id=get_concept_by_code("INTEREST_AREA").concept_id,
                    fact_id_1=interest_area.observation_id,
                    domain_concept_2_id=get_concept_by_code("TRIGGER").concept_id,
                    fact_id_2=trigger.observation_id,
                    relationship_concept_id=get_concept_by_code("AOI_TRIGGER").concept_id,
                )

        # Delete any remaining triggers that weren't in the new data
        # No crowd sourcing
        for trigger in existing_triggers.values():
            FactRelationship.objects.filter(
                domain_concept_2_id=get_concept_by_code("TRIGGER").concept_id,
                fact_id_2=trigger.observation_id,
                fact_id_1=interest_area.observation_id,
            ).delete()
            trigger.delete()

        return interest_area

    def delete(self, validated_data):
        """
        Deletes an interest area and its relationships with triggers
        """
        relationships = FactRelationship.objects.filter(
            domain_concept_1_id=get_concept_by_code("INTEREST_AREA").concept_id,
            fact_id_1=validated_data.observation_id,
            relationship_concept_id=get_concept_by_code("AOI_TRIGGER").concept_id,
        )

        trigger_ids = relationships.values_list("fact_id_2", flat=True)

        relationships.delete()

        for trigger_id in trigger_ids:
            if not FactRelationship.objects.filter(
                domain_concept_2_id=get_concept_by_code("TRIGGER").concept_id, fact_id_2=trigger_id
            ).exists():
                Observation.objects.filter(observation_id=trigger_id).delete()

        validated_data.delete()

        return True

    def update(self, validated_data):
        user = self.context.get("request").user
        person = get_object_or_404(Person, user=user)
        for data in validated_data:

            interest_id = data.get("interest_area_id")
            interest_value = data.get("value_as_string")

            if interest_id and interest_value:
                try:
                    interest = Observation.objects.get(
                        observation_id=interest_id,
                        person=person,
                    )
                    interest.value_as_string = interest_value
                    interest.observation_date = timezone.now()
                    interest.shared_with_provider = data.get("shared_with_provider")
                    interest.save()
                except Observation.DoesNotExist:
                    continue

            # Update triggers
            for trigger in data.get("triggers", []):
                trigger_id = trigger.get("trigger_id")
                trigger_value = trigger.get("value_as_string")

                if trigger_id and trigger_value:
                    try:
                        trigger = Observation.objects.get(
                            observation_id=trigger_id,
                            person=person,
                        )
                        trigger.value_as_string = trigger_value
                        trigger.observation_date = timezone.now()
                        trigger.save()
                    except (FactRelationship.DoesNotExist, Observation.DoesNotExist):
                        continue

        return {"updated": True, "message": "Interest areas and triggers updated successfully"}

    def to_representation(self, instance):
        """Enhance the interest area representation with concept names"""
        representation = {
            "interest_name": instance.observation_source_value,
            "interest_area_id": instance.observation_id,
            "observation_concept_id": instance.observation_concept_id,
            "value_as_string": instance.value_as_string,
            "value_as_concept": instance.value_as_concept.concept_id,
            "shared_with_provider": instance.shared_with_provider,
        }

        return representation


class InterestAreaUpdateSerializer(serializers.Serializer):
    interest_area_id = serializers.IntegerField(
        required=True, help_text="ID of the interest area observation to update"
    )
    value_as_string = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, help_text="New value for the interest area observation"
    )
    shared_with_provider = serializers.BooleanField(
        required=False, default=False, help_text="Indicates if the interest area should be shared with the provider"
    )
    triggers = InterestAreaTriggerUpdateSerializer(
        many=True, required=False, help_text="List of triggers to update within this interest area"
    )


class InterestAreaBulkUpdateSerializer(serializers.Serializer):
    interest_areas = InterestAreaUpdateSerializer(
        many=True, required=True, help_text="List of interest areas to update"
    )

    def validate(self, data):
        if not data.get("interest_areas"):
            raise serializers.ValidationError("At least one interest area must be provided")
        return data

    def create(self, validated_data):
        interest_area_serializer = InterestAreaSerializer(context=self.context)
        result = interest_area_serializer.update(validated_data["interest_areas"])
        return result

    def update(self, instance, validated_data):
        interest_area_serializer = InterestAreaSerializer(context=self.context)
        result = interest_area_serializer.update(validated_data["interest_areas"])
        return result


class DiaryCreateSerializer(serializers.Serializer):
    date_range_type = serializers.ChoiceField(choices=["today", "since_last"])
    text = serializers.CharField(allow_blank=True)
    text_shared = serializers.BooleanField()
    interest_areas = InterestAreaUpdateSerializer(many=True, required=False, allow_empty=True)

    def create(self, validated_data):
        user = self.context["request"].user
        person = Person.objects.get(user=user)
        now = timezone.now()

        # 1. Observation "mother"
        diary_entry = Observation.objects.create(
            person=person,
            observation_concept=get_concept_by_code("diary_entry"),
            value_as_string=validated_data["date_range_type"],
            observation_date=now,
            shared_with_provider=True,
            observation_type_concept=get_concept_by_code("diary_entry_type"),
        )

        # 2. Observations of the diary
        observations = []

        # Free text
        if validated_data["text"]:
            observations.append(
                Observation(
                    person=person,
                    observation_concept=get_concept_by_code("diary_text"),
                    value_as_string=validated_data["text"],
                    shared_with_provider=validated_data["text_shared"],
                    observation_date=now,
                    observation_type_concept=get_concept_by_code("diary_entry_type"),
                )
            )

        # 3. Process interest areas
        interest_areas_updated = []
        for interest_area_data in validated_data.get("interest_areas", []):
            interest_id = interest_area_data.get("interest_area_id")
            if interest_id:
                try:
                    # Find the interest area observation
                    interest_area = Observation.objects.get(
                        observation_id=interest_id,
                        person=person,
                    )

                    # Update values
                    if "value_as_string" in interest_area_data:
                        interest_area.value_as_string = interest_area_data["value_as_string"]

                    # Update sharing preference
                    if "shared_with_provider" in interest_area_data:
                        interest_area.shared_with_provider = interest_area_data["shared_with_provider"]

                    interest_area.observation_date = now
                    interest_area.save()

                    # Add to updated list
                    interest_areas_updated.append(interest_id)

                    # Process triggers if present
                    for trigger_data in interest_area_data.get("triggers", []):
                        trigger_id = trigger_data.get("trigger_id")
                        if trigger_id and "value_as_string" in trigger_data:
                            try:
                                trigger = Observation.objects.get(
                                    observation_id=trigger_id,
                                    person=person,
                                )
                                trigger.value_as_string = trigger_data["value_as_string"]
                                trigger.observation_date = now
                                trigger.save()
                            except Observation.DoesNotExist:
                                continue

                except Observation.DoesNotExist:
                    continue

        # Create all the observations
        Observation.objects.bulk_create(observations)

        return {
            "diary_id": diary_entry.observation_id,
            "created": True,
            "interest_areas_updated": interest_areas_updated,
        }

    def delete(self, diary_id):
        # Get the user from context
        user = self.context.get("request").user
        person = get_object_or_404(Person, user=user)

        # Find the diary
        diary = get_object_or_404(
            Observation,
            observation_id=diary_id,
            person=person,
            observation_concept_id=get_concept_by_code("diary_entry").concept_id,
        )

        # Find all relationships where this diary is the parent
        diary_relationships = FactRelationship.objects.filter(
            domain_concept_1_id=get_concept_by_code("diary_entry").concept_id, fact_id_1=diary.observation_id
        )

        # Find all related observations (text entries, etc.)
        related_observations = Observation.objects.filter(
            person=person,
            observation_date=diary.observation_date,
            observation_type_concept_id=get_concept_by_code("diary_entry_type").concept_id,
        ).exclude(observation_id=diary.observation_id)

        # Delete in order: relationships first, then related observations, then the diary itself
        diary_relationships.delete()
        related_observations.delete()
        diary.delete()

        return {"deleted": True, "diary_id": diary_id}


class UserRetrieveSerializer(BaseRetrieveSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "is_active", "is_staff", "date_joined"]
        read_only_fields = fields


class UserDeleteSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(help_text="ID of the user to be deleted")

    def validate_user_id(self, value):
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError("User not found.")
        return value


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(help_text="Refresh token for logout")

    def validate_refresh(self, value):
        if not value:
            raise serializers.ValidationError("The refresh token is required.")
        return value


class MarkAttentionPointSerializer(serializers.Serializer):
    observation_id = serializers.IntegerField(help_text="ID of the observation to be marked as an attention point")
    is_attention_point = serializers.BooleanField(
        help_text="Indicates whether the observation should be marked as an attention point"
    )


class AccountRetrieveSerializer(serializers.Serializer):
    pass


class AccountDeleteSerializer(serializers.Serializer):
    pass
