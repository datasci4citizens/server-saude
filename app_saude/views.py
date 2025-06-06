import logging
import uuid
from datetime import timedelta

from django.contrib.auth import authenticate, get_user_model
from django.db import transaction
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import filters, status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from app_saude.serializers import AuthSerializer
from libs.google import google_get_user_data

from .models import *
from .serializers import *
from .utils.provider import *

User = get_user_model()
logger = logging.getLogger(__name__)


class GoogleLoginView(APIView):
    serializer_class = AuthSerializer
    permission_classes = [AllowAny]

    @extend_schema(request=AuthSerializer, responses={200: AuthTokenResponseSerializer})
    def post(self, request, *args, **kwargs):

        auth_serializer = self.serializer_class(data=request.data)
        auth_serializer.is_valid(raise_exception=True)

        validated_data = auth_serializer.validated_data

        # Get user data from google
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

        # Generate jwt token for the user
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


@extend_schema(tags=["Logout"], request=LogoutSerializer)
class LogoutView(APIView):
    """
    View to logout the user.
    Removes the refresh token and returns a success response.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"detail": "Logout successful."}, status=status.HTTP_205_RESET_CONTENT)
        except AttributeError:
            return Response({"detail": "Token blacklisting not enabled."}, status=status.HTTP_501_NOT_IMPLEMENTED)
        except Exception as e:
            print(f"Logout error: {str(e)}")
            return Response(
                {"detail": "Invalid token or token already blacklisted."}, status=status.HTTP_400_BAD_REQUEST
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


@extend_schema(tags=["Account"])
class AccountViewSet(FlexibleViewSet):
    """
    ViewSet to manage user accounts.
    Allowed HTTP methods: GET, DELETE.
    """

    http_method_names = ["get", "delete"]

    queryset = User.objects.all()
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        user = request.user
        serializer = UserRetrieveSerializer(user)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        return Response({"detail": "This endpoint is not available."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def destroy(self, request, *args, **kwargs):
        user = request.user
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Person"])
class PersonViewSet(FlexibleViewSet):
    queryset = Person.objects.all()
    permission_classes = [IsAuthenticated]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = "__all__"
    ordering_fields = "__all__"
    search_fields = ["social_name"]

    @extend_schema(request=PersonCreateSerializer, responses={201: PersonRetrieveSerializer})
    def create(self, request, *args, **kwargs):
        if Person.objects.filter(user=request.user).exists():
            raise ValidationError("You already have a person registration.")
        return super().create(request, *args, **kwargs)


@extend_schema(tags=["Provider"])
class ProviderViewSet(FlexibleViewSet):
    queryset = Provider.objects.all()
    permission_classes = [IsAuthenticated]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = "__all__"
    ordering_fields = "__all__"
    search_fields = ["social_name"]

    @extend_schema(request=ProviderCreateSerializer, responses={201: ProviderRetrieveSerializer})
    def create(self, request, *args, **kwargs):
        if Provider.objects.filter(user=request.user).exists():
            raise ValidationError("You already have a provider registration.")
        return super().create(request, *args, **kwargs)


class UserRoleView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Check if the user is associated with a Person
        try:
            person = Person.objects.get(user=user)
            return Response({"person_id": person.person_id}, status=status.HTTP_200_OK)
        except Person.DoesNotExist:
            pass

        # Check if the user is associated with a Provider
        try:
            provider = Provider.objects.get(user=user)
            return Response({"provider_id": provider.provider_id}, status=status.HTTP_200_OK)
        except Provider.DoesNotExist:
            pass

        # If the user is not associated with either
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
            description="concept_class_id list (ex: class=Gender,Ethnicity)",
            required=False,
            type=str,
            style="form",
            explode=False,
        ),
        OpenApiParameter(name="lang", description="Translation language (ex: pt)", required=False, type=str),
        OpenApiParameter(
            name="relationship",
            description="relationship_id to search for each concept (ex: has_value_type)",
            required=False,
            type=str,
        ),
    ],
)
class ConceptViewSet(FlexibleViewSet):
    queryset = Concept.objects.all()

    def get_queryset(self):
        queryset = Concept.objects.all()

        lang = self.request.query_params.get("lang", "pt")
        class_ids = self.request.query_params.get("class")
        relationship_id = self.request.query_params.get("relationship")

        if class_ids:
            # Supports multiple separated by comma
            class_id_list = [s.strip() for s in class_ids.split(",")]
            queryset = queryset.filter(concept_class__concept_class_id__in=class_id_list)

        # Prefetch only synonyms in the desired language
        queryset = queryset.prefetch_related(
            Prefetch(
                "concept_synonym_concept_set",
                queryset=ConceptSynonym.objects.filter(language_concept__concept_code=lang),
                to_attr="translated_synonyms",
            )
        )

        self._enrich_relationship_id = relationship_id  # Store for later use
        self._lang = lang
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        relationship_id = getattr(self, "_enrich_relationship_id", None)
        lang = getattr(self, "_lang", None)
        results = []

        for concept in queryset:
            # Serialize the main concept
            base = ConceptRetrieveSerializer(concept).data

            if relationship_id:
                rel = (
                    ConceptRelationship.objects.select_related("concept_2")
                    .prefetch_related(
                        Prefetch(
                            "concept_2__concept_synonym_concept_set",
                            queryset=ConceptSynonym.objects.filter(language_concept__concept_code=lang),
                            to_attr="translated_synonyms",
                        )
                    )
                    .filter(relationship_id=relationship_id, concept_1=concept)
                    .first()
                )

                if rel:
                    # Serialize the related concept with the same serializer
                    base["related_concept"] = ConceptRetrieveSerializer(rel.concept_2).data

            results.append(base)

        return Response(results)


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

    # Create the PATCH request, that receives only the value_as_concept field
    @extend_schema(
        request=MarkAttentionPointSerializer,
        responses={204: OpenApiTypes.OBJECT},
    )
    def patch(self, request, *args, **kwargs):
        serializer = MarkAttentionPointSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Update the observation
        observation = get_object_or_404(Observation, id=data["observation_id"])
        if data["is_attention_point"]:
            # If is_attention_point is True, set value_as_concept to YES
            observation.value_as_concept = get_concept_by_code("value_yes")
        else:
            # If is_attention_point is False, set value_as_concept to NO
            observation.value_as_concept = get_concept_by_code("value_no")

        observation.save()

        return Response(status=status.HTTP_204_NO_CONTENT)


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
    http_method_names = ["post"]  # only allow POST
    queryset = Person.objects.none()  # prevents GET from returning anything

    def post(self, request):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        person_data = data["person"]
        location_data = data["location"]
        observations_data = data["observations"]
        drug_exposures_data = data["drug_exposures"]

        try:
            with transaction.atomic():
                # 1. Create Person
                person = Person.objects.create(**person_data)

                # 2. Create Location (associated with person)
                Location.objects.create(person=person, **location_data)

                # 3. Create Observations
                for obs in observations_data:
                    Observation.objects.create(person=person, **obs)

                # 4. Create Drug Exposures
                for drug in drug_exposures_data:
                    DrugExposure.objects.create(person=person, **drug)

                return Response({"message": "Onboarding completed successfully"}, status=status.HTTP_201_CREATED)

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

        # Validate the data
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                # Delegate creation to the serializer
                result = serializer.save()

                return Response(
                    {"message": "Provider created successfully", "data": result},
                    status=status.HTTP_201_CREATED,
                )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=["Link-Person-Provider"], responses=ProviderLinkCodeResponseSerializer)
class GenerateProviderLinkCodeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        provider = get_object_or_404(Provider, user=request.user)

        code = uuid.uuid4().hex[:6].upper()  # E.g., 'A1B2C3'

        obs, created = Observation.objects.get_or_create(
            person=None,
            observation_concept_id=get_concept_by_code("PROVIDER_LINK_CODE").concept_id,  # PROVIDER_LINK_CODE
            observation_type_concept_id=get_concept_by_code("CLINICIAN_GENERATED").concept_id,  # CLINICIAN_GENERATED
            provider_id=provider.provider_id,
            defaults={
                "value_as_string": code,
                "observation_date": timezone.now(),
            },
        )

        if not created:
            # Update the code and date if it already exists
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
                observation_concept_id=get_concept_by_code("PROVIDER_LINK_CODE").concept_id,
                observation_date__gte=timezone.now() - timedelta(minutes=10),
                person__isnull=True,  # not used yet
            )
            .order_by("-observation_date")
            .first()
        )

        if not obs or not obs.provider_id:
            return Response({"error": "Invalid or expired code."}, status=400)

        # Relationship person ↔ provider
        FactRelationship.objects.get_or_create(
            fact_id_1=person.person_id,
            domain_concept_1_id=get_concept_by_code("PERSON").concept_id,
            fact_id_2=obs.provider_id,
            domain_concept_2_id=get_concept_by_code("PROVIDER").concept_id,
            relationship_concept_id=get_concept_by_code("PERSON_PROVIDER").concept_id,  # Person linked to Provider
        )

        # Mark as used
        obs.person_id = person.person_id
        obs.save(update_fields=["person_id"])

        return Response({"status": "linked"})


@extend_schema(
    tags=["Link-Person-Provider"],
    request=PersonLinkProviderRequestSerializer,
    responses=ProviderRetrieveSerializer,
)
class ProviderByLinkCodeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        code = request.data.get("code")
        if not code:
            return Response({"error": "Code is required."}, status=400)

        obs = (
            Observation.objects.filter(
                value_as_string=code,
                observation_concept_id=get_concept_by_code("PROVIDER_LINK_CODE").concept_id,
                observation_date__gte=timezone.now() - timedelta(minutes=10),
            )
            .order_by("-observation_date")
            .first()
        )

        if not obs or not obs.provider_id:
            return Response({"error": "Invalid or expired code."}, status=400)

        provider = get_object_or_404(Provider, provider_id=obs.provider_id)
        serializer = ProviderRetrieveSerializer(provider)
        return Response(serializer.data)


@extend_schema(
    tags=["Link-Person-Provider"],
    request=PersonProviderUnlinkRequestSerializer,
    responses=PersonProviderUnlinkResponseSerializer,
)
class PersonProviderUnlinkView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, person_id, provider_id):
        person = get_object_or_404(Person, person_id=person_id)
        provider = get_object_or_404(Provider, provider_id=provider_id)

        # Remove the relationship
        FactRelationship.objects.filter(
            fact_id_1=person.person_id,
            domain_concept_1_id=9202,  # Person
            fact_id_2=provider.provider_id,
            domain_concept_2_id=9201,  # Provider
            relationship_concept_id=9200001,
        ).delete()

        return Response({"status": "unlinked"})


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
            domain_concept_1_id=get_concept_by_code("PERSON"),  # Person
            domain_concept_2_id=get_concept_by_code("PROVIDER"),  # Provider
            relationship_concept_id=get_concept_by_code("PERSON_PROVIDER"),  # Person linked to Provider
        )
        provider_ids = relationships.values_list("fact_id_2", flat=True)
        providers = Provider.objects.filter(provider_id__in=provider_ids)
        serializer = ProviderRetrieveSerializer(providers, many=True)
        return Response(serializer.data)


@extend_schema(tags=["Link-Person-Provider"], responses=ProviderPersonSummarySerializer(many=True))
class ProviderPersonsView(APIView):
    """
    View to retrieve all patients linked to the authenticated provider additional information
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Check if user is a provider and get their ID
        provider = get_object_or_404(Provider, user=request.user)
        provider_id = provider.provider_id

        # Find IDs of persons linked to this provider through FactRelationship
        linked_persons_ids = FactRelationship.objects.filter(
            fact_id_2=provider_id,
            domain_concept_1_id=get_concept_by_code("PERSON"),
            domain_concept_2_id=get_concept_by_code("PROVIDER"),
            relationship_concept_id=get_concept_by_code("PERSON_PROVIDER"),
        ).values_list("fact_id_1", flat=True)

        # Get persons with these IDs
        persons = Person.objects.filter(person_id__in=linked_persons_ids)

        # Prepare response data with additional information
        person_summaries = []
        for person in persons:
            today = timezone.now()
            age = None

            # Calculate age
            if person.birth_datetime:
                age = today.year - person.birth_datetime.year
                # Adjust if birthday hasn't occurred this year
                if today.month < person.birth_datetime.month or (
                    today.month == person.birth_datetime.month and today.day < person.birth_datetime.day
                ):
                    age -= 1
            elif person.year_of_birth:
                age = today.year - person.year_of_birth

            # Get the last visit (consultation) with this provider
            last_visit = None
            visit = (
                VisitOccurrence.objects.filter(person=person, provider_id=provider_id, visit_start_date__isnull=False)
                .order_by("-visit_start_date")
                .first()
            )

            if visit:
                last_visit = visit.visit_start_date

            # Get the last recorded help
            last_help = None
            help = (
                Observation.objects.filter(
                    person=person,
                    observation_concept_id=get_concept_by_code("HELP"),
                    observation_date__isnull=False,
                )
                .order_by("-observation_date")
                .first()
            )

            if help:
                last_help = help.observation_date

            # Name could be in social_name or associated user
            name = person.social_name
            if not name and person.user:
                name = f"{person.user.first_name} {person.user.last_name}".strip()
                if not name:
                    name = person.user.username

            person_summaries.append(
                {
                    "person_id": person.person_id,
                    "name": name,
                    "age": age,
                    "last_visit_date": last_visit,
                    "last_help_date": last_help,
                }
            )

        # Use the serializer to format and validate the data
        serializer = ProviderPersonSummarySerializer(person_summaries, many=True)
        return Response(serializer.data)


@api_view(["POST"])
@permission_classes([AllowAny])
def dev_login_as_provider(request):
    if not settings.DEBUG:
        return Response({"detail": "Not available in production"}, status=403)

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
        return Response({"detail": "Not available in production"}, status=403)

    User = get_user_model()
    user = User.objects.get(email="mock-person@email.com")
    refresh = RefreshToken.for_user(user)
    return Response(
        {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }
    )


@extend_schema(tags=["Help"], responses=HelpCountSerializer)
class HelpCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        This endpoint counts the number of active helps (observations) for all patients linked to the provider.

        Returns:
            Object with the count of active helps:
                - help_count: number of active helps
        """
        # Check if user is a provider and get ID
        provider = get_object_or_404(Provider, user=request.user)
        provider_id = provider.provider_id

        # Find IDs of persons linked to the provider through FactRelationship
        linked_persons_ids = FactRelationship.objects.filter(
            fact_id_2=provider_id,
            domain_concept_1_id=get_concept_by_code("PERSON"),  # Person concept
            domain_concept_2_id=get_concept_by_code("PROVIDER"),  # Provider concept
            relationship_concept_id=get_concept_by_code("PERSON_PROVIDER"),  # Person-Provider relationship
        ).values_list("fact_id_1", flat=True)

        # Count active helps for these persons
        help_count = Observation.objects.filter(
            person_id__in=linked_persons_ids,
            provider_id=provider_id,  # Only helps from this provider
            observation_concept_id=get_concept_by_code("HELP"),  # Help concept
            value_as_concept_id=get_concept_by_code("ACTIVE"),  # Active status concept
        )

        # Use serializer for response data validation and formatting
        serializer = HelpCountSerializer({"help_count": help_count.count()})
        return Response(serializer.data)


@extend_schema(tags=["Linked_Persons"], responses=NextVisitSerializer)
class NextScheduledVisitView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Get the next scheduled visit for the authenticated provider

        Returns:
            Object with details about the next visit:
                - next_visit: Object containing:
                    - person_name: Patient name
                    - visit_date: Date and time of the appointment
        """
        # Check if user is a provider and get ID
        provider = get_object_or_404(Provider, user=request.user)
        provider_id = provider.provider_id

        # Find the next scheduled visit for this provider
        # Only consider future visits (from current date)
        today = timezone.now()
        next_visit = (
            VisitOccurrence.objects.filter(provider_id=provider_id, visit_start_date__gt=today)
            .order_by("visit_start_date")
            .first()
        )

        if not next_visit:
            serializer = NextVisitSerializer({"next_visit": None})
            return Response(serializer.data)

        # Get patient name
        person = next_visit.person
        person_name = person.social_name
        if not person_name and person.user:
            person_name = f"{person.user.first_name} {person.user.last_name}".strip()
            if not person_name:
                person_name = person.user.username

        # Prepare response
        visit_data = {"next_visit": {"person_name": person_name, "visit_date": next_visit.visit_start_date}}

        serializer = NextVisitSerializer(visit_data)
        return Response(serializer.data)


@extend_schema(
    tags=["Help"],
    request=HelpCreateSerializer(many=True),
    responses=ObservationRetrieveSerializer(many=True),
)
class SendHelpView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = HelpCreateSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        data_list = serializer.validated_data

        observations = []
        for data in data_list:
            data["person_id"] = request.user.person.person_id
            data["observation_concept_id"] = get_concept_by_code("HELP").concept_id
            data["value_as_concept_id"] = get_concept_by_code("ACTIVE").concept_id
            data["observation_date"] = timezone.now()
            data["observation_type_concept_id"] = None

            obs = Observation.objects.create(**data)
            observations.append(obs)

        response_serializer = ObservationRetrieveSerializer(observations, many=True)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=["Help"],
    responses=ObservationRetrieveSerializer(many=True),
)
class ReceivedHelpsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        provider = get_object_or_404(Provider, user=request.user)
        helps = Observation.objects.filter(
            provider_id=provider.provider_id, observation_concept_id=get_concept_by_code("HELP")  # Ajuda
        ).order_by("-observation_date")
        print(helps)
        serializer = ObservationRetrieveSerializer(helps, many=True)
        return Response(serializer.data)


@extend_schema(
    tags=["Diary"],
)
class DiaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            # Get optional limit parameter
            limit = request.query_params.get("limit")

            # Search for all "mother" diary entries
            diary_entries_query = Observation.objects.filter(
                observation_concept_id=get_concept_by_code("diary_entry").concept_id
            ).order_by("-observation_date")

            # Apply limit if provided
            if limit and limit.isdigit():
                diary_entries_query = diary_entries_query[: int(limit)]

            diary_entries = diary_entries_query.select_related("observation_concept")

            serializer = DiaryRetrieveSerializer(diary_entries, many=True)
            return Response(serializer.data)

        except Exception as e:
            logger.error(f"Error retrieving diaries: {str(e)}")
            return Response({"error": "Failed to retrieve diaries"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        summary="Create a new diary for the logged-in user",
        request=DiaryCreateSerializer,
        responses={201: OpenApiTypes.OBJECT},
    )
    def post(self, request):
        serializer = DiaryCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(result, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=["Diary"],
    responses=DiaryRetrieveSerializer(),
)
class DiaryDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, diary_id):
        try:
            diary = get_object_or_404(
                Observation,
                observation_id=diary_id,
                observation_concept_id=get_concept_by_code("diary_entry").concept_id,
            )

            serializer = DiaryRetrieveSerializer(diary)
            return Response(serializer.data)

        except Exception as e:
            logger.error(f"Error retrieving diary {diary_id}: {str(e)}")
            return Response({"error": "Failed to retrieve diary"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        responses={204: None},
        parameters=[
            OpenApiParameter(
                name="diary_id", type=int, location=OpenApiParameter.PATH, description="ID of the diary to delete"
            )
        ],
    )
    def delete(self, request, diary_id):
        serializer = DiaryDeleteSerializer()
        result = serializer.delete({"diary_id": diary_id})
        return Response(result, status=status.HTTP_200_OK)


@extend_schema(
    tags=["Diary"],
    responses=DiaryRetrieveSerializer(many=True),
)
class PersonDiariesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        person = get_object_or_404(Person, user=request.user)

        diaries = Observation.objects.filter(
            person=person, observation_concept_id=get_concept_by_code("diary_entry").concept_id
        ).order_by("-observation_date")

        serializer = DiaryRetrieveSerializer(diaries, many=True)
        return Response(serializer.data)


@extend_schema(
    tags=["Diary"],
    responses=DiaryRetrieveSerializer(many=True),
)
class ProviderPersonDiariesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        provider = get_object_or_404(Provider, user=request.user)
        linked_persons_ids = FactRelationship.objects.filter(
            fact_id_2=provider.provider_id,
            domain_concept_1_id=get_concept_by_code("PERSON"),
            domain_concept_2_id=get_concept_by_code("PROVIDER"),
            relationship_concept_id=get_concept_by_code("PERSON_PROVIDER"),
        ).values_list("fact_id_1", flat=True)

        persons = Person.objects.filter(person_id__in=linked_persons_ids)

        diaries = Observation.objects.filter(
            person_id__in=persons.values_list("person_id", flat=True),
            observation_concept_id=get_concept_by_code("diary_entry").concept_id,
            shared_with_provider=True,
        ).order_by("-observation_date")

        serializer = DiaryRetrieveSerializer(diaries, many=True)
        return Response(serializer.data)


# Fiquei com medo de mudar essa funcao, mas teoricamente absoleta
class ProviderPersonDiaryDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, person_id, diary_id):
        try:
            person = Person.objects.get(person_id=person_id)
            # Get the specific diary
            diary = get_object_or_404(
                Observation,
                observation_id=diary_id,
                person=person,
                observation_concept_id=get_concept_by_code("diary_entry").concept_id,
            )

            # Get related observations using the same timestamp
            related_observations = Observation.objects.filter(
                person=person,
                observation_date=diary.observation_date,
                observation_type_concept_id=get_concept_by_code("diary_entry_type").concept_id,
            ).exclude(observation_id=diary.observation_id)

            interest_areas = Observation.objects.filter(
                person=person, observation_type_concept_id=get_concept_by_code("INTEREST_AREA").concept_id
            ).select_related("observation_concept")

            # Get triggers for each interest area
            interest_areas_with_triggers = []
            for interest_area in interest_areas:
                # Get triggers for this interest area
                trigger_relationships = FactRelationship.objects.filter(
                    domain_concept_1_id=get_concept_by_code("INTEREST_AREA").concept_id,
                    fact_id_1=interest_area.observation_id,
                    relationship_concept_id=get_concept_by_code("AOI_TRIGGER").concept_id,
                )
                trigger_ids = trigger_relationships.values_list("fact_id_2", flat=True)
                triggers = Observation.objects.filter(observation_id__in=trigger_ids)

                # Format interest area with its triggers
                interest_data = InterestAreaSerializer(interest_area).data
                interest_data["triggers"] = InterestAreaTriggerSerializer(triggers, many=True).data
                interest_areas_with_triggers.append(interest_data)

            # Prepare full response
            diary_data = {
                "diary_id": diary.observation_id,
                "date": diary.observation_date,
                "scope": diary.value_as_string,
                "entries": ObservationRetrieveSerializer(related_observations, many=True).data,
                "interest_areas": interest_areas_with_triggers,
            }

            return Response(diary_data)

        except Exception as e:
            logger.error(f"Error retrieving diary details: {str(e)}")
            return Response({"error": "Failed to retrieve diary details"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(tags=["Interest_Areas"], responses={200: InterestAreaSerializer(many=True)})
class PersonInterestAreaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        person = get_object_or_404(Person, user=request.user)

        interest_areas = Observation.objects.filter(
            person=person, observation_type_concept_id=get_concept_by_code("INTEREST_AREA").concept_id
        ).select_related("observation_concept")

        results = []

        for interest_area in interest_areas:
            interest_data = InterestAreaSerializer(interest_area).data

            relationships = FactRelationship.objects.filter(
                domain_concept_1_id=get_concept_by_code("INTEREST_AREA").concept_id,
                fact_id_1=interest_area.observation_id,
                relationship_concept_id=get_concept_by_code("AOI_TRIGGER").concept_id,
            )

            trigger_ids = relationships.values_list("fact_id_2", flat=True)

            # Searching for triggers related to the interest area
            triggers = Observation.objects.filter(observation_id__in=trigger_ids).select_related("observation_concept")

            interest_data["triggers"] = InterestAreaTriggerSerializer(triggers, many=True).data
            results.append(interest_data)

        return Response(results)

    @extend_schema(tags=["Interest_Areas"], request=InterestAreaSerializer, responses={201: InterestAreaSerializer})
    def post(self, request):

        serializer = InterestAreaSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        interest_area = serializer.save()

        return Response(InterestAreaSerializer(interest_area).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        request=InterestAreaBulkUpdateSerializer,
        responses={200: OpenApiTypes.OBJECT},
    )
    def patch(self, request):
        serializer = InterestAreaBulkUpdateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        result = serializer.save()

        return Response(result, status=status.HTTP_200_OK)


@extend_schema(tags=["Interest_Areas"])
class PersonInterestAreaDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: InterestAreaSerializer})
    def get(self, request, interest_area_id):
        person = get_object_or_404(Person, user=request.user)

        interest_area = get_object_or_404(
            Observation,
            observation_id=interest_area_id,
            person=person,
            observation_type_concept_id=get_concept_by_code("INTEREST_AREA").concept_id,
        )

        interest_data = InterestAreaSerializer(interest_area).data

        relationships = FactRelationship.objects.filter(
            domain_concept_1_id=get_concept_by_code("INTEREST_AREA").concept_id,
            fact_id_1=interest_area.observation_id,
            relationship_concept_id=get_concept_by_code("AOI_TRIGGER").concept_id,
        )

        trigger_ids = relationships.values_list("fact_id_2", flat=True)
        triggers = Observation.objects.filter(observation_id__in=trigger_ids).select_related("observation_concept")

        interest_data["triggers"] = InterestAreaTriggerSerializer(triggers, many=True).data

        return Response(interest_data)

    @extend_schema(responses={204: None})
    def delete(self, request, interest_area_id):
        person = get_object_or_404(Person, user=request.user)

        interest_area = get_object_or_404(
            Observation,
            observation_id=interest_area_id,
            person=person,
            observation_type_concept_id=get_concept_by_code("INTEREST_AREA").concept_id,
        )

        relationships = FactRelationship.objects.filter(
            domain_concept_1_id=get_concept_by_code("INTEREST_AREA").concept_id,
            fact_id_1=interest_area.observation_id,
            relationship_concept_id=get_concept_by_code("AOI_TRIGGER").concept_id,
        )

        trigger_ids = list(relationships.values_list("fact_id_2", flat=True))

        relationships.delete()

        for trigger_id in trigger_ids:
            if not FactRelationship.objects.filter(
                domain_concept_2_id=get_concept_by_code("TRIGGER").concept_id, fact_id_2=trigger_id
            ).exists():
                Observation.objects.filter(observation_id=trigger_id).delete()

        interest_area.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)
