import logging

from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from app_saude.serializers import AuthSerializer
from libs.google import google_get_user_data

from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from .models import Person, Provider
from .serializers import PersonSerializer, ProviderSerializer

User = get_user_model()
logger = logging.getLogger(__name__)

# Just a test endpoint to check if the user is logged in and return user info
class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
            }
        )

class GoogleLoginView(APIView):
    serializer_class = AuthSerializer

    def post(self, request, *args, **kwargs):
        auth_serializer = self.serializer_class(data=request.data)
        auth_serializer.is_valid(raise_exception=True)

        validated_data = auth_serializer.validated_data

        # get user data from google
        user_data = google_get_user_data(validated_data)

        # Creates user in DB if first time login
        user, _ = User.objects.get_or_create(
            email=user_data.get("email"),
            username=user_data.get("email"),
            first_name=user_data.get("given_name"),
            last_name=user_data.get("given_name"),
        )

        role = 'none'
        if Provider.objects.filter(user=user).exists():
            role = 'provider'
        elif Person.objects.filter(user=user).exists():
            role = 'person'

        # generate jwt token for the user
        token = RefreshToken.for_user(user)
        response = {
            "access": str(token.access_token),
            "refresh": str(token),
            "role": role
        }

        return Response(response, status=200)
    
class PersonViewSet(viewsets.ModelViewSet):
    queryset = Person.objects.all()
    serializer_class = PersonSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
         return Person.objects.filter(user=self.request.user)
    
    def create(self, request, *args, **kwargs):
        if Person.objects.filter(user=request.user).exists():
            raise ValidationError("You already have a person registration.")
        return super().create(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        raise PermissionDenied("DELETE not allowed.")

class ProviderViewSet(viewsets.ModelViewSet):
    queryset = Provider.objects.all()
    serializer_class = ProviderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
         return Person.objects.filter(user=self.request.user)
    
    def create(self, request, *args, **kwargs):
        if Person.objects.filter(user=request.user).exists():
            raise ValidationError("You already have a provider registration.")
        return super().create(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        raise PermissionDenied("DELETE not allowed.")

