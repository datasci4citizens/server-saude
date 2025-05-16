from django.utils import timezone
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import *
from .utils.concept import get_concept_by_code


######## AUTH SERIALIZERS ########
class AuthSerializer(serializers.Serializer):
    code = serializers.CharField(required=True, allow_null=False, allow_blank=False)


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

    @extend_schema_field(ConceptRelatedSerializer(many=False))
    def get_related_concept(self, obj):
        related_concept = obj.related_concept.all()
        if related_concept:
            return ConceptRelatedSerializer(related_concept, many=False).data
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
            print(f"Error: Provider with user {user} already exists.")
            raise serializers.ValidationError("A provider with this user already exists.")

        validated_data["user"] = user
        return super().create(validated_data)


class PersonUpdateSerializer(BaseUpdateSerializer):
    class Meta:
        model = Person
        exclude = ["created_at", "updated_at", "user"]


class PersonRetrieveSerializer(BaseRetrieveSerializer):
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

        # Cria Location
        location = Location.objects.create(**location_data)

        # Converte os conceitos em int para o Serializer
        person_data["gender_concept"] = person_data.get("gender_concept").concept_id
        person_data["ethnicity_concept"] = person_data.get("ethnicity_concept").concept_id
        person_data["race_concept"] = person_data.get("race_concept").concept_id

        # Adiciona a instância de Location ao person_data
        person_data["location"] = location

        # Valida e cria o Person
        person_serializer = PersonCreateSerializer(data=person_data, context=self.context)
        person_serializer.is_valid(raise_exception=True)
        person = person_serializer.save()

        # Cria Observations e DrugExposures
        for obs in observations_data:
            obs.pop("person", None)  # remove se existir
            Observation.objects.create(person=person, **obs)

        for drug_data in drug_exposures_data:
            drug_data.pop("person", None)  # remove se existir
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

        # Verifica se specialty_concept é um objeto e extrai o ID
        specialty_concept = provider_data.get("specialty_concept")
        if isinstance(specialty_concept, Concept):  # Verifica se é uma instância do modelo Concept
            provider_data["specialty_concept"] = specialty_concept.concept_id

        # Valida e cria o provider usando o ProviderCreateSerializer
        provider_serializer = ProviderCreateSerializer(data=provider_data, context=self.context)
        provider_serializer.is_valid(raise_exception=True)
        provider = provider_serializer.save()

        return {"provider": provider}


class FullProviderRetrieveSerializer(serializers.Serializer):
    provider = ProviderRetrieveSerializer()


class ProviderLinkCodeResponseSerializer(serializers.Serializer):
    code = serializers.CharField(
        max_length=6, help_text="Código gerado para vincular uma pessoa a este provider (ex: 'A1B2C3')"
    )


class PersonLinkProviderRequestSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=16, help_text="Código de vínculo fornecido pelo provider")


class PersonLinkProviderResponseSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["linked"], help_text="Resultado do vínculo")
    already_existed = serializers.BooleanField(help_text="Indica se o relacionamento já existia antes")


class EmergencyCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Observation
        fields = [
            "provider",
            "value_as_string",
            "shared_with_provider",
        ]


class EmergencyRetrieveSerializer(serializers.ModelSerializer):
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
        concept = get_concept_by_code(obs["concept_id"])
        value = obs.get("value")

        observation = Observation(
            person=person,
            observation_concept=concept,
            shared_with_provider=shared_flag,
            observation_date=now,
            observation_type_concept=get_concept_by_code("diary_entry_type"),
        )

        if isinstance(value, int) or (isinstance(value, str) and value.isdigit()):
            observation.value_as_string = str(value)
        else:
            observation.value_as_concept = Concept.objects.get(pk=value)

        obs_instances.append(observation)

    return obs_instances


class DiaryCreateSerializer(serializers.Serializer):
    date_range_type = serializers.ChoiceField(choices=["today", "since_last"])
    text = serializers.CharField(allow_blank=True)
    text_shared = serializers.BooleanField()
    habits_shared = serializers.BooleanField()
    wellness_shared = serializers.BooleanField()
    habits = serializers.ListField(
        child=serializers.DictField(), default=list  # cada item: {"concept_id": X, "value": Y}
    )
    wellness = serializers.ListField(
        child=serializers.DictField(), default=list  # cada item: {"concept_id": X, "value": Y}
    )

    def create(self, validated_data):
        user = self.context["request"].user
        person = Person.objects.get(user=user)
        now = timezone.now()

        # 1. Observation "mãe"
        diary_entry = Observation.objects.create(
            person=person,
            observation_concept=get_concept_by_code("diary_entry"),
            value_as_string=validated_data["date_range_type"],
            observation_date=now,
            shared_with_provider=False,
            observation_type_concept=get_concept_by_code("diary_entry_type"),
        )

        # 2. Observações do diário
        observations = []

        # Texto livre
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

        habits = validated_data.get("habits", [])
        habits_shared = validated_data.get("habits_shared", False)
        wellness = validated_data.get("wellness", [])
        wellness_shared = validated_data.get("wellness_shared", False)

        # Habits
        observations.extend(build_observations_from_list(habits, now, person, habits_shared))
        # Wellness
        observations.extend(build_observations_from_list(wellness, now, person, wellness_shared))

        Observation.objects.bulk_create(observations)

        return {"diary_id": diary_entry.observation_id, "created": True}
