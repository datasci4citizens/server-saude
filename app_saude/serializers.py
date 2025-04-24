from rest_framework import serializers

from .models import *


class AuthSerializer(serializers.Serializer):
    code = serializers.CharField(required=True, allow_null=False, allow_blank=False)


class PersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Person
        exclude = ["user"]

    def create(self, validated_data):
        print("validated_data:", validated_data)
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class ProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Provider
        exclude = ["user"]

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class LinkedProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = LinkedProvider
        fields = "__all__"


class ConceptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Concept
        fields = ["concept_id", "concept_name"]


class DomainSerializer(serializers.ModelSerializer):
    concepts = serializers.SerializerMethodField()

    class Meta:
        model = Domain
        fields = ["domain_name", "concepts"]

    def get_concepts(self, obj):
        concepts = Concept.objects.filter(domain=obj)
        return ConceptSerializer(concepts, many=True).data
