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
from libs.google import GoogleUserData, google_get_user_data

from .models import *
from .serializers import *

# from .utils.interest_area import get_interest_areas_and_triggers
from .utils.provider import *

User = get_user_model()
logger = logging.getLogger("app_saude")


class GoogleLoginView(APIView):
    serializer_class = AuthSerializer
    permission_classes = [AllowAny]

    @extend_schema(request=AuthSerializer, responses={200: AuthTokenResponseSerializer})
    def post(self, request, *args, **kwargs):

        auth_serializer = self.serializer_class(data=request.data)
        auth_serializer.is_valid(raise_exception=True)

        validated_data = auth_serializer.validated_data

        # Get user data from google
        user_data: GoogleUserData = google_get_user_data(validated_data)

        # Creates user in DB if first time login
        user, created = User.objects.get_or_create(
            email=user_data.email,
            username=user_data.email,
            defaults={
                "first_name": user_data.given_name,
                "last_name": user_data.family_name,
            },
        )

        if not created:
            user.first_name = user_data.given_name
            user.last_name = user_data.family_name
            user.save()

        # Check if user is already registered as a provider or person
        provider_id = None
        person_id = None
        social_name = None
        use_dark_mode = False
        profile_picture = user_data.picture
        role = "none"

        # Check if user is already registered as a provider
        if Provider.objects.filter(user=user).exists():
            provider = Provider.objects.get(user=user)
            social_name = getattr(provider, "social_name", None)
            use_dark_mode = provider.use_dark_mode
            if profile_picture:
                provider.profile_picture = profile_picture
                provider.save(update_fields=["profile_picture"])
            provider_id = provider.provider_id
            role = "provider"

        # Check if user is already registered as a person
        if Person.objects.filter(user=user).exists():
            person = Person.objects.get(user=user)
            social_name = getattr(person, "social_name", None)
            use_dark_mode = person.use_dark_mode
            if profile_picture:
                person.profile_picture = profile_picture
                person.save(update_fields=["profile_picture"])
            person_id = person.person_id
            role = "person"

        # Generate jwt token for the user
        token = RefreshToken.for_user(user)

        # Name could be in social_name or associated user
        name = social_name
        if not name and user:
            name = f"{user.first_name} {user.last_name}".strip()
            if not name:
                name = user.username

        response = {
            "access": str(token.access_token),
            "refresh": str(token),
            "provider_id": provider_id,
            "person_id": person_id,
            "role": role,
            "user_id": user.pk,
            "full_name": name,
            "email": user_data.email,
            "social_name": social_name,
            "profile_picture": profile_picture,
            "use_dark_mode": use_dark_mode,
        }

        return Response(response, status=200)


class AdminLoginView(APIView):
    permission_classes = [AllowAny]

    # Add query params to the schema
    @extend_schema(
        parameters=[
            OpenApiParameter("email", OpenApiTypes.STR, description="Email of the user"),
            OpenApiParameter("username", OpenApiTypes.STR, description="Admin username"),
            OpenApiParameter("password", OpenApiTypes.STR, description="Admin password"),
        ]
    )
    def get(self, request):
        """
        Admin login endpoint.
        Passes admin user and pass to authenticate, and a email to get the user data.
        Returns a JWT token for the email if successful.
        """
        email = request.query_params.get("email")

        # Authenticate the user using admin credentials
        username = request.query_params.get("username")
        password = request.query_params.get("password")
        admin_user = authenticate(username=username, password=password)

        if not admin_user or not admin_user.is_staff:
            return Response(
                {"detail": "Invalid credentials or insufficient permissions."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not email:
            return Response(
                {"detail": "Email is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.filter(email=email).first()
        if not user:
            return Response(
                {"detail": "User with this email does not exist."},
                status=status.HTTP_404_NOT_FOUND,
            )

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "user_id": user.id,
                "username": user.username,
                "person_id": getattr(user.person, "person_id", None) if hasattr(user, "person") else None,
                "provider_id": getattr(user.provider, "provider_id", None) if hasattr(user, "provider") else None,
            }
        )

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
class AccountView(APIView):
    """
    ViewSet to manage user accounts.
    Allowed HTTP methods: GET, DELETE.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        logger.info(
            "Account retrieval requested",
            extra={"user_id": user.id, "username": user.username, "email": user.email, "action": "get_account"},
        )

        try:
            serializer = UserRetrieveSerializer(user)
            logger.info(
                "Account data successfully retrieved",
                extra={
                    "user_id": user.id,
                    "data_fields": list(serializer.data.keys()),
                    "action": "get_account_success",
                },
            )
            return Response(serializer.data)
        except Exception as e:
            logger.error(
                "Failed to retrieve account data",
                extra={"user_id": user.id, "error": str(e), "action": "get_account_error"},
                exc_info=True,
            )
            raise

    def delete(self, request, *args, **kwargs):
        user = request.user
        logger.warning(
            "Account deletion requested - CRITICAL ACTION",
            extra={
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "ip_address": request.META.get("REMOTE_ADDR"),
                "user_agent": request.META.get("HTTP_USER_AGENT"),
                "action": "delete_account_requested",
            },
        )

        id = None
        user_type = None

        # Determine user type and ID
        try:
            if Provider.objects.filter(user=user).exists():
                provider = Provider.objects.get(user=user)
                id = provider.provider_id
                user_type = "provider"
                logger.debug(
                    "User identified as provider for deletion",
                    extra={"user_id": user.id, "provider_id": id, "action": "delete_account_type_identified"},
                )
            elif Person.objects.filter(user=user).exists():
                person = Person.objects.get(user=user)
                id = person.person_id
                user_type = "person"
                logger.debug(
                    "User identified as person for deletion",
                    extra={"user_id": user.id, "person_id": id, "action": "delete_account_type_identified"},
                )
            else:
                logger.warning(
                    "User deletion attempted but no associated Person or Provider found",
                    extra={"user_id": user.id, "action": "delete_account_no_profile"},
                )
        except Exception as e:
            logger.error(
                "Error determining user type for deletion",
                extra={"user_id": user.id, "error": str(e), "action": "delete_account_type_error"},
                exc_info=True,
            )
            raise

        # Atomic deletion process
        try:
            with transaction.atomic():
                logger.info(
                    "Starting atomic account deletion transaction",
                    extra={
                        "user_id": user.id,
                        "profile_id": id,
                        "user_type": user_type,
                        "action": "delete_account_transaction_start",
                    },
                )

                # Delete fact relationships
                relationships_deleted_1 = FactRelationship.objects.filter(fact_id_1=id).count()
                relationships_deleted_2 = FactRelationship.objects.filter(fact_id_2=id).count()

                FactRelationship.objects.filter(fact_id_1=id).delete()
                FactRelationship.objects.filter(fact_id_2=id).delete()

                logger.info(
                    "Fact relationships deleted during account deletion",
                    extra={
                        "user_id": user.id,
                        "profile_id": id,
                        "relationships_deleted_as_fact_1": relationships_deleted_1,
                        "relationships_deleted_as_fact_2": relationships_deleted_2,
                        "total_relationships_deleted": relationships_deleted_1 + relationships_deleted_2,
                        "action": "delete_account_relationships_deleted",
                    },
                )

                # Soft delete user account
                original_email = user.email
                original_username = user.username

                user.email = f"deleted_{id}_{user.email}"
                user.username = f"deleted_{id}_{user.username}"
                user.is_active = False
                user.save()

                logger.critical(
                    "User account successfully soft deleted",
                    extra={
                        "user_id": user.id,
                        "profile_id": id,
                        "user_type": user_type,
                        "original_email": original_email,
                        "original_username": original_username,
                        "new_email": user.email,
                        "new_username": user.username,
                        "is_active": user.is_active,
                        "action": "delete_account_completed",
                    },
                )

        except Exception as e:
            logger.error(
                "Critical error during account deletion transaction",
                extra={
                    "user_id": user.id,
                    "profile_id": id,
                    "user_type": user_type,
                    "error": str(e),
                    "action": "delete_account_transaction_error",
                },
                exc_info=True,
            )
            raise

        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Account"])
class SwitchDarkModeView(APIView):
    """
    ViewSet to switch dark mode for the user.
    Allowed HTTP methods: POST.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        logger.info("Dark mode toggle requested", extra={"user_id": user.id, "action": "toggle_dark_mode_requested"})

        try:
            person = Person.objects.filter(user=user).first()
            if person:
                original_setting = person.use_dark_mode
                person.use_dark_mode = not person.use_dark_mode
                person.save(update_fields=["use_dark_mode"])

                logger.info(
                    "Dark mode toggled for Person",
                    extra={
                        "user_id": user.id,
                        "person_id": person.person_id,
                        "user_type": "person",
                        "previous_dark_mode": original_setting,
                        "new_dark_mode": person.use_dark_mode,
                        "action": "toggle_dark_mode_person_success",
                    },
                )
            else:
                provider = Provider.objects.filter(user=user).first()
                if provider:
                    original_setting = provider.use_dark_mode
                    provider.use_dark_mode = not provider.use_dark_mode
                    provider.save(update_fields=["use_dark_mode"])

                    logger.info(
                        "Dark mode toggled for Provider",
                        extra={
                            "user_id": user.id,
                            "provider_id": provider.provider_id,
                            "user_type": "provider",
                            "previous_dark_mode": original_setting,
                            "new_dark_mode": provider.use_dark_mode,
                            "action": "toggle_dark_mode_provider_success",
                        },
                    )
                else:
                    logger.warning(
                        "Dark mode toggle attempted but no Person or Provider profile found",
                        extra={"user_id": user.id, "action": "toggle_dark_mode_no_profile"},
                    )

        except Exception as e:
            logger.error(
                "Error toggling dark mode",
                extra={"user_id": user.id, "error": str(e), "action": "toggle_dark_mode_error"},
                exc_info=True,
            )
            raise

        return Response(status=status.HTTP_200_OK)


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
        user = request.user
        logger.info(
            "Person registration attempted",
            extra={
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "action": "person_registration_requested",
            },
        )

        # Check for existing person registration
        if Person.objects.filter(user=request.user).exists():
            existing_person = Person.objects.get(user=request.user)
            logger.warning(
                "Person registration blocked - user already has person profile",
                extra={
                    "user_id": user.id,
                    "existing_person_id": existing_person.person_id,
                    "existing_social_name": existing_person.social_name,
                    "action": "person_registration_duplicate_blocked",
                },
            )
            raise ValidationError("You already have a person registration.")

        try:
            result = super().create(request, *args, **kwargs)

            # Get the created person for logging
            if result.status_code == 201:
                created_person = Person.objects.get(user=user)
                logger.info(
                    "Person registration completed successfully",
                    extra={
                        "user_id": user.id,
                        "person_id": created_person.person_id,
                        "social_name": created_person.social_name,
                        "age": getattr(created_person, "age", None),
                        "action": "person_registration_success",
                    },
                )

            return result

        except Exception as e:
            logger.error(
                "Person registration failed",
                extra={
                    "user_id": user.id,
                    "error": str(e),
                    "request_data": request.data,
                    "action": "person_registration_error",
                },
                exc_info=True,
            )
            raise


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
        user = request.user
        logger.info(
            "Provider registration attempted",
            extra={
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "action": "provider_registration_requested",
            },
        )

        # Check for existing provider registration
        if Provider.objects.filter(user=request.user).exists():
            existing_provider = Provider.objects.get(user=request.user)
            logger.warning(
                "Provider registration blocked - user already has provider profile",
                extra={
                    "user_id": user.id,
                    "existing_provider_id": existing_provider.provider_id,
                    "existing_social_name": existing_provider.social_name,
                    "existing_professional_registration": getattr(existing_provider, "professional_registration", None),
                    "action": "provider_registration_duplicate_blocked",
                },
            )
            raise ValidationError("You already have a provider registration.")

        try:
            result = super().create(request, *args, **kwargs)

            # Get the created provider for logging
            if result.status_code == 201:
                created_provider = Provider.objects.get(user=user)
                logger.info(
                    "Provider registration completed successfully",
                    extra={
                        "user_id": user.id,
                        "provider_id": created_provider.provider_id,
                        "social_name": created_provider.social_name,
                        "professional_registration": getattr(created_provider, "professional_registration", None),
                        "specialty": getattr(created_provider, "specialty", None),
                        "action": "provider_registration_success",
                    },
                )

            return result

        except Exception as e:
            logger.error(
                "Provider registration failed",
                extra={
                    "user_id": user.id,
                    "error": str(e),
                    "request_data": request.data,
                    "action": "provider_registration_error",
                },
                exc_info=True,
            )
            raise


class UserRoleView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        logger.debug(
            "User role lookup requested",
            extra={"user_id": user.id, "username": user.username, "action": "user_role_lookup_requested"},
        )

        # Check if the user is associated with a Person
        try:
            person = Person.objects.get(user=user)
            logger.info(
                "User role identified as Person",
                extra={
                    "user_id": user.id,
                    "person_id": person.person_id,
                    "social_name": person.social_name,
                    "role": "person",
                    "action": "user_role_person_found",
                },
            )
            return Response({"person_id": person.person_id}, status=status.HTTP_200_OK)
        except Person.DoesNotExist:
            logger.debug(
                "User not found as Person, checking Provider",
                extra={"user_id": user.id, "action": "user_role_person_not_found"},
            )

        # Check if the user is associated with a Provider
        try:
            provider = Provider.objects.get(user=user)
            logger.info(
                "User role identified as Provider",
                extra={
                    "user_id": user.id,
                    "provider_id": provider.provider_id,
                    "social_name": provider.social_name,
                    "professional_registration": getattr(provider, "professional_registration", None),
                    "role": "provider",
                    "action": "user_role_provider_found",
                },
            )
            return Response({"provider_id": provider.provider_id}, status=status.HTTP_200_OK)
        except Provider.DoesNotExist:
            logger.warning(
                "User role lookup failed - no Person or Provider profile found",
                extra={
                    "user_id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "is_active": user.is_active,
                    "date_joined": user.date_joined.isoformat() if user.date_joined else None,
                    "action": "user_role_not_found",
                },
            )

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
        OpenApiParameter(
            name="code",
            description="concept_code list (ex: code=ACTIVE,RESOLVED)",
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

        lang = self.request.query_params.get("lang", "297504001")  # Default to Portuguese (297504001)
        class_ids = self.request.query_params.get("class")
        codes = self.request.query_params.get("code")
        relationship_id = self.request.query_params.get("relationship")

        if class_ids:
            # Supports multiple separated by comma
            class_id_list = [s.strip() for s in class_ids.split(",")]
            queryset = queryset.filter(concept_class__concept_class_id__in=class_id_list)

        if codes:
            # Supports multiple separated by comma
            code_list = [s.strip() for s in codes.split(",")]
            queryset = queryset.filter(concept_code__in=code_list)

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

    def create(self, request):
        user = request.user
        logger.info(
            "Full person onboarding initiated",
            extra={
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "ip_address": request.META.get("REMOTE_ADDR"),
                "user_agent": request.META.get("HTTP_USER_AGENT"),
                "action": "full_person_onboarding_start",
            },
        )

        serializer: FullPersonCreateSerializer = self.get_serializer(data=request.data, context={"request": request})

        try:
            # Check for existing person registration
            if Person.objects.filter(user=request.user).exists():
                existing_person = Person.objects.get(user=request.user)
                logger.warning(
                    "Full person onboarding blocked - duplicate registration",
                    extra={
                        "user_id": user.id,
                        "existing_person_id": existing_person.person_id,
                        "existing_social_name": existing_person.social_name,
                        "action": "full_person_onboarding_duplicate_blocked",
                    },
                )
                raise ValidationError("You already have a person registration.")

            # Validate and create
            serializer.is_valid(raise_exception=True)

            logger.debug(
                "Full person onboarding data validated successfully",
                extra={
                    "user_id": user.id,
                    "data_fields": list(request.data.keys()),
                    "action": "full_person_onboarding_validated",
                },
            )

            serializer.create(request.data)

            # Get the created person for detailed logging
            created_person = Person.objects.get(user=user)
            logger.info(
                "Full person onboarding completed successfully",
                extra={
                    "user_id": user.id,
                    "person_id": created_person.person_id,
                    "social_name": created_person.social_name,
                    "age": getattr(created_person, "age", None),
                    "birth_datetime": (
                        created_person.birth_datetime.isoformat() if created_person.birth_datetime else None
                    ),
                    "action": "full_person_onboarding_success",
                },
            )

            return Response({"message": "Onboarding completed successfully"}, status=status.HTTP_201_CREATED)

        except ValidationError as ve:
            logger.warning(
                "Full person onboarding validation failed",
                extra={
                    "user_id": user.id,
                    "validation_errors": str(ve),
                    "request_data_keys": list(request.data.keys()),
                    "action": "full_person_onboarding_validation_error",
                },
            )
            return Response({"error": str(ve)}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(
                "Critical error during full person onboarding",
                extra={
                    "user_id": user.id,
                    "error": str(e),
                    "request_data": request.data,
                    "action": "full_person_onboarding_critical_error",
                },
                exc_info=True,
            )
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

    def create(self, request):
        logger.info(
            "Full provider registration initiated",
            extra={
                "ip_address": request.META.get("REMOTE_ADDR"),
                "user_agent": request.META.get("HTTP_USER_AGENT"),
                "email": request.data.get("email"),
                "professional_registration": request.data.get("professional_registration"),
                "action": "full_provider_registration_start",
            },
        )

        serializer = self.get_serializer(data=request.data, context={"request": request})

        # Validate the data
        if not serializer.is_valid():
            errors = serializer.errors
            logger.warning(
                "Full provider registration validation failed",
                extra={
                    "validation_errors": json.dumps(errors, ensure_ascii=False),
                    "email": request.data.get("email"),
                    "request_data_keys": list(request.data.keys()),
                    "action": "full_provider_registration_validation_failed",
                },
            )
            return Response(
                {
                    "message": "Validation failed",
                    "errors": errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            try:
                logger.debug(
                    "Starting atomic transaction for provider creation",
                    extra={
                        "email": request.data.get("email"),
                        "action": "full_provider_registration_transaction_start",
                    },
                )

                result = serializer.save()
                response = ProviderRetrieveSerializer(result["provider"]).data

                # Log successful creation with provider details
                provider = result["provider"]
                user = result.get("user")

                logger.info(
                    "Full provider registration completed successfully",
                    extra={
                        "provider_id": provider.provider_id,
                        "user_id": user.id if user else None,
                        "social_name": provider.social_name,
                        "professional_registration": getattr(provider, "professional_registration", None),
                        "specialty": getattr(provider, "specialty", None),
                        "email": user.email if user else None,
                        "action": "full_provider_registration_success",
                    },
                )

                return Response(
                    {"message": "Provider created successfully", "data": response},
                    status=status.HTTP_201_CREATED,
                )

            except Exception as e:
                # revert the transaction
                transaction.set_rollback(True)
                logger.error(
                    "Critical error during provider creation - transaction rolled back",
                    extra={
                        "error": str(e),
                        "email": request.data.get("email"),
                        "request_data": request.data,
                        "action": "full_provider_registration_critical_error",
                    },
                    exc_info=True,
                )
                return Response(
                    {"error": "Erro interno ao criar o provedor"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )


@extend_schema(tags=["Link-Person-Provider"], responses=ProviderLinkCodeResponseSerializer)
class GenerateProviderLinkCodeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        provider = get_object_or_404(Provider, user=request.user)

        logger.info(
            "Provider link code generation requested",
            extra={
                "user_id": user.id,
                "provider_id": provider.provider_id,
                "provider_name": provider.social_name,
                "action": "provider_link_code_generation_requested",
            },
        )

        code = uuid.uuid4().hex[:6].upper()  # E.g., 'A1B2C3'

        logger.debug(
            "Generated new provider link code",
            extra={
                "user_id": user.id,
                "provider_id": provider.provider_id,
                "code": code,
                "expiry_minutes": 10,
                "action": "provider_link_code_generated",
            },
        )

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
            old_code = obs.value_as_string
            obs.value_as_string = code
            obs.observation_date = timezone.now()
            obs.save(update_fields=["value_as_string", "observation_date"])

            logger.info(
                "Provider link code updated (replaced existing)",
                extra={
                    "user_id": user.id,
                    "provider_id": provider.provider_id,
                    "old_code": old_code,
                    "new_code": code,
                    "action": "provider_link_code_updated",
                },
            )
        else:
            logger.info(
                "New provider link code created",
                extra={
                    "user_id": user.id,
                    "provider_id": provider.provider_id,
                    "code": code,
                    "observation_id": obs.id,
                    "action": "provider_link_code_created",
                },
            )

        return Response({"code": code})


@extend_schema(
    tags=["Link-Person-Provider"],
    request=PersonLinkProviderRequestSerializer,
    responses=PersonLinkProviderResponseSerializer,
)
class PersonLinkProviderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        person = get_object_or_404(Person, user=request.user)
        code = request.data.get("code")

        logger.info(
            "Person-Provider linking attempted",
            extra={
                "user_id": user.id,
                "person_id": person.person_id,
                "person_name": person.social_name,
                "code": code,
                "action": "person_provider_linking_attempted",
            },
        )

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
            logger.warning(
                "Person-Provider linking failed - invalid or expired code",
                extra={
                    "user_id": user.id,
                    "person_id": person.person_id,
                    "code": code,
                    "code_found": obs is not None,
                    "provider_id_exists": obs.provider_id if obs else None,
                    "action": "person_provider_linking_invalid_code",
                },
            )
            return Response({"error": "Invalid or expired code."}, status=400)

        # Get provider details for logging
        provider = get_object_or_404(Provider, provider_id=obs.provider_id)

        # Check if relationship already exists
        existing_relationship = FactRelationship.objects.filter(
            fact_id_1=person.person_id,
            domain_concept_1_id=get_concept_by_code("PERSON").concept_id,
            fact_id_2=obs.provider_id,
            domain_concept_2_id=get_concept_by_code("PROVIDER").concept_id,
            relationship_concept_id=get_concept_by_code("PERSON_PROVIDER").concept_id,
        ).exists()

        # Relationship person ↔ provider
        relationship, created = FactRelationship.objects.get_or_create(
            fact_id_1=person.person_id,
            domain_concept_1_id=get_concept_by_code("PERSON").concept_id,
            fact_id_2=obs.provider_id,
            domain_concept_2_id=get_concept_by_code("PROVIDER").concept_id,
            relationship_concept_id=get_concept_by_code("PERSON_PROVIDER").concept_id,  # Person linked to Provider
        )

        # Mark as used
        obs.person_id = person.person_id
        obs.save(update_fields=["person_id"])

        logger.info(
            "Person-Provider linking completed successfully",
            extra={
                "user_id": user.id,
                "person_id": person.person_id,
                "person_name": person.social_name,
                "provider_id": obs.provider_id,
                "provider_name": provider.social_name,
                "code": code,
                "relationship_created": created,
                "relationship_existed": existing_relationship,
                "observation_id": obs.id,
                "action": "person_provider_linking_success",
            },
        )

        return Response({"status": "linked"})


@extend_schema(
    tags=["Link-Person-Provider"],
    request=PersonLinkProviderRequestSerializer,
    responses=ProviderRetrieveSerializer,
)
class ProviderByLinkCodeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        code = request.data.get("code")

        logger.debug(
            "Provider lookup by link code requested",
            extra={"user_id": user.id, "code": code, "action": "provider_lookup_by_code_requested"},
        )

        if not code:
            logger.warning(
                "Provider lookup failed - no code provided",
                extra={"user_id": user.id, "action": "provider_lookup_no_code"},
            )
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
            logger.warning(
                "Provider lookup failed - invalid or expired code",
                extra={
                    "user_id": user.id,
                    "code": code,
                    "observation_found": obs is not None,
                    "provider_id_exists": obs.provider_id if obs else None,
                    "action": "provider_lookup_invalid_code",
                },
            )
            return Response({"error": "Invalid or expired code."}, status=400)

        provider = get_object_or_404(Provider, provider_id=obs.provider_id)
        serializer = ProviderRetrieveSerializer(provider)

        logger.info(
            "Provider successfully retrieved by link code",
            extra={
                "user_id": user.id,
                "code": code,
                "provider_id": provider.provider_id,
                "provider_name": provider.social_name,
                "professional_registration": getattr(provider, "professional_registration", None),
                "observation_id": obs.id,
                "action": "provider_lookup_success",
            },
        )

        return Response(serializer.data)


@extend_schema(
    tags=["Link-Person-Provider"],
    request=PersonProviderUnlinkRequestSerializer,
    responses=PersonProviderUnlinkResponseSerializer,
)
class PersonProviderUnlinkView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, person_id, provider_id):
        user = request.user
        person = get_object_or_404(Person, person_id=person_id)
        provider = get_object_or_404(Provider, provider_id=provider_id)

        logger.warning(
            "Person-Provider unlinking requested - CRITICAL ACTION",
            extra={
                "user_id": user.id,
                "person_id": person_id,
                "provider_id": provider_id,
                "person_name": person.social_name,
                "provider_name": provider.social_name,
                "ip_address": request.META.get("REMOTE_ADDR"),
                "user_agent": request.META.get("HTTP_USER_AGENT"),
                "action": "person_provider_unlinking_requested",
            },
        )

        # Find and count relationships to be removed
        relationships = FactRelationship.objects.filter(
            fact_id_1=person.person_id,
            domain_concept_1_id=get_concept_by_code("PERSON").concept_id,
            fact_id_2=provider.provider_id,
            domain_concept_2_id=get_concept_by_code("PROVIDER").concept_id,
            relationship_concept_id=get_concept_by_code("PERSON_PROVIDER").concept_id,
        )

        relationship_count = relationships.count()

        logger.info(
            "Person-Provider relationships identified for deletion",
            extra={
                "user_id": user.id,
                "person_id": person_id,
                "provider_id": provider_id,
                "relationships_found": relationship_count,
                "action": "person_provider_unlinking_relationships_found",
            },
        )

        # Remove the relationships
        deleted_count, deleted_details = relationships.delete()

        logger.critical(
            "Person-Provider unlinking completed successfully",
            extra={
                "user_id": user.id,
                "person_id": person_id,
                "provider_id": provider_id,
                "person_name": person.social_name,
                "provider_name": provider.social_name,
                "relationships_deleted": deleted_count,
                "deletion_details": deleted_details,
                "action": "person_provider_unlinking_success",
            },
        )

        return Response({"status": "unlinked"})


@extend_schema(
    tags=["Link-Person-Provider"],
    responses=ProviderRetrieveSerializer(many=True),
)
class PersonProvidersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        person = get_object_or_404(Person, user=request.user)

        logger.debug(
            "Person's linked providers retrieval requested",
            extra={
                "user_id": user.id,
                "person_id": person.person_id,
                "person_name": person.social_name,
                "action": "person_providers_retrieval_requested",
            },
        )

        relationships = FactRelationship.objects.filter(
            fact_id_1=person.person_id,
            domain_concept_1_id=get_concept_by_code("PERSON").concept_id,  # Person
            domain_concept_2_id=get_concept_by_code("PROVIDER").concept_id,  # Provider
            relationship_concept_id=get_concept_by_code("PERSON_PROVIDER").concept_id,  # Person linked to Provider
        )

        provider_ids = relationships.values_list("fact_id_2", flat=True)
        providers = Provider.objects.filter(provider_id__in=provider_ids)
        serializer = ProviderRetrieveSerializer(providers, many=True)

        logger.info(
            "Person's linked providers retrieved successfully",
            extra={
                "user_id": user.id,
                "person_id": person.person_id,
                "person_name": person.social_name,
                "linked_providers_count": len(provider_ids),
                "provider_ids": list(provider_ids),
                "provider_names": [p.social_name for p in providers],
                "action": "person_providers_retrieval_success",
            },
        )

        return Response(serializer.data)


@extend_schema(tags=["Link-Person-Provider"], responses=ProviderPersonSummarySerializer(many=True))
class ProviderPersonsView(APIView):
    """
    View to retrieve all patients linked to the authenticated provider with additional information
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        # Check if user is a provider and get their ID
        provider = get_object_or_404(Provider, user=request.user)
        provider_id = provider.provider_id

        logger.debug(
            "Provider's linked persons retrieval requested",
            extra={
                "user_id": user.id,
                "provider_id": provider_id,
                "provider_name": provider.social_name,
                "action": "provider_persons_retrieval_requested",
            },
        )

        # Find IDs of persons linked to this provider through FactRelationship
        linked_persons_ids = FactRelationship.objects.filter(
            fact_id_2=provider_id,
            domain_concept_1_id=get_concept_by_code("PERSON").concept_id,
            domain_concept_2_id=get_concept_by_code("PROVIDER").concept_id,
            relationship_concept_id=get_concept_by_code("PERSON_PROVIDER").concept_id,
        ).values_list("fact_id_1", flat=True)

        # Get persons with these IDs
        persons = Person.objects.filter(person_id__in=linked_persons_ids)

        logger.debug(
            "Provider's linked persons identified",
            extra={
                "user_id": user.id,
                "provider_id": provider_id,
                "linked_persons_count": len(linked_persons_ids),
                "person_ids": list(linked_persons_ids),
                "action": "provider_persons_identified",
            },
        )

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
            help_obs = (
                Observation.objects.filter(
                    person=person,
                    provider_id=provider_id,
                    observation_concept_id=get_concept_by_code("HELP").concept_id,
                    value_as_concept_id=get_concept_by_code("ACTIVE").concept_id,
                    observation_date__isnull=False,
                )
                .order_by("-observation_date")
                .first()
            )

            if help_obs:
                last_help = help_obs.observation_date

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

        logger.info(
            "Provider's linked persons retrieved successfully",
            extra={
                "user_id": user.id,
                "provider_id": provider_id,
                "provider_name": provider.social_name,
                "total_linked_persons": len(person_summaries),
                "persons_with_recent_help": len([p for p in person_summaries if p["last_help_date"]]),
                "persons_with_recent_visits": len([p for p in person_summaries if p["last_visit_date"]]),
                "action": "provider_persons_retrieval_success",
            },
        )

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
        user = request.user

        logger.info("Help count retrieval requested", extra={"user_id": user.id, "action": "help_count_requested"})

        try:
            # Check if user is a provider and get ID
            provider = get_object_or_404(Provider, user=request.user)
            provider_id = provider.provider_id

            # Find IDs of persons linked to the provider through FactRelationship
            linked_persons_ids = FactRelationship.objects.filter(
                fact_id_2=provider_id,
                domain_concept_1_id=get_concept_by_code("PERSON").concept_id,  # Person concept
                domain_concept_2_id=get_concept_by_code("PROVIDER").concept_id,  # Provider concept
                relationship_concept_id=get_concept_by_code(
                    "PERSON_PROVIDER"
                ).concept_id,  # Person-Provider relationship
            ).values_list("fact_id_1", flat=True)

            # Count active helps for these persons
            help_count = Observation.objects.filter(
                person_id__in=linked_persons_ids,
                provider_id=provider_id,  # Only helps from this provider
                observation_concept_id=get_concept_by_code("HELP").concept_id,  # Help concept
                value_as_concept_id=get_concept_by_code("ACTIVE").concept_id,  # Active status concept
            ).count()

            # Use serializer for response data validation and formatting
            serializer = HelpCountSerializer({"help_count": help_count})

            logger.info(
                "Help count retrieval completed successfully",
                extra={
                    "user_id": user.id,
                    "provider_id": provider_id,
                    "help_count": help_count,
                    "action": "help_count_success",
                },
            )

            return Response(serializer.data)

        except Exception as e:
            logger.error(
                "Error during help count retrieval",
                extra={"user_id": user.id, "error": str(e), "action": "help_count_error"},
                exc_info=True,
            )
            raise


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
        user = request.user

        logger.info("Send help request received", extra={"user_id": user.id, "action": "send_help_requested"})

        try:
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

            logger.info(
                "Send help request completed successfully",
                extra={
                    "user_id": user.id,
                    "person_id": request.user.person.person_id,
                    "help_requests_created": len(observations),
                    "action": "send_help_success",
                },
            )

            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(
                "Error during send help request",
                extra={"user_id": user.id, "error": str(e), "action": "send_help_error"},
                exc_info=True,
            )
            raise


@extend_schema(
    tags=["Help"],
    responses=ObservationRetrieveSerializer(many=True),
)
class ReceivedHelpsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        logger.info(
            "Received helps retrieval requested", extra={"user_id": user.id, "action": "received_helps_requested"}
        )

        try:
            provider = get_object_or_404(Provider, user=request.user)
            helps = Observation.objects.filter(
                provider_id=provider.provider_id, observation_concept_id=get_concept_by_code("HELP").concept_id
            ).order_by("-observation_date")
            serializer = ObservationRetrieveSerializer(helps, many=True)

            logger.info(
                "Received helps retrieval completed successfully",
                extra={
                    "user_id": user.id,
                    "provider_id": provider.provider_id,
                    "helps_count": len(helps),
                    "action": "received_helps_success",
                },
            )

            return Response(serializer.data)

        except Exception as e:
            logger.error(
                "Error during received helps retrieval",
                extra={"user_id": user.id, "error": str(e), "action": "received_helps_error"},
                exc_info=True,
            )
            raise


@extend_schema(
    tags=["Help"],
    responses=ObservationRetrieveSerializer(many=True),
)
class MarkHelpAsResolvedView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, help_id):
        """
        Marks a help as resolved by updating its value_as_concept_id to the RESOLVED concept.
        """
        user = request.user

        logger.info(
            "Mark help as resolved requested",
            extra={"user_id": user.id, "help_id": help_id, "action": "mark_help_resolved_requested"},
        )

        try:
            help_observation = get_object_or_404(
                Observation,
                observation_id=help_id,
                observation_concept_id=get_concept_by_code("HELP").concept_id,
            )

            # Update the help observation to mark it as resolved
            help_observation.value_as_concept_id = get_concept_by_code("RESOLVED").concept_id
            help_observation.save(update_fields=["value_as_concept_id"])

            serializer = ObservationRetrieveSerializer(help_observation)

            logger.info(
                "Mark help as resolved completed successfully",
                extra={
                    "user_id": user.id,
                    "help_id": help_id,
                    "person_id": help_observation.person_id,
                    "action": "mark_help_resolved_success",
                },
            )

            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(
                "Error marking help as resolved",
                extra={"user_id": user.id, "help_id": help_id, "error": str(e), "action": "mark_help_resolved_error"},
                exc_info=True,
            )
            return Response({"error": "Failed to mark help as resolved"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    tags=["Diary"],
)
class DiaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        logger.info(
            "Diary retrieval requested",
            extra={
                "user_id": user.id,
                "limit": request.query_params.get("limit"),
                "action": "diary_retrieval_requested",
            },
        )

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

            logger.info(
                "Diary retrieval completed successfully",
                extra={
                    "user_id": user.id,
                    "diary_entries_count": len(diary_entries),
                    "limit_applied": limit,
                    "action": "diary_retrieval_success",
                },
            )

            return Response(serializer.data)

        except Exception as e:
            logger.error(
                "Error retrieving diaries",
                extra={"user_id": user.id, "error": str(e), "action": "diary_retrieval_error"},
                exc_info=True,
            )
            return Response({"error": "Failed to retrieve diaries"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        summary="Create a new diary for the logged-in user",
        request=DiaryCreateSerializer,
        responses={201: OpenApiTypes.OBJECT},
    )
    def post(self, request):
        user = request.user

        logger.info("Diary creation requested", extra={"user_id": user.id, "action": "diary_creation_requested"})

        try:
            serializer = DiaryCreateSerializer(data=request.data, context={"request": request})
            serializer.is_valid(raise_exception=True)
            result = serializer.save()

            logger.info(
                "Diary creation completed successfully",
                extra={"user_id": user.id, "diary_result": str(result), "action": "diary_creation_success"},
            )

            return Response(result, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(
                "Error creating diary",
                extra={"user_id": user.id, "error": str(e), "action": "diary_creation_error"},
                exc_info=True,
            )
            raise


@extend_schema(
    tags=["Diary"],
    responses=DiaryRetrieveSerializer(),
)
class DiaryDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, diary_id):
        user = request.user

        logger.info(
            "Diary detail retrieval requested",
            extra={"user_id": user.id, "diary_id": diary_id, "action": "diary_detail_requested"},
        )

        try:
            diary = get_object_or_404(
                Observation,
                observation_id=diary_id,
                observation_concept_id=get_concept_by_code("diary_entry").concept_id,
            )

            serializer = DiaryRetrieveSerializer(diary)

            logger.info(
                "Diary detail retrieval completed successfully",
                extra={
                    "user_id": user.id,
                    "diary_id": diary_id,
                    "person_id": diary.person_id,
                    "action": "diary_detail_success",
                },
            )

            return Response(serializer.data)

        except Exception as e:
            logger.error(
                "Error retrieving diary detail",
                extra={"user_id": user.id, "diary_id": diary_id, "error": str(e), "action": "diary_detail_error"},
                exc_info=True,
            )
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
        user = request.user

        logger.info(
            "Diary deletion requested",
            extra={"user_id": user.id, "diary_id": diary_id, "action": "diary_deletion_requested"},
        )

        try:
            serializer = DiaryDeleteSerializer()
            result = serializer.delete({"diary_id": diary_id})

            logger.info(
                "Diary deletion completed successfully",
                extra={"user_id": user.id, "diary_id": diary_id, "action": "diary_deletion_success"},
            )

            return Response(result, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(
                "Error deleting diary",
                extra={"user_id": user.id, "diary_id": diary_id, "error": str(e), "action": "diary_deletion_error"},
                exc_info=True,
            )
            raise


@extend_schema(
    tags=["Diary"],
    responses=DiaryRetrieveSerializer(many=True),
)
class PersonDiariesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        logger.info(
            "Person diaries retrieval requested", extra={"user_id": user.id, "action": "person_diaries_requested"}
        )

        try:
            person = get_object_or_404(Person, user=request.user)

            diaries = Observation.objects.filter(
                person=person, observation_concept_id=get_concept_by_code("diary_entry").concept_id
            ).order_by("-observation_date")

            serializer = DiaryRetrieveSerializer(diaries, many=True)

            logger.info(
                "Person diaries retrieval completed successfully",
                extra={
                    "user_id": user.id,
                    "person_id": person.person_id,
                    "diaries_count": len(diaries),
                    "action": "person_diaries_success",
                },
            )

            return Response(serializer.data)

        except Exception as e:
            logger.error(
                "Error retrieving person diaries",
                extra={"user_id": user.id, "error": str(e), "action": "person_diaries_error"},
                exc_info=True,
            )
            raise


@extend_schema(
    tags=["Provider"],
    responses=DiaryRetrieveSerializer(many=True),
)
class ProviderPersonDiariesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, person_id):
        user = request.user

        logger.info(
            "Provider person diaries retrieval requested",
            extra={"user_id": user.id, "person_id": person_id, "action": "provider_person_diaries_requested"},
        )

        try:
            provider, person = get_provider_and_linked_person_or_404(request.user, person_id)
            diaries = Observation.objects.filter(
                person=person,
                observation_concept_id=get_concept_by_code("diary_entry").concept_id,
                shared_with_provider=True,
            ).order_by("-observation_date")

            serializer = DiaryRetrieveSerializer(diaries, many=True)

            logger.info(
                "Provider person diaries retrieval completed successfully",
                extra={
                    "user_id": user.id,
                    "provider_id": provider.provider_id,
                    "person_id": person_id,
                    "shared_diaries_count": len(diaries),
                    "action": "provider_person_diaries_success",
                },
            )

            return Response(serializer.data)

        except Exception as e:
            logger.error(
                "Error retrieving provider person diaries",
                extra={
                    "user_id": user.id,
                    "person_id": person_id,
                    "error": str(e),
                    "action": "provider_person_diaries_error",
                },
                exc_info=True,
            )
            raise


@extend_schema(tags=["Provider"])
class ProviderPersonDiaryDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, person_id, diary_id):
        user = request.user

        logger.info(
            "Provider person diary detail requested",
            extra={
                "user_id": user.id,
                "person_id": person_id,
                "diary_id": diary_id,
                "action": "provider_person_diary_detail_requested",
            },
        )

        try:
            person = Person.objects.get(person_id=person_id)
            # Get the specific diary
            diary = get_object_or_404(
                Observation,
                observation_id=diary_id,
                person=person,
                observation_concept_id=get_concept_by_code("diary_entry").concept_id,
            )

            serializer = DiaryRetrieveSerializer(diary, context={"person_id": person.person_id})

            logger.info(
                "Provider person diary detail completed successfully",
                extra={
                    "user_id": user.id,
                    "person_id": person_id,
                    "diary_id": diary_id,
                    "action": "provider_person_diary_detail_success",
                },
            )

            return Response(serializer.data)

        except Exception as e:
            logger.error(
                "Error retrieving provider person diary detail",
                extra={
                    "user_id": user.id,
                    "person_id": person_id,
                    "diary_id": diary_id,
                    "error": str(e),
                    "action": "provider_person_diary_detail_error",
                },
                exc_info=True,
            )
            raise


@extend_schema(
    tags=["Interest_Areas"],
    request=InterestAreaSerializer,
    responses={201: InterestAreaRetrieveSerializer},
    parameters=[
        OpenApiParameter(name="person_id", description="Filter interest areas by person ID", required=False, type=int)
    ],
)
class InterestAreaViewSet(FlexibleViewSet):

    def get_queryset(self):
        queryset = Observation.objects.filter(observation_concept_id=get_concept_by_code("INTEREST_AREA").concept_id)

        person_id = self.request.query_params.get("person_id", None)
        if person_id:
            queryset = queryset.filter(person_id=person_id)

        return queryset

    @extend_schema(
        request=InterestAreaCreateSerializer,
    )
    def create(self, request):
        user = request.user

        logger.info(
            "Interest area creation requested", extra={"user_id": user.id, "action": "interest_area_creation_requested"}
        )

        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            instance = serializer.save()

            retrieve_serializer = InterestAreaRetrieveSerializer(instance)

            logger.info(
                "Interest area creation completed successfully",
                extra={
                    "user_id": user.id,
                    "interest_area_id": instance.observation_id,
                    "action": "interest_area_creation_success",
                },
            )

            return Response(retrieve_serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(
                "Error creating interest area",
                extra={"user_id": user.id, "error": str(e), "action": "interest_area_creation_error"},
                exc_info=True,
            )
            return Response(
                {
                    "error": "An error occurred while creating the interest area",
                    "details": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        request=InterestAreaUpdateSerializer,
    )
    def update(self, request, pk=None):
        user = request.user

        logger.info(
            "Interest area update requested",
            extra={"user_id": user.id, "interest_area_id": pk, "action": "interest_area_update_requested"},
        )

        try:
            interest_area = get_object_or_404(
                Observation, observation_id=pk, observation_concept=get_concept_by_code("INTEREST_AREA")
            )

            serializer = self.get_serializer(interest_area, data=request.data)
            serializer.is_valid(raise_exception=True)
            updated_instance = serializer.save()

            logger.info(
                "Interest area update completed successfully",
                extra={"user_id": user.id, "interest_area_id": pk, "action": "interest_area_update_success"},
            )

            return Response(InterestAreaRetrieveSerializer(updated_instance).data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(
                "Error updating interest area",
                extra={
                    "user_id": user.id,
                    "interest_area_id": pk,
                    "error": str(e),
                    "action": "interest_area_update_error",
                },
                exc_info=True,
            )
            raise


@extend_schema(
    tags=["Interest_Areas"],
    operation_id="markObservationAsAttentionPoint",
    description="Marcar área como ponto de atenção",
    request=MarkAttentionPointSerializer,
    responses={204: OpenApiTypes.OBJECT},
)
class MarkAttentionPointView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        user = request.user

        logger.info(
            "Mark attention point requested", extra={"user_id": user.id, "action": "mark_attention_point_requested"}
        )

        try:
            serializer = MarkAttentionPointSerializer(data=request.data, context={"request": request})
            serializer.is_valid(raise_exception=True)

            provider_name = get_provider_full_name(request.user.provider.provider_id)
            data = serializer.validated_data

            observation = get_object_or_404(Observation, observation_id=data["area_id"])
            interest_data = json.loads(observation.value_as_string) if observation.value_as_string else {}

            interest_data["marked_by"] = interest_data.get("marked_by", [])

            if data["is_attention_point"]:
                if provider_name not in interest_data["marked_by"]:
                    interest_data["marked_by"].append(provider_name)
            else:
                if provider_name in interest_data["marked_by"]:
                    interest_data["marked_by"].remove(provider_name)

            # Update the observation with the new interest data
            observation.value_as_string = json.dumps(interest_data, ensure_ascii=False)
            observation.save()

            logger.info(
                "Mark attention point completed successfully",
                extra={
                    "user_id": user.id,
                    "provider_name": provider_name,
                    "area_id": data["area_id"],
                    "is_attention_point": data["is_attention_point"],
                    "action": "mark_attention_point_success",
                },
            )

            return Response(
                {"provider_name": provider_name, "is_marked": data["is_attention_point"]}, status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.error(
                "Error marking attention point",
                extra={"user_id": user.id, "error": str(e), "action": "mark_attention_point_error"},
                exc_info=True,
            )
            return Response({"error": "Failed to mark attention point"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
