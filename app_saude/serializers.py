import json
import logging
import re

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import *
from .utils.concept import get_concept_by_code

User = get_user_model()

logger = logging.getLogger("app_saude")


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
    full_name = serializers.CharField(
        help_text="Full name of the user.",
    )
    email = serializers.EmailField(help_text="Email address of the user.")
    social_name = serializers.CharField()
    profile_picture = serializers.CharField(
        help_text="URL of the user's profile picture.",
        allow_blank=True,
        allow_null=True,
    )
    use_dark_mode = serializers.BooleanField(
        help_text="Indicates if the user prefers dark mode.",
        default=False,
    )


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
        exclude = ["concept_synonym_id", "created_at", "updated_at"]


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
            logger.warning("Error: User not found in the request context.")
            raise serializers.ValidationError("User not found in the request context.")

        if Person.objects.filter(user=user).exists():
            logger.warning(f"Error: Person with user {user} already exists.")
            raise serializers.ValidationError("A person with this user already exists.")

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
        if not user or not user.is_authenticated:
            raise serializers.ValidationError({"user": "User not authenticated."})

        if Provider.objects.filter(user=user).exists():
            raise serializers.ValidationError({"user": "This user is already linked to a provider."})

        registration = validated_data.get("professional_registration")
        if Provider.objects.filter(professional_registration=registration, user__is_active=True).exists():
            raise serializers.ValidationError(
                {"professional_registration": "A provider with this professional registration already exists."}
            )

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

        # Convert concept objects to their IDs for the serializer
        person_data["gender_concept_id"] = person_data.pop("gender_concept")
        person_data["ethnicity_concept_id"] = person_data.pop("ethnicity_concept")
        person_data["race_concept_id"] = person_data.pop("race_concept")

        with transaction.atomic():
            # 1. Create Location
            location = Location.objects.create(**location_data)

            # Add the Location instance to person_data
            person_data["location"] = location

            # 2. Create Person
            person_serializer = PersonCreateSerializer(data=person_data, context=self.context)
            person_serializer.is_valid(raise_exception=True)
            person = person_serializer.create(person_data)

            # 3. Create Observations
            for obs in observations_data:
                obs.pop("person", None)  # remove if exists
                Observation.objects.create(person=person, **obs)

            # 4. Create Drug Exposures
            for drug in drug_exposures_data:
                drug.pop("person", None)  # remove if exists
                DrugExposure.objects.create(person=person, **drug)

            return {
                "person": person,
                "location": location,
                "observations": observations_data,
                "drug_exposures": drug_exposures_data,
            }

        raise serializers.ValidationError("Failed to create FullPerson due to an error in the transaction.")


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
        try:
            provider_serializer = ProviderCreateSerializer(data=provider_data, context=self.context)
            provider_serializer.is_valid(raise_exception=True)
            provider = provider_serializer.save()
            return {"provider": provider}
        except serializers.ValidationError as e:
            logger.warning("Provider validation error", extra={"errors": provider_serializer.errors})
            raise


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


class InterestAreaTriggerSerializer(serializers.Serializer):
    name = serializers.CharField()
    type = serializers.ChoiceField(choices=["boolean", "text", "int", "scale"], default="boolean")
    response = serializers.CharField(allow_null=True, allow_blank=True)


class InterestAreaSerializer(serializers.Serializer):
    name = serializers.CharField(required=True)
    marked_by = serializers.ListField(child=serializers.CharField(), required=False, default=[])
    shared_with_provider = serializers.BooleanField(required=False, default=False)
    triggers = InterestAreaTriggerSerializer(many=True, required=False, allow_empty=True)


class InterestAreaCreateSerializer(serializers.Serializer):
    interest_area = InterestAreaSerializer()

    def create(self, validated_data):
        try:
            user = self.context.get("request").user
            person = get_object_or_404(Person, user=user)

            # Check if the interest area already exists for the person
            interest_name = validated_data["interest_area"].get("name")
            existing = Observation.objects.filter(
                person=person,
                observation_concept=get_concept_by_code("INTEREST_AREA"),
                value_as_string__icontains=f'"name": "{interest_name}"',
            ).exists()
            if existing:
                raise serializers.ValidationError({"interest_area": "An interest area with this name already exists."})

            interest_area_observation = Observation.objects.create(
                person=person,
                observation_concept=get_concept_by_code("INTEREST_AREA"),
                value_as_string=json.dumps(validated_data["interest_area"], ensure_ascii=False),
                observation_date=timezone.now(),
            )
            return interest_area_observation

        except serializers.ValidationError:
            raise
        except Exception:
            raise serializers.ValidationError({"error": "An unexpected error occurred while processing your request."})


class InterestAreaRetrieveSerializer(serializers.Serializer):
    def to_representation(self, validated_data):
        try:
            interest_area_data = json.loads(validated_data.value_as_string)

            return {
                "observation_id": validated_data.observation_id,
                "person_id": validated_data.person_id,
                "interest_area": interest_area_data,
            }

        except Exception as e:
            raise serializers.ValidationError(f"Error retrieving interest area: {str(e)}")


class InterestAreaUpdateSerializer(serializers.Serializer):
    interest_area = InterestAreaSerializer()

    def update(self, instance, validated_data):
        try:
            updated_interest_area = validated_data.get("interest_area", {})
            instance.value_as_string = json.dumps(updated_interest_area, ensure_ascii=False)
            instance.observation_date = timezone.now()
            instance.save()

            return instance
        except Exception as e:
            raise serializers.ValidationError(f"Error updating interest area: {str(e)}")


class DiaryCreateSerializer(serializers.Serializer):
    date_range_type = serializers.ChoiceField(choices=["today", "since_last"])
    text = serializers.CharField(allow_blank=True)
    text_shared = serializers.BooleanField()
    diary_shared = serializers.BooleanField()
    interest_areas = InterestAreaSerializer(many=True, required=False, allow_empty=True)

    def create(self, validated_data):
        user = self.context["request"].user
        person = Person.objects.get(user=user)
        now = timezone.now()
        logger.info(f"Validated Data in serializers: {validated_data}")

        diary_payload = {
            "date_range_type": validated_data["date_range_type"],
            "text": validated_data["text"],
            "text_shared": validated_data["text_shared"],
            "diary_shared": validated_data["diary_shared"],
            "interest_areas": validated_data.get("interest_areas", []),
        }

        diary_entry = Observation.objects.create(
            person=person,
            observation_concept=get_concept_by_code("diary_entry"),
            value_as_string=json.dumps(diary_payload, ensure_ascii=False),
            observation_date=now,
            shared_with_provider=validated_data["diary_shared"],
            observation_type_concept=get_concept_by_code("diary_entry_type"),
        )

        return {
            "diary_id": diary_entry.observation_id,
            "created": True,
        }


class DiaryDeleteSerializer(serializers.Serializer):
    diary_id = serializers.IntegerField(help_text="ID of the diary to be deleted")

    def delete(self, validated_data):
        diary_id = validated_data.get("diary_id")

        diary = get_object_or_404(
            Observation,
            observation_id=diary_id,
            observation_concept_id=get_concept_by_code("diary_entry").concept_id,
        )

        diary.delete()

        return {"deleted": True, "diary_id": diary_id}


class DiaryRetrieveSerializer(serializers.Serializer):
    diary_id = serializers.IntegerField(source="observation_id")
    date = serializers.DateTimeField(source="observation_date")
    entries = serializers.SerializerMethodField()
    interest_areas = serializers.SerializerMethodField()

    def _load_json(self, diary):
        try:
            return json.loads(diary.value_as_string)
        except Exception:
            return {}

    def get_entries(self, diary):
        data = self._load_json(diary)
        return [
            {
                "text": data.get("text", ""),
                "text_shared": data.get("text_shared", False),
            }
        ]

    def get_interest_areas(self, diary):
        data = self._load_json(diary)
        interest_areas = data.get("interest_areas", [])
        person_id = self.context.get("person_id")

        for i, area in enumerate(interest_areas):
            interest_area = Observation.objects.filter(
                person_id=person_id,
                observation_concept=get_concept_by_code("INTEREST_AREA"),
                value_as_string__regex=rf'"name":\s*"{re.escape(area["name"])}"',
            ).first()
            if interest_area:
                interest_area_data = json.loads(interest_area.value_as_string)
                interest_areas[i]["observation_id"] = interest_area.observation_id
                interest_areas[i]["marked_by"] = interest_area_data.get("marked_by", [])
            else:
                interest_areas[i]["observation_id"] = None
                interest_areas[i]["marked_by"] = []
        return interest_areas


class UserRetrieveSerializer(BaseRetrieveSerializer):
    role = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "full_name",
            "first_name",
            "last_name",
            "is_active",
            "role",
            "is_staff",
            "date_joined",
        ]
        read_only_fields = fields

    def get_role(self, obj):
        if obj.is_staff:
            return "admin"
        elif Person.objects.filter(user=obj).exists():
            return "person"
        elif Provider.objects.filter(user=obj).exists():
            return "provider"
        return "unknown"

    def get_full_name(self, obj):
        role = self.get_role(obj)
        if role in ["person", "provider"]:
            if hasattr(obj, "social_name") and obj.social_name:
                return obj.social_name
            else:
                return f"{obj.first_name} {obj.last_name}".strip()
        return None


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
    area_id = serializers.IntegerField(help_text="ID of the interest area to be marked as an attention point")
    is_attention_point = serializers.BooleanField(
        help_text="Indicates whether the interest area should be marked as an attention point"
    )


class AccountRetrieveSerializer(serializers.Serializer):
    pass


class AccountDeleteSerializer(serializers.Serializer):
    pass
