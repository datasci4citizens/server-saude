import logging

from django.contrib.auth import authenticate, get_user_model
from django.db import transaction
from django.db.models import Prefetch
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import filters, status, viewsets
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

        # Check if user is already registered as a provider or person
        provider_id = None
        person_id = None
        role = "none"
        if Provider.objects.filter(user=user).exists():
            provider_id = Provider.objects.get(user=user).pk
            role = "provider"
        elif Person.objects.filter(user=user).exists():
            person_id = Person.objects.get(user=user).pk
            role = "person"

        # generate jwt token for the user
        token = RefreshToken.for_user(user)
        response = {
            "access": str(token.access_token),
            "refresh": str(token),
            "provider_id": provider_id,
            "person_id": person_id,
            "role": role,
            "user_id": user.pk,
        }

        return Response(response, status=200)


class AdminLoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=AdminLoginSerializer)
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


class FlexibleViewSet(viewsets.ModelViewSet):
    def get_serializer_class(self):
        prefix = self.__class__.__name__.replace("ViewSet", "")
        if self.action == "create":
            return globals()[f"{prefix}CreateSerializer"]
        elif self.action in ["update", "partial_update"]:
            return globals()[f"{prefix}UpdateSerializer"]
        return globals()[f"{prefix}RetrieveSerializer"]


@extend_schema(tags=["Person"])
class PersonViewSet(FlexibleViewSet):
    queryset = Person.objects.all()
    permission_classes = [IsAuthenticated]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = "__all__"
    ordering_fields = "__all__"
    search_fields = ["social_name"]

    def get_queryset(self):
        return Person.objects.all()

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
class ProviderViewSet(FlexibleViewSet):
    queryset = Provider.objects.all()
    permission_classes = [IsAuthenticated]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = "__all__"
    ordering_fields = "__all__"
    search_fields = ["social_name"]

    def get_queryset(self):
        return Provider.objects.all()

    def create(self, request, *args, **kwargs):
        if Provider.objects.filter(user=request.user).exists():
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

        serializer = FactRelationshipCreateSerializer(fact_relationship)
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

        serializer = FactRelationshipRetrieveSerializer(relationships, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(tags=["Vocabulary"])
class VocabularyViewSet(FlexibleViewSet):
    queryset = Vocabulary.objects.all()


@extend_schema(tags=["ConceptClass"])
class ConceptClassViewSet(FlexibleViewSet):
    queryset = ConceptClass.objects.all()


@extend_schema(
    tags=["Concept"],
    parameters=[
        OpenApiParameter(
            name="class",
            description="Lista de concept_class_id (ex: class=Gender,Ethnicity)",
            required=False,
            type=str,
            style="form",
            explode=False,
        ),
        OpenApiParameter(name="lang", description="Idioma da tradução (ex: pt)", required=False, type=str),
    ],
)
class ConceptViewSet(FlexibleViewSet):
    queryset = Concept.objects.all()

    def get_queryset(self):
        queryset = Concept.objects.all()

        lang = self.request.query_params.get("lang", "pt")

        class_ids = self.request.query_params.get("class")
        if class_ids:
            # Suporta múltiplos separados por vírgula
            class_id_list = [s.strip() for s in class_ids.split(",")]
            queryset = queryset.filter(concept_class__concept_class_id__in=class_id_list)

        # traz só os sinônimos no idioma desejado
        queryset = queryset.prefetch_related(
            Prefetch(
                "concept_synonym_concept_set",
                queryset=ConceptSynonym.objects.filter(language_concept__concept_code=lang),
                to_attr="translated_synonyms",
            )
        )

        return queryset


@extend_schema(tags=["ConceptSynonym"])
class ConceptSynonymViewSet(FlexibleViewSet):
    queryset = ConceptSynonym.objects.all()


@extend_schema(tags=["Domain"])
class DomainViewSet(FlexibleViewSet):
    queryset = Domain.objects.all()


@extend_schema(tags=["Location"])
class LocationViewSet(FlexibleViewSet):
    queryset = Location.objects.all()


@extend_schema(tags=["CareSite"])
class CareSiteViewSet(FlexibleViewSet):
    queryset = CareSite.objects.all()


@extend_schema(tags=["DrugExposure"])
class DrugExposureViewSet(FlexibleViewSet):
    queryset = DrugExposure.objects.all()


@extend_schema(tags=["Observation"])
class ObservationViewSet(FlexibleViewSet):
    queryset = Observation.objects.all()


@extend_schema(tags=["VisitOccurrence"])
class VisitOccurrenceViewSet(FlexibleViewSet):
    queryset = VisitOccurrence.objects.all()


@extend_schema(tags=["Measurement"])
class MeasurementViewSet(FlexibleViewSet):
    queryset = Measurement.objects.all()


@extend_schema(tags=["FactRelationship"])
class FactRelationshipViewSet(FlexibleViewSet):
    queryset = FactRelationship.objects.all()


@extend_schema(
    tags=["FullPerson"],
    request=FullPersonCreateSerializer,
    responses={201: FullPersonRetrieveSerializer},
)
class FullPersonViewSet(FlexibleViewSet):
    http_method_names = ["post"]  # limita só para POST
    queryset = Person.objects.none()  # evita problemas, mas não retorna nada se alguém fizer GET

    def post(self, request):
        serializer = self.serializer_class(data=request.data, context={"request": request})
        data = serializer.validated_data
        person_data = data["person"]
        location_data = data["location"]
        observations_data = data["observations"]
        drug_exposures_data = data["drug_exposures"]

        try:
            with transaction.atomic():
                # 1. Criar Person
                person = Person.objects.create(**person_data)

                # 2. Criar Location (associada a person)
                Location.objects.create(person=person, **location_data)

                # 3. Criar Observations
                for obs in observations_data:
                    Observation.objects.create(person=person, **obs)

                # 4. Criar Drug Exposures
                for drug in drug_exposures_data:
                    DrugExposure.objects.create(person=person, **drug)

                return Response({"message": "Onboarding concluído com sucesso"}, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=["FullProvider"],
    request=FullProviderCreateSerializer,
    responses={201: FullProviderRetrieveSerializer},
)
class FullProviderViewSet(FlexibleViewSet):
    http_method_names = ["post"]
    queryset = Provider.objects.none()
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data, context={"request": request})

        # Valida os dados
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                # Delega a criação ao serializer
                result = serializer.save()

                return Response(
                    {"message": "Provider criado com sucesso", "data": result},
                    status=status.HTTP_201_CREATED,
                )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
