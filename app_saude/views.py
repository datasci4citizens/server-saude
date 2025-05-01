import logging

from django.contrib.auth import authenticate, get_user_model
from drf_spectacular.utils import extend_schema
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from app_saude.serializers import AuthSerializer
from libs.google import google_get_user_data

from .models import *
from .serializers import *

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
    permission_classes = [AllowAny]

    @extend_schema(request=AuthSerializer, responses={200: AuthTokenResponseSerializer})
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

        role = "none"
        if Provider.objects.filter(user=user).exists():
            role = "provider"
        elif Person.objects.filter(user=user).exists():
            role = "person"

        # generate jwt token for the user
        token = RefreshToken.for_user(user)
        response = {
            "access": str(token.access_token),
            "refresh": str(token),
            "role": role,
        }

        return Response(response, status=200)


class AdminLoginView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(request_body=AdminLoginSerializer)
    def post(self, request, *args, **kwargs):
        username = request.data.get("username")
        password = request.data.get("password")

        user = authenticate(username=username, password=password)

        if not user:
            return Response(
                {"detail": "Invalid credentials."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.is_staff:
            return Response(
                {"detail": "You do not have permission to access this endpoint."},
                status=status.HTTP_403_FORBIDDEN,
            )

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "user_id": user.id,
                "username": user.username,
            }
        )


class UserRole:
    def get_role(self, request):
        role = "none"
        if Provider.objects.filter(user=request.user).exists():
            role = "provider"
        elif Person.objects.filter(user=request.user).exists():
            role = "person"
        return role


@extend_schema(tags=["Person"])
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
        if Person.objects.filter(user=request.user).exists():
            if request.user == self.get_object().user:
                # Delete the user and their related Person object
                return super().destroy(request, *args, **kwargs)
            else:
                # If not, raise a permission denied error
                raise PermissionDenied("You can only delete your own account.")


@extend_schema(tags=["Provider"])
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


class IsProviderOrAdmin(BasePermission):
    def has_permission(self, request, view):
        role = UserRole().get_role(request)
        return role == "provider" or request.user.is_staff


class LinkPersonToProviderView(APIView):
    permission_classes = [IsAuthenticated, IsProviderOrAdmin]

    def get_provider(self, request):
        try:
            return Provider.objects.get(user=request.user)
        except Provider.DoesNotExist:
            return None

    def post(self, request):
        provider = self.get_provider(request)
        if not provider:
            return Response(
                {"detail": "Provider not found for this user."},
                status=status.HTTP_404_NOT_FOUND,
            )

        person_id = request.data.get("person_id")
        if not person_id:
            return Response(
                {"detail": "Missing person_id in request."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Certifique-se de que existe a pessoa
        try:
            person = Person.objects.get(pk=person_id)
        except Person.DoesNotExist:
            return Response(
                {"detail": "Person not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Buscando o conceito "CUIDADOR" para o relacionamento
        try:
            relationship_concept = Concept.objects.get(concept_name="CUIDADOR")
        except Concept.DoesNotExist:
            return Response(
                {"detail": "Relationship concept 'CUIDADOR' not configured."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Criar o FactRelationship
        fact_relationship = FactRelationship.objects.create(
            domain_concept_id_1=Concept.objects.get(concept_name="Person"),
            fact_id_1=person.pk,
            domain_concept_id_2=Concept.objects.get(concept_name="Provider"),
            fact_id_2=provider.pk,
            relationship_concept_id=relationship_concept,
        )

        serializer = FactRelationshipSerializer(fact_relationship)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get(self, request):
        provider = self.get_provider(request)
        if not provider:
            return Response(
                {"detail": "Provider not found for this user."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            relationship_concept = Concept.objects.get(concept_name="CUIDADOR")
        except Concept.DoesNotExist:
            return Response(
                {"detail": "Relationship concept 'CUIDADOR' not configured."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        relationships = FactRelationship.objects.filter(
            fact_id_2=provider.pk,
            relationship_concept_id=relationship_concept,
            domain_concept_id_1__concept_name="Person",
            domain_concept_id_2__concept_name="Provider",
        ).select_related("domain_concept_id_1", "domain_concept_id_2", "relationship_concept_id")

        serializer = FactRelationshipSerializer(relationships, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(tags=["Vocabulary"])
class VocabularyViewSet(viewsets.ModelViewSet):
    queryset = Vocabulary.objects.all()
    serializer_class = VocabularySerializer


@extend_schema(tags=["ConceptClass"])
class ConceptClassViewSet(viewsets.ModelViewSet):
    queryset = ConceptClass.objects.all()
    serializer_class = ConceptClassSerializer


@extend_schema(tags=["Concept"])
class ConceptViewSet(viewsets.ModelViewSet):
    queryset = Concept.objects.all()
    serializer_class = ConceptSerializer


@extend_schema(tags=["ConceptSynonym"])
class ConceptSynonymViewSet(viewsets.ModelViewSet):
    queryset = ConceptSynonym.objects.all()
    serializer_class = ConceptSynonymSerializer


@extend_schema(tags=["Domain"])
class DomainViewSet(viewsets.ModelViewSet):
    queryset = Domain.objects.all()
    serializer_class = DomainSerializer


@extend_schema(tags=["Location"])
class LocationViewSet(viewsets.ModelViewSet):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer


@extend_schema(tags=["CareSite"])
class CareSiteViewSet(viewsets.ModelViewSet):
    queryset = CareSite.objects.all()
    serializer_class = CareSiteSerializer


@extend_schema(tags=["DrugExposure"])
class DrugExposureViewSet(viewsets.ModelViewSet):
    queryset = DrugExposure.objects.all()
    serializer_class = DrugExposureSerializer


@extend_schema(tags=["Observation"])
class ObservationViewSet(viewsets.ModelViewSet):
    queryset = Observation.objects.all()
    serializer_class = ObservationSerializer


@extend_schema(tags=["VisitOccurrence"])
class VisitOccurrenceViewSet(viewsets.ModelViewSet):
    queryset = VisitOccurrence.objects.all()
    serializer_class = VisitOccurrenceSerializer


@extend_schema(tags=["Measurement"])
class MeasurementViewSet(viewsets.ModelViewSet):
    queryset = Measurement.objects.all()
    serializer_class = MeasurementSerializer


@extend_schema(tags=["FactRelationship"])
class FactRelationshipViewSet(viewsets.ModelViewSet):
    queryset = FactRelationship.objects.all()
    serializer_class = FactRelationshipSerializer
