from rest_framework import serializers
from .models import Person, Provider, LinkedProvider

class AuthSerializer(serializers.Serializer):
    code = serializers.CharField(required=True, allow_null=False, allow_blank=False)

class PersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Person
        exclude = ['user'] 

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class ProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Provider
        exclude = ['user']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class LinkedProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = LinkedProvider
        fields = '__all__'