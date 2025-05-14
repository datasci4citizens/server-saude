import logging
import uuid
from datetime import timedelta

from django.contrib.auth import authenticate, get_user_model
from django.db import transaction
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import filters, status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
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


class UserRoleView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Verifica se o usuário está associado a um Person
        try:
            person = Person.objects.get(user=user)
            return Response({"person_id": person.person_id}, status=status.HTTP_200_OK)
        except Person.DoesNotExist:
            pass

        # Verifica se o usuário está associado a um Provider
        try:
            provider = Provider.objects.get(user=user)
            return Response({"provider_id": provider.provider_id}, status=status.HTTP_200_OK)
        except Provider.DoesNotExist:
            pass

        # Caso o usuário não esteja associado a nenhum dos dois
        return Response(
            {"detail": "User is not associated with a Person or Provider."},
            status=status.HTTP_404_NOT_FOUND,
        )


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


@extend_schema(tags=["Link-Person-Provider"], responses=ProviderLinkCodeResponseSerializer)
class GenerateProviderLinkCodeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        provider = get_object_or_404(Provider, user=request.user)

        code = uuid.uuid4().hex[:6].upper()  # Ex: 'A1B2C3'

        obs, created = Observation.objects.get_or_create(
            person=None,
            observation_concept_id=9200010,  # PROVIDER_LINK_CODE
            observation_type_concept_id=9200011,  # CLINICIAN_GENERATED
            provider_id=provider.provider_id,
            defaults={
                "value_as_string": code,
                "observation_date": timezone.now(),
            }
        )

        if not created:
            # Atualiza o código e a data se já existe
            obs.value_as_string = code
            obs.observation_date = timezone.now()
            obs.save(update_fields=["value_as_string", "observation_date"])

        return Response({"code": code})


@extend_schema(
    tags=["Link-Person-Provider"],
    request=PersonLinkProviderRequestSerializer,
    responses=PersonLinkProviderResponseSerializer,
)
class PersonLinkProviderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        person = get_object_or_404(Person, user=request.user)
        code = request.data.get("code")

        obs = (
            Observation.objects.filter(
                value_as_string=code,
                observation_concept_id=9200010,
                observation_date__gte=timezone.now() - timedelta(minutes=10),
                person__isnull=True,  # ainda não usado
            )
            .order_by("-observation_date")
            .first()
        )

        if not obs or not obs.provider_id:
            return Response({"error": "Código inválido ou expirado."}, status=400)

        # Relacionamento person ↔ provider
        FactRelationship.objects.get_or_create(
            fact_id_1=person.person_id,
            domain_concept_1_id=9202,  # Concept ID para "Person" (OMOP)
            fact_id_2=obs.provider_id,
            domain_concept_2_id=9201,  # Concept ID para "Provider" (OMOP)
            relationship_concept_id=9200001,  # Person linked to Provider
        )

        # Marca como usado
        obs.person_id = person.person_id
        obs.save(update_fields=["person_id"])

        return Response({"status": "linked"})
@extend_schema(
    tags=["Link-Person-Provider"],
    request=PersonLinkProviderRequestSerializer,
    responses=ProviderRetrieveSerializer,
)
class ProviderByLinkCodeView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        code = request.data.get("code")
        if not code:
            return Response({"error": "Code is required."}, status=400)

        obs = (
            Observation.objects.filter(
                value_as_string=code,
                observation_concept_id=9200010,
                observation_date__gte=timezone.now() - timedelta(minutes=10),
            )
            .order_by("-observation_date")
            .first()
        )

        if not obs or not obs.provider_id:
            return Response({"error": "Código inválido ou expirado."}, status=400)

        provider = get_object_or_404(Provider, provider_id=obs.provider_id)
        serializer = ProviderRetrieveSerializer(provider)
        return Response(serializer.data)
    
@extend_schema(
    tags=["Link-Person-Provider"],
    responses=ProviderRetrieveSerializer(many=True),
)
class PersonProvidersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        person = get_object_or_404(Person, user=request.user)
        relationships = FactRelationship.objects.filter(
            fact_id_1=person.person_id,
            domain_concept_1_id=9202,  # Person
            domain_concept_2_id=9201,  # Provider
            relationship_concept_id=9200001,
        )
        provider_ids = relationships.values_list("fact_id_2", flat=True)
        providers = Provider.objects.filter(provider_id__in=provider_ids)
        serializer = ProviderRetrieveSerializer(providers, many=True)
        return Response(serializer.data)
    
@extend_schema(
    tags=["Link-Person-Provider"],
    responses=PersonRetrieveSerializer(many=True),
)
class ProviderPersonsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        provider = get_object_or_404(Provider, user=request.user)
        relationships = FactRelationship.objects.filter(
            fact_id_2=provider.provider_id,
            domain_concept_1_id=9202,  # Person
            domain_concept_2_id=9201,  # Provider
            relationship_concept_id=9200001,
        )
        person_ids = relationships.values_list("fact_id_1", flat=True)
        persons = Person.objects.filter(person_id__in=person_ids)
        serializer = PersonRetrieveSerializer(persons, many=True)
        return Response(serializer.data)

@api_view(["POST"])
@permission_classes([AllowAny])
def dev_login_as_provider(request):
    if not settings.DEBUG:
        return Response({"detail": "Não disponível em produção"}, status=403)

    User = get_user_model()
    user = User.objects.get(email="mock-provider@email.com")
    refresh = RefreshToken.for_user(user)
    return Response(
        {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def dev_login_as_person(request):
    if not settings.DEBUG:
        return Response({"detail": "Não disponível em produção"}, status=403)

    User = get_user_model()
    user = User.objects.get(email="Dummy@email.com")
    refresh = RefreshToken.for_user(user)
    return Response(
        {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }
    )

@api_view(["GET"])
@permission_classes([IsAuthenticated])
@extend_schema(
    tags=["Link-Person-Provider"],
    responses={"200": {"type": "array", "items": {"type": "object", "properties": {
        "person_id": {"type": "integer"},
        "name": {"type": "string"},
        "age": {"type": "integer", "nullable": True},
        "last_emergency_date": {"type": "string", "format": "date-time", "nullable": True}
    }}}}
)
def provider_persons(request):
    """
    Função para obter todos os pacientes vinculados ao médico (provider) autenticado
    
    Returns:
        lista de dicionários com os dados de cada paciente:
            - person_id: ID do paciente
            - name: Nome do paciente (social_name ou nome do usuário)
            - age: Idade calculada com base na data de nascimento ou ano de nascimento
            - last_emergency_date: Data da última emergência registrada
    """
    # Verifica se o usuário é um provider e obtém seu ID
    provider = get_object_or_404(Provider, user=request.user)
    provider_id = provider.provider_id
    
    # O restante do código permanece o mesmo
    # Encontra os IDs de pessoas vinculadas ao provider através do FactRelationship
    linked_persons_ids = FactRelationship.objects.filter(
        fact_id_2=provider_id,
        domain_concept_1_id=9202,  # Person
        domain_concept_2_id=9201,  # Provider
        relationship_concept_id=9200001  # Person linked to Provider
    ).values_list('fact_id_1', flat=True)
    
    # Busca as pessoas com esses IDs
    persons = Person.objects.filter(person_id__in=linked_persons_ids)
    
    # Prepara os dados da resposta com informações adicionais
    result = []
    for person in persons:
        today = timezone.now()
        age = None
        
        # Calcula a idade
        if person.birth_datetime:
            age = today.year - person.birth_datetime.year
            # Ajusta se ainda não fez aniversário este ano
            if today.month < person.birth_datetime.month or (
                today.month == person.birth_datetime.month and
                today.day < person.birth_datetime.day
            ):
                age -= 1
        elif person.year_of_birth:
            age = today.year - person.year_of_birth
            
        # Busca a última emergência
        last_emergency = None
        emergency_observation = Observation.objects.filter(
            person=person,
            observation_concept_id=9200020,  # Código para emergência
            observation_date__isnull=False
        ).order_by('-observation_date').first()
        
        if emergency_observation:
            last_emergency = emergency_observation.observation_date
            
        # Nome pode estar em social_name ou no user associado
        name = person.social_name
        if not name and person.user:
            name = f"{person.user.first_name} {person.user.last_name}".strip()
            if not name:
                name = person.user.username
        
        result.append({
            "person_id": person.person_id,
            "name": name,
            "age": age,
            "last_emergency_date": last_emergency
        })
        
    return Response(result)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
@extend_schema(
    tags=["Linked_Persons"],
    responses={"200": {"type": "object", "properties": {
        "emergency_count": {"type": "integer"},
    }}}
)
def get_emergency(request):
    """
    Função para obter o número de emergências ativas para os pacientes vinculados ao provider autenticado
    
    Returns:
        objeto com a contagem de emergências ativas:
            - emergency_count: número de emergências ativas
    """
    # Verifica se o usuário é um provider e obtém seu ID
    provider = get_object_or_404(Provider, user=request.user)
    provider_id = provider.provider_id
    
    # Encontra os IDs de pessoas vinculadas ao provider através do FactRelationship
    linked_persons_ids = FactRelationship.objects.filter(
        fact_id_2=provider_id,
        domain_concept_1_id=9202,  # Person
        domain_concept_2_id=9201,  # Provider
        relationship_concept_id=9200001  # Person linked to Provider
    ).values_list('fact_id_1', flat=True)
    
    # Conta as emergências ativas para essas pessoas
    emergency_count = Observation.objects.filter(
        person_id__in=linked_persons_ids,
        observation_concept_id=9200020,  # Emergency concept
        value_as_concept_id=9200021  # Active status concept
    ).count()
    
    return Response({"emergency_count": emergency_count})
