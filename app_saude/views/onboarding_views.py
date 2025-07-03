import logging

from django.contrib.auth import get_user_model
from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ..models import *
from ..serializers import *
from ..utils.provider import *
from .commons import FlexibleViewSet

User = get_user_model()
logger = logging.getLogger("app_saude")


@extend_schema(
    tags=["Complete Onboarding"],
    summary="Complete Person Onboarding",
    description="""
    Complete onboarding process for Person profiles with all required information.
    
    **Comprehensive Onboarding Features:**
    - Creates complete Person profile in single request
    - Validates all required personal information
    - Sets up initial preferences and settings
    - Links to authenticated user account
    - Performs full data validation and consistency checks
    
    **Business Rules:**
    - User must be authenticated
    - User cannot already have a Person profile
    - All required fields must be provided
    - Age validation and birth date consistency
    - Social name must be unique within system
    
    **Data Validation:**
    - Birth date vs age consistency
    - Required field completeness
    - Format validation for all inputs
    - Business rule compliance
    
    **Post-Onboarding:**
    - User gains access to Person features
    - Profile appears in search results
    - Can receive services from Providers
    - Preferences are immediately active
    """,
    request=FullPersonCreateSerializer,
    responses={
        201: {"description": "Person onboarding completed successfully"},
        400: {"description": "Validation error or duplicate registration"},
        401: {"description": "Authentication required"},
    },
)
class FullPersonViewSet(FlexibleViewSet):
    """
    Complete Person Onboarding

    Handles comprehensive Person profile creation with full validation
    and data consistency checks in a single atomic operation.
    """

    http_method_names = ["post"]  # only allow POST
    queryset = Person.objects.none()  # prevents GET from returning anything

    def create(self, request):
        user = request.user
        ip_address = request.META.get("REMOTE_ADDR", "Unknown")
        user_agent = request.META.get("HTTP_USER_AGENT", "Unknown")

        logger.info(
            "Full person onboarding initiated",
            extra={
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "request_data_size": len(str(request.data)),
                "request_fields": list(request.data.keys()) if request.data else [],
                "action": "full_person_onboarding_start",
            },
        )

        serializer: FullPersonCreateSerializer = self.get_serializer(data=request.data, context={"request": request})

        try:
            # Check for existing person registration with detailed logging
            existing_person = Person.objects.filter(user=request.user).first()
            if existing_person:
                logger.warning(
                    "Full person onboarding blocked - duplicate registration",
                    extra={
                        "user_id": user.id,
                        "existing_person_id": existing_person.person_id,
                        "existing_social_name": existing_person.social_name,
                        "existing_age": getattr(existing_person, "age", None),
                        "existing_created_date": (
                            existing_person.created_at.isoformat() if hasattr(existing_person, "created_at") else None
                        ),
                        "ip_address": ip_address,
                        "action": "full_person_onboarding_duplicate_blocked",
                    },
                )
                return Response(
                    {"error": "You already have a person registration."}, status=status.HTTP_400_BAD_REQUEST
                )

            # Validate serializer data
            if not serializer.is_valid():
                validation_errors = serializer.errors
                logger.warning(
                    "Full person onboarding validation failed",
                    extra={
                        "user_id": user.id,
                        "validation_errors": json.dumps(validation_errors, ensure_ascii=False),
                        "request_data_keys": list(request.data.keys()),
                        "ip_address": ip_address,
                        "action": "full_person_onboarding_validation_failed",
                    },
                )
                return Response(
                    {"error": "Validation failed", "details": validation_errors}, status=status.HTTP_400_BAD_REQUEST
                )

            logger.debug(
                "Full person onboarding data validated successfully",
                extra={
                    "user_id": user.id,
                    "data_fields": list(request.data.keys()),
                    "social_name": request.data.get("social_name"),
                    "age": request.data.get("age"),
                    "action": "full_person_onboarding_validated",
                },
            )

            # Create person with atomic transaction
            with transaction.atomic():
                logger.debug(
                    "Starting atomic transaction for person creation",
                    extra={"user_id": user.id, "action": "full_person_onboarding_transaction_start"},
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
                            created_person.birth_datetime.isoformat()
                            if hasattr(created_person, "birth_datetime") and created_person.birth_datetime
                            else None
                        ),
                        "use_dark_mode": getattr(created_person, "use_dark_mode", False),
                        "ip_address": ip_address,
                        "action": "full_person_onboarding_success",
                    },
                )

                return Response(
                    {"message": "Onboarding completed successfully", "person_id": created_person.person_id},
                    status=status.HTTP_201_CREATED,
                )

        except ValidationError as ve:
            logger.warning(
                "Full person onboarding validation failed with ValidationError",
                extra={
                    "user_id": user.id,
                    "validation_errors": str(ve),
                    "request_data_keys": list(request.data.keys()),
                    "ip_address": ip_address,
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
                    "error_type": type(e).__name__,
                    "request_data": request.data,
                    "ip_address": ip_address,
                    "action": "full_person_onboarding_critical_error",
                },
                exc_info=True,
            )
            return Response(
                {"error": "An unexpected error occurred during onboarding"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@extend_schema(
    tags=["Complete Onboarding"],
    summary="Complete Provider Registration",
    description="""
    Complete registration process for Provider profiles with user account creation.
    
    **Comprehensive Registration Features:**
    - Creates both User account and Provider profile
    - Validates professional credentials
    - Sets up complete provider information
    - Handles account activation and permissions
    - Atomic transaction ensures data consistency
    
    **Account Creation Process:**
    1. **User Validation**: Email uniqueness and format validation
    2. **Professional Validation**: Registration number verification
    3. **Profile Creation**: Complete provider profile setup
    4. **Account Activation**: User account setup with proper permissions
    5. **Relationship Setup**: Links user to provider profile
    
    **Professional Requirements:**
    - Valid email address (will become username)
    - Professional registration number (if applicable)
    - Specialty/service category specification
    - Complete contact information
    
    **Security Features:**
    - Password requirements enforcement
    - Email verification preparation
    - Professional credential validation
    - Duplicate registration prevention
    
    **Post-Registration:**
    - Provider can immediately start offering services
    - Profile appears in provider directories
    - Can generate link codes for person connections
    - Access to provider dashboard and features
    """,
    request=FullProviderCreateSerializer,
    responses={
        201: {"description": "Provider registration completed successfully"},
        400: {"description": "Validation error or duplicate registration"},
        500: {"description": "Server error during registration"},
    },
)
class FullProviderViewSet(FlexibleViewSet):
    """
    Complete Provider Registration

    Handles comprehensive Provider registration including user account creation
    and complete professional profile setup in atomic transactions.
    """

    http_method_names = ["post"]
    queryset = Provider.objects.none()
    permission_classes = [AllowAny]

    def create(self, request):
        ip_address = request.META.get("REMOTE_ADDR", "Unknown")
        user_agent = request.META.get("HTTP_USER_AGENT", "Unknown")
        email = request.data.get("email")
        professional_registration = request.data.get("professional_registration")

        logger.info(
            "Full provider registration initiated",
            extra={
                "ip_address": ip_address,
                "user_agent": user_agent,
                "email": email,
                "professional_registration": professional_registration,
                "specialty": request.data.get("specialty"),
                "request_data_size": len(str(request.data)),
                "request_fields": list(request.data.keys()) if request.data else [],
                "action": "full_provider_registration_start",
            },
        )

        serializer = self.get_serializer(data=request.data, context={"request": request})

        # Validate the data with detailed error logging
        if not serializer.is_valid():
            errors = serializer.errors
            logger.warning(
                "Full provider registration validation failed",
                extra={
                    "validation_errors": json.dumps(errors, ensure_ascii=False),
                    "email": email,
                    "professional_registration": professional_registration,
                    "request_data_keys": list(request.data.keys()),
                    "ip_address": ip_address,
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

        # Check for existing user with same email
        if User.objects.filter(email=email).exists():
            logger.warning(
                "Full provider registration blocked - email already exists",
                extra={
                    "email": email,
                    "ip_address": ip_address,
                    "action": "full_provider_registration_email_duplicate",
                },
            )
            return Response({"error": "User with this email already exists."}, status=status.HTTP_400_BAD_REQUEST)

        # Check for existing provider with same professional registration
        if (
            professional_registration
            and Provider.objects.filter(professional_registration=professional_registration).exists()
        ):
            logger.warning(
                "Full provider registration blocked - professional registration already exists",
                extra={
                    "professional_registration": professional_registration,
                    "email": email,
                    "ip_address": ip_address,
                    "action": "full_provider_registration_prof_reg_duplicate",
                },
            )
            return Response(
                {"error": "Provider with this professional registration already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            try:
                logger.debug(
                    "Starting atomic transaction for provider creation",
                    extra={
                        "email": email,
                        "professional_registration": professional_registration,
                        "action": "full_provider_registration_transaction_start",
                    },
                )

                result = serializer.save()
                response_data = ProviderRetrieveSerializer(result["provider"]).data

                # Log successful creation with comprehensive details
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
                        "use_dark_mode": getattr(provider, "use_dark_mode", False),
                        "is_active": user.is_active if user else None,
                        "ip_address": ip_address,
                        "action": "full_provider_registration_success",
                    },
                )

                return Response(
                    {
                        "message": "Provider created successfully",
                        "data": response_data,
                        "provider_id": provider.provider_id,
                    },
                    status=status.HTTP_201_CREATED,
                )

            except IntegrityError as ie:
                transaction.set_rollback(True)
                logger.error(
                    "Database integrity error during provider creation - transaction rolled back",
                    extra={
                        "error": str(ie),
                        "email": email,
                        "professional_registration": professional_registration,
                        "ip_address": ip_address,
                        "action": "full_provider_registration_integrity_error",
                    },
                    exc_info=True,
                )
                return Response(
                    {"error": "Registration data conflicts with existing records."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            except Exception as e:
                transaction.set_rollback(True)
                logger.error(
                    "Critical error during provider creation - transaction rolled back",
                    extra={
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "email": email,
                        "professional_registration": professional_registration,
                        "request_data": request.data,
                        "ip_address": ip_address,
                        "action": "full_provider_registration_critical_error",
                    },
                    exc_info=True,
                )
                return Response(
                    {"error": "Internal server error occurred during registration."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
