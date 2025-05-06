from rest_framework import serializers

from .models import *


class AuthSerializer(serializers.Serializer):
    code = serializers.CharField(required=True, allow_null=False, allow_blank=False)


class AuthTokenResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    role = serializers.CharField()


class AdminLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()


class VocabularySerializer(serializers.ModelSerializer):
    class Meta:
        model = Vocabulary
        fields = "__all__"
        read_only_fields = ("vocabulary_id", "created_at", "updated_at")


class ConceptClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConceptClass
        fields = "__all__"
        read_only_fields = ("concept_class_id", "created_at", "updated_at")


class ConceptSerializer(serializers.ModelSerializer):
    translated_name = serializers.SerializerMethodField()

    class Meta:
        model = Concept
        fields = ["concept_id", "concept_name", "translated_name", "concept_class_id", "domain_id", "concept_code"]
        read_only_fields = ("created_at", "updated_at")

    def get_translated_name(self, obj):
        if hasattr(obj, "translated_synonyms") and obj.translated_synonyms:
            return obj.translated_synonyms[0].concept_synonym_name
        return obj.concept_name


class ConceptSynonymSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConceptSynonym
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at")


class DomainSerializer(serializers.ModelSerializer):
    class Meta:
        model = Domain
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at")


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at")


class PersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Person
        exclude = ["user"]
        read_only_fields = ("created_at", "updated_at")

    def create(self, validated_data):
        request = self.context.get("request", None)
        if request and request.user and request.user.is_authenticated: # dummy for testing
            validated_data["user"] = request.user
        return super().create(validated_data)


class ProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Provider
        exclude = ["user"]
        read_only_fields = ("created_at", "updated_at")

    def create(self, validated_data):
        request = self.context.get("request", None)
        if request and request.user and request.user.is_authenticated: # dummy for testing
            validated_data["user"] = request.user
        return super().create(validated_data)


class CareSiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CareSite
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at")


class DrugExposureSerializer(serializers.ModelSerializer):
    class Meta:
        model = DrugExposure
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at")


class ObservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Observation
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at")


class VisitOccurrenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisitOccurrence
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at")


class MeasurementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Measurement
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at")


class FactRelationshipSerializer(serializers.ModelSerializer):
    class Meta:
        model = FactRelationship
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at")


#### Increasing Complexity ###
