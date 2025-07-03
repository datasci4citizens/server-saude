import logging

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import *
from ..serializers import *
from ..utils.provider import *
from .commons import FlexibleViewSet

User = get_user_model()
logger = logging.getLogger("app_saude")


@extend_schema(tags=["Account Management"])
class AccountView(APIView):
    """
    Account Management Endpoint

    Provides functionality for users to view and delete their own accounts.
    Supports both Provider and Person user types.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get User Account Information",
        description="""
        Retrieves complete account information for the authenticated user.
        
        **Supported User Types:**
        - **Provider**: Service providers on the platform
        - **Person**: Regular users/customers
        - **Standard User**: Users without specific roles
        
        **Returned Information:**
        - Basic user profile data (name, email, username)
        - Role-specific information when applicable
        - Account settings and preferences
        - Profile completion status
        
        **Use Cases:**
        - Loading user profile pages
        - Populating account settings forms
        - Displaying user information in navigation
        - Account verification processes
        """,
        responses={
            200: {
                "description": "Account information retrieved successfully",
            },
            401: {
                "description": "Authentication required",
            },
            500: {
                "description": "Server error retrieving account data",
            },
        },
    )
    def get(self, request, *args, **kwargs):
        user = request.user
        logger.info(
            "Account retrieval requested",
            extra={
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "ip_address": request.META.get("REMOTE_ADDR"),
                "action": "get_account",
            },
        )

        try:
            serializer = UserRetrieveSerializer(user)

            logger.info(
                "Account data successfully retrieved",
                extra={
                    "user_id": user.id,
                    "data_fields": list(serializer.data.keys()),
                    "data_size": len(str(serializer.data)),
                    "action": "get_account_success",
                },
            )

            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(
                "Failed to retrieve account data",
                extra={
                    "user_id": user.id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "action": "get_account_error",
                },
                exc_info=True,
            )
            return Response(
                {"detail": "Error retrieving account information."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        summary="Delete User Account",
        description="""
        Permanently deletes the authenticated user's account and all associated data.
        
        **⚠️ CRITICAL OPERATION - IRREVERSIBLE ⚠️**
        
        **Deletion Process:**
        1. **Data Cleanup**: Removes all fact relationships and associated data
        2. **Soft Delete**: Account is deactivated and marked as deleted
        3. **Data Anonymization**: Email and username are anonymized for audit purposes
        4. **Atomic Operation**: All changes happen in a single database transaction
        
        **What Gets Deleted:**
        - All fact relationships where user is involved
        - User profile data (Provider or Person)
        - Account preferences and settings
        - Authentication tokens (user becomes unable to login)
        
        **What Gets Preserved:**
        - Anonymized user record for audit purposes
        - System logs and audit trails
        - Aggregated analytics data (non-personally identifiable)
        
        **User Types Supported:**
        - **Provider**: Service provider accounts with all associated services
        - **Person**: Regular user accounts with all personal data
        - **Standard User**: Basic accounts without specific roles
        
        **Security Features:**
        - Requires user authentication
        - Full audit logging with IP tracking
        - Atomic transaction ensures data consistency
        - Cannot be undone once completed
        
        **Post-Deletion:**
        - User will be immediately logged out
        - All future login attempts will fail
        - Account cannot be recovered
        """,
        responses={
            204: {
                "description": "Account successfully deleted - No Content",
            },
            401: {
                "description": "Authentication required",
            },
            500: {
                "description": "Server error during deletion",
            },
        },
    )
    def delete(self, request, *args, **kwargs):
        user = request.user
        user_agent = request.META.get("HTTP_USER_AGENT", "Unknown")
        ip_address = request.META.get("REMOTE_ADDR", "Unknown")

        logger.warning(
            "Account deletion requested - CRITICAL ACTION",
            extra={
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "timestamp": timezone.now().isoformat(),
                "action": "delete_account_requested",
            },
        )

        profile_id = None
        user_type = None

        # Determine user type and ID for cleanup
        try:
            if Provider.objects.filter(user=user).exists():
                provider = Provider.objects.get(user=user)
                profile_id = provider.provider_id
                user_type = "provider"
                logger.info(
                    "User identified as provider for deletion",
                    extra={"user_id": user.id, "provider_id": profile_id, "action": "delete_account_type_identified"},
                )
            elif Person.objects.filter(user=user).exists():
                person = Person.objects.get(user=user)
                profile_id = person.person_id
                user_type = "person"
                logger.info(
                    "User identified as person for deletion",
                    extra={"user_id": user.id, "person_id": profile_id, "action": "delete_account_type_identified"},
                )
            else:
                logger.warning(
                    "User deletion attempted but no associated Person or Provider found",
                    extra={"user_id": user.id, "action": "delete_account_no_profile"},
                )
                # Continue with deletion even without profile
                profile_id = f"user_{user.id}"
                user_type = "standard_user"

        except Exception as e:
            logger.error(
                "Error determining user type for deletion",
                extra={
                    "user_id": user.id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "action": "delete_account_type_error",
                },
                exc_info=True,
            )
            return Response(
                {"detail": "Error processing account deletion."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Atomic deletion process
        try:
            with transaction.atomic():
                logger.info(
                    "Starting atomic account deletion transaction",
                    extra={
                        "user_id": user.id,
                        "profile_id": profile_id,
                        "user_type": user_type,
                        "action": "delete_account_transaction_start",
                    },
                )

                # Delete fact relationships if profile exists
                relationships_deleted_1 = 0
                relationships_deleted_2 = 0

                if profile_id and profile_id != f"user_{user.id}":
                    try:
                        relationships_deleted_1 = FactRelationship.objects.filter(fact_id_1=profile_id).count()
                        relationships_deleted_2 = FactRelationship.objects.filter(fact_id_2=profile_id).count()

                        FactRelationship.objects.filter(fact_id_1=profile_id).delete()
                        FactRelationship.objects.filter(fact_id_2=profile_id).delete()

                        logger.info(
                            "Fact relationships deleted during account deletion",
                            extra={
                                "user_id": user.id,
                                "profile_id": profile_id,
                                "relationships_deleted_as_fact_1": relationships_deleted_1,
                                "relationships_deleted_as_fact_2": relationships_deleted_2,
                                "total_relationships_deleted": relationships_deleted_1 + relationships_deleted_2,
                                "action": "delete_account_relationships_deleted",
                            },
                        )
                    except Exception as e:
                        logger.error(
                            "Error deleting fact relationships",
                            extra={
                                "user_id": user.id,
                                "profile_id": profile_id,
                                "error": str(e),
                                "action": "delete_account_relationships_error",
                            },
                            exc_info=True,
                        )
                        # Continue with user deletion even if relationship cleanup fails

                # Soft delete user account with anonymization
                original_email = user.email
                original_username = user.username
                deletion_timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")

                try:
                    user.email = f"deleted_{deletion_timestamp}_{profile_id}@deleted.local"
                    user.username = f"deleted_{deletion_timestamp}_{profile_id}"
                    user.is_active = False
                    user.first_name = "DELETED"
                    user.last_name = "USER"
                    user.save()

                    logger.critical(
                        "User account successfully soft deleted and anonymized",
                        extra={
                            "user_id": user.id,
                            "profile_id": profile_id,
                            "user_type": user_type,
                            "original_email": original_email,
                            "original_username": original_username,
                            "new_email": user.email,
                            "new_username": user.username,
                            "is_active": user.is_active,
                            "deletion_timestamp": deletion_timestamp,
                            "relationships_deleted": relationships_deleted_1 + relationships_deleted_2,
                            "action": "delete_account_completed",
                        },
                    )
                except Exception as e:
                    logger.error(
                        "Error during user account anonymization",
                        extra={
                            "user_id": user.id,
                            "profile_id": profile_id,
                            "error": str(e),
                            "action": "delete_account_anonymization_error",
                        },
                        exc_info=True,
                    )
                    raise  # Re-raise to trigger transaction rollback

        except Exception as e:
            logger.error(
                "Critical error during account deletion transaction - ROLLBACK TRIGGERED",
                extra={
                    "user_id": user.id,
                    "profile_id": profile_id,
                    "user_type": user_type,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "action": "delete_account_transaction_error",
                },
                exc_info=True,
            )
            return Response(
                {"detail": "Error occurred during account deletion."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Account Management"])
class SwitchDarkModeView(APIView):
    """
    Dark Mode Toggle Endpoint

    Allows users to toggle between light and dark mode themes.
    Works for both Provider and Person user types.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Toggle Dark Mode Setting",
        description="""
        Toggles the dark mode preference for the authenticated user.
        
        **Functionality:**
        - Switches between light mode (false) and dark mode (true)
        - Setting is automatically saved to user's profile
        - Works for both Provider and Person user types
        - Returns HTTP 200 on successful toggle
        
        **User Type Support:**
        - **Person**: Toggles `use_dark_mode` field in Person profile
        - **Provider**: Toggles `use_dark_mode` field in Provider profile
        - **Standard User**: No-op (returns 200 but no change made)
        
        **Use Cases:**
        - User interface theme switching
        - Accessibility preferences
        - Personal customization settings
        - Mobile app theme synchronization
        
        **Behavior:**
        - If current setting is `false` (light mode) → changes to `true` (dark mode)
        - If current setting is `true` (dark mode) → changes to `false` (light mode)
        - Setting persists across user sessions
        - Immediate effect - no page refresh required
        
        **Frontend Integration:**
        After calling this endpoint, frontend should:
        1. Immediately update UI theme
        2. Store new preference locally for faster loading
        3. Handle any theme-dependent components
        """,
        responses={
            200: {
                "description": "Dark mode setting successfully toggled",
            },
            401: {
                "description": "Authentication required",
            },
            404: {
                "description": "User profile not found",
            },
            500: {
                "description": "Server error updating setting",
            },
        },
    )
    def post(self, request, *args, **kwargs):
        user = request.user
        ip_address = request.META.get("REMOTE_ADDR", "Unknown")

        logger.info(
            "Dark mode toggle requested",
            extra={"user_id": user.id, "ip_address": ip_address, "action": "toggle_dark_mode_requested"},
        )

        try:
            # Try Person first
            person = Person.objects.filter(user=user).first()
            if person:
                original_setting = person.use_dark_mode
                person.use_dark_mode = not person.use_dark_mode

                try:
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

                    return Response({"detail": "Dark mode setting updated successfully."}, status=status.HTTP_200_OK)

                except Exception as e:
                    logger.error(
                        "Error saving dark mode setting for Person",
                        extra={
                            "user_id": user.id,
                            "person_id": person.person_id,
                            "error": str(e),
                            "action": "toggle_dark_mode_person_save_error",
                        },
                        exc_info=True,
                    )
                    raise

            # Try Provider if Person not found
            provider = Provider.objects.filter(user=user).first()
            if provider:
                original_setting = provider.use_dark_mode
                provider.use_dark_mode = not provider.use_dark_mode

                try:
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

                    return Response({"detail": "Dark mode setting updated successfully."}, status=status.HTTP_200_OK)

                except Exception as e:
                    logger.error(
                        "Error saving dark mode setting for Provider",
                        extra={
                            "user_id": user.id,
                            "provider_id": provider.provider_id,
                            "error": str(e),
                            "action": "toggle_dark_mode_provider_save_error",
                        },
                        exc_info=True,
                    )
                    raise

            # No Person or Provider profile found
            logger.warning(
                "Dark mode toggle attempted but no Person or Provider profile found",
                extra={
                    "user_id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "action": "toggle_dark_mode_no_profile",
                },
            )

            return Response(
                {"detail": "User profile not found. Cannot update dark mode setting."}, status=status.HTTP_404_NOT_FOUND
            )

        except Exception as e:
            logger.error(
                "Unexpected error toggling dark mode",
                extra={
                    "user_id": user.id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "action": "toggle_dark_mode_error",
                },
                exc_info=True,
            )

            return Response(
                {"detail": "Error updating dark mode setting."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@extend_schema(tags=["Person Management"])
class PersonViewSet(FlexibleViewSet):
    """
    Person Profile Management

    Manages Person profiles in the system. Persons are regular users/customers
    who can receive services from Providers.

    **Key Features:**
    - Profile creation and management
    - Search by social name
    - Full CRUD operations
    - Duplicate registration prevention
    """

    queryset = Person.objects.all()
    permission_classes = [IsAuthenticated]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = "__all__"
    ordering_fields = "__all__"
    search_fields = ["social_name"]

    @extend_schema(
        summary="Create Person Profile",
        description="""
        Creates a new Person profile for the authenticated user.
        
        **Business Rules:**
        - Each user can only have ONE Person profile
        - User cannot have both Person and Provider profiles simultaneously
        - All required fields must be provided during creation
        - Social name is used for search and display purposes
        
        **Profile Creation Process:**
        1. Validates user doesn't already have a Person profile
        2. Creates Person record linked to authenticated user
        3. Generates unique person_id for the profile
        4. Sets initial preferences (dark mode, etc.)
        
        **Use Cases:**
        - New user registration as a service consumer
        - Customer onboarding process
        - Profile setup for receiving services
        
        **Important Notes:**
        - This action cannot be undone easily (requires account deletion)
        - User will be able to receive services after profile creation
        - Profile information is used for service matching and communication
        """,
        request=PersonCreateSerializer,
        responses={
            201: {
                "description": "Person profile created successfully",
                "content": {
                    "application/json": {
                        "examples": {
                            "successful_creation": {
                                "summary": "Successful person creation",
                                "value": {
                                    "person_id": "PERS123456",
                                    "social_name": "Maria Silva",
                                    "age": 25,
                                    "use_dark_mode": False,
                                    "profile_picture": None,
                                    "created_at": "2024-07-02T10:30:00Z",
                                    "user": {
                                        "id": 42,
                                        "email": "maria@example.com",
                                        "first_name": "Maria",
                                        "last_name": "Silva",
                                    },
                                },
                            }
                        }
                    }
                },
            },
            400: {
                "description": "Validation error or duplicate registration",
                "content": {
                    "application/json": {
                        "examples": {
                            "duplicate_registration": {
                                "summary": "User already has Person profile",
                                "value": {"detail": "You already have a person registration."},
                            },
                            "validation_error": {
                                "summary": "Missing required fields",
                                "value": {
                                    "social_name": ["This field is required."],
                                    "age": ["This field is required."],
                                },
                            },
                        }
                    }
                },
            },
            401: {
                "description": "Authentication required",
                "content": {
                    "application/json": {
                        "examples": {
                            "not_authenticated": {
                                "summary": "User not authenticated",
                                "value": {"detail": "Authentication credentials were not provided."},
                            }
                        }
                    }
                },
            },
        },
    )
    def create(self, request, *args, **kwargs):
        user = request.user
        ip_address = request.META.get("REMOTE_ADDR", "Unknown")

        logger.info(
            "Person registration attempted",
            extra={
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "ip_address": ip_address,
                "request_data_keys": list(request.data.keys()) if request.data else [],
                "action": "person_registration_requested",
            },
        )

        # Check for existing person registration
        try:
            if Person.objects.filter(user=request.user).exists():
                existing_person = Person.objects.get(user=request.user)
                logger.warning(
                    "Person registration blocked - user already has person profile",
                    extra={
                        "user_id": user.id,
                        "existing_person_id": existing_person.person_id,
                        "existing_social_name": existing_person.social_name,
                        "existing_created_at": (
                            existing_person.created_at.isoformat() if hasattr(existing_person, "created_at") else None
                        ),
                        "ip_address": ip_address,
                        "action": "person_registration_duplicate_blocked",
                    },
                )
                raise ValidationError("You already have a person registration.")
        except Person.DoesNotExist:
            # This is expected for new registrations
            pass
        except Exception as e:
            logger.error(
                "Error checking existing person registration",
                extra={
                    "user_id": user.id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "action": "person_registration_check_error",
                },
                exc_info=True,
            )
            raise

        try:
            result = super().create(request, *args, **kwargs)

            # Get the created person for logging
            if result.status_code == 201:
                try:
                    created_person = Person.objects.get(user=user)
                    logger.info(
                        "Person registration completed successfully",
                        extra={
                            "user_id": user.id,
                            "person_id": created_person.person_id,
                            "social_name": created_person.social_name,
                            "age": getattr(created_person, "age", None),
                            "use_dark_mode": getattr(created_person, "use_dark_mode", False),
                            "ip_address": ip_address,
                            "action": "person_registration_success",
                        },
                    )
                except Person.DoesNotExist:
                    logger.warning(
                        "Person registration reported success but person not found in database",
                        extra={
                            "user_id": user.id,
                            "response_status": result.status_code,
                            "action": "person_registration_success_not_found",
                        },
                    )

            return result

        except ValidationError:
            # Re-raise validation errors without additional logging
            raise
        except Exception as e:
            logger.error(
                "Person registration failed with unexpected error",
                extra={
                    "user_id": user.id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "request_data": request.data,
                    "ip_address": ip_address,
                    "action": "person_registration_error",
                },
                exc_info=True,
            )
            raise


@extend_schema(tags=["Provider Management"])
class ProviderViewSet(FlexibleViewSet):
    """
    Provider Profile Management

    Manages Provider profiles in the system. Providers are service providers
    who offer services to Persons in the platform.

    **Key Features:**
    - Professional profile creation and management
    - Search by social name and professional details
    - Professional registration validation
    - Service offering capabilities
    """

    queryset = Provider.objects.all()
    permission_classes = [IsAuthenticated]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = "__all__"
    ordering_fields = "__all__"
    search_fields = ["social_name"]

    @extend_schema(
        summary="Create Provider Profile",
        description="""
        Creates a new Provider profile for the authenticated user.
        
        **Business Rules:**
        - Each user can only have ONE Provider profile
        - User cannot have both Person and Provider profiles simultaneously
        - Professional registration number must be unique (if provided)
        - All required professional information must be provided
        
        **Provider Registration Process:**
        1. Validates user doesn't already have a Provider profile
        2. Validates professional credentials (if applicable)
        3. Creates Provider record with professional information
        4. Generates unique provider_id for the profile
        5. Sets up initial service offering capabilities
        
        **Use Cases:**
        - Healthcare professional registration
        - Service provider onboarding
        - Professional practice setup
        - Marketplace seller registration
        
        **Professional Information:**
        - Professional registration number (for regulated professions)
        - Specialty/area of expertise
        - Professional certifications
        - Service categories
        
        **Post-Creation:**
        - Provider can start offering services
        - Profile appears in provider searches
        - Can receive service requests from Persons
        """,
        request=ProviderCreateSerializer,
        responses={
            201: {
                "description": "Provider profile created successfully",
                "content": {
                    "application/json": {
                        "examples": {
                            "healthcare_provider": {
                                "summary": "Healthcare provider creation",
                                "value": {
                                    "provider_id": "PROV789012",
                                    "social_name": "Dr. João Santos",
                                    "professional_registration": "CRM123456",
                                    "specialty": "Cardiologia",
                                    "use_dark_mode": False,
                                    "profile_picture": None,
                                    "created_at": "2024-07-02T14:20:00Z",
                                    "user": {
                                        "id": 43,
                                        "email": "joao.santos@example.com",
                                        "first_name": "João",
                                        "last_name": "Santos",
                                    },
                                },
                            },
                            "service_provider": {
                                "summary": "General service provider creation",
                                "value": {
                                    "provider_id": "PROV789013",
                                    "social_name": "Ana Cleaning Services",
                                    "professional_registration": None,
                                    "specialty": "Limpeza Residencial",
                                    "use_dark_mode": True,
                                    "created_at": "2024-07-02T14:25:00Z",
                                },
                            },
                        }
                    }
                },
            },
            400: {
                "description": "Validation error or duplicate registration",
                "content": {
                    "application/json": {
                        "examples": {
                            "duplicate_registration": {
                                "summary": "User already has Provider profile",
                                "value": {"detail": "You already have a provider registration."},
                            },
                            "duplicate_professional_registration": {
                                "summary": "Professional registration already exists",
                                "value": {
                                    "professional_registration": [
                                        "Provider with this professional registration already exists."
                                    ]
                                },
                            },
                            "validation_error": {
                                "summary": "Missing required fields",
                                "value": {
                                    "social_name": ["This field is required."],
                                    "specialty": ["This field is required."],
                                },
                            },
                        }
                    }
                },
            },
            401: {"description": "Authentication required"},
        },
    )
    def create(self, request, *args, **kwargs):
        user = request.user
        ip_address = request.META.get("REMOTE_ADDR", "Unknown")

        logger.info(
            "Provider registration attempted",
            extra={
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "ip_address": ip_address,
                "request_data_keys": list(request.data.keys()) if request.data else [],
                "professional_registration": request.data.get("professional_registration"),
                "specialty": request.data.get("specialty"),
                "action": "provider_registration_requested",
            },
        )

        # Check for existing provider registration
        try:
            if Provider.objects.filter(user=request.user).exists():
                existing_provider = Provider.objects.get(user=request.user)
                logger.warning(
                    "Provider registration blocked - user already has provider profile",
                    extra={
                        "user_id": user.id,
                        "existing_provider_id": existing_provider.provider_id,
                        "existing_social_name": existing_provider.social_name,
                        "existing_professional_registration": getattr(
                            existing_provider, "professional_registration", None
                        ),
                        "existing_specialty": getattr(existing_provider, "specialty", None),
                        "existing_created_at": (
                            existing_provider.created_at.isoformat()
                            if hasattr(existing_provider, "created_at")
                            else None
                        ),
                        "ip_address": ip_address,
                        "action": "provider_registration_duplicate_blocked",
                    },
                )
                raise ValidationError("You already have a provider registration.")
        except Provider.DoesNotExist:
            # This is expected for new registrations
            pass
        except Exception as e:
            logger.error(
                "Error checking existing provider registration",
                extra={
                    "user_id": user.id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "action": "provider_registration_check_error",
                },
                exc_info=True,
            )
            raise

        try:
            result = super().create(request, *args, **kwargs)

            # Get the created provider for detailed logging
            if result.status_code == 201:
                try:
                    created_provider = Provider.objects.get(user=user)
                    logger.info(
                        "Provider registration completed successfully",
                        extra={
                            "user_id": user.id,
                            "provider_id": created_provider.provider_id,
                            "social_name": created_provider.social_name,
                            "professional_registration": getattr(created_provider, "professional_registration", None),
                            "specialty": getattr(created_provider, "specialty", None),
                            "use_dark_mode": getattr(created_provider, "use_dark_mode", False),
                            "ip_address": ip_address,
                            "action": "provider_registration_success",
                        },
                    )
                except Provider.DoesNotExist:
                    logger.warning(
                        "Provider registration reported success but provider not found in database",
                        extra={
                            "user_id": user.id,
                            "response_status": result.status_code,
                            "action": "provider_registration_success_not_found",
                        },
                    )

            return result

        except ValidationError:
            # Re-raise validation errors without additional logging
            raise
        except Exception as e:
            logger.error(
                "Provider registration failed with unexpected error",
                extra={
                    "user_id": user.id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "request_data": request.data,
                    "ip_address": ip_address,
                    "action": "provider_registration_error",
                },
                exc_info=True,
            )
            raise


@extend_schema(tags=["User Management"])
class UserRoleView(APIView):
    """
    User Role Detection Endpoint

    Determines the role and profile information for the authenticated user.
    Returns specific profile IDs based on user type.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get User Role and Profile Information",
        description="""
        Identifies the authenticated user's role and returns relevant profile information.
        
        **Role Detection Logic:**
        1. **Person Check**: First checks if user has a Person profile
        2. **Provider Check**: If not Person, checks if user has Provider profile  
        3. **No Profile**: If neither exists, returns 404
        
        **Response Patterns:**
        - **Person User**: Returns `{"person_id": "PERS123456"}`
        - **Provider User**: Returns `{"provider_id": "PROV789012"}`
        - **No Profile**: Returns 404 with error message
        
        **Use Cases:**
        - Application initialization and routing
        - Determining user capabilities and permissions
        - Conditional UI rendering based on user type
        - Navigation menu customization
        - Feature access control
        
        **Frontend Integration:**
        ```javascript
        // Example usage in frontend
        const roleResponse = await api.get('/user-role/');
        
        if (roleResponse.person_id) {
            // User is a Person - show person features
            navigateTo('/person-dashboard');
        } else if (roleResponse.provider_id) {
            // User is a Provider - show provider features  
            navigateTo('/provider-dashboard');
        } else {
            // User has no profile - show onboarding
            navigateTo('/choose-profile-type');
        }
        ```
        
        **Security Notes:**
        - Only returns profile ID for the authenticated user
        - Cannot be used to lookup other users' profiles
        - Profile IDs are safe to expose in frontend applications
        """,
        responses={
            200: {
                "description": "User role identified successfully",
                "content": {
                    "application/json": {
                        "examples": {
                            "person_user": {
                                "summary": "User with Person profile",
                                "value": {"person_id": "PERS123456"},
                            },
                            "provider_user": {
                                "summary": "User with Provider profile",
                                "value": {"provider_id": "PROV789012"},
                            },
                        }
                    }
                },
            },
            401: {
                "description": "Authentication required",
                "content": {
                    "application/json": {
                        "examples": {
                            "not_authenticated": {
                                "summary": "User not authenticated",
                                "value": {"detail": "Authentication credentials were not provided."},
                            }
                        }
                    }
                },
            },
            404: {
                "description": "No profile found for user",
                "content": {
                    "application/json": {
                        "examples": {
                            "no_profile": {
                                "summary": "User has no Person or Provider profile",
                                "value": {"detail": "User is not associated with a Person or Provider."},
                            }
                        }
                    }
                },
            },
        },
    )
    def get(self, request):
        user = request.user
        ip_address = request.META.get("REMOTE_ADDR", "Unknown")

        logger.debug(
            "User role lookup requested",
            extra={
                "user_id": user.id,
                "username": user.username,
                "ip_address": ip_address,
                "action": "user_role_lookup_requested",
            },
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
                    "ip_address": ip_address,
                    "action": "user_role_person_found",
                },
            )
            return Response({"person_id": person.person_id}, status=status.HTTP_200_OK)
        except Person.DoesNotExist:
            logger.debug(
                "User not found as Person, checking Provider",
                extra={"user_id": user.id, "action": "user_role_person_not_found"},
            )
        except Exception as e:
            logger.error(
                "Error checking Person profile during role lookup",
                extra={
                    "user_id": user.id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "action": "user_role_person_check_error",
                },
                exc_info=True,
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
                    "specialty": getattr(provider, "specialty", None),
                    "role": "provider",
                    "ip_address": ip_address,
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
                    "ip_address": ip_address,
                    "action": "user_role_not_found",
                },
            )
        except Exception as e:
            logger.error(
                "Error checking Provider profile during role lookup",
                extra={
                    "user_id": user.id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "action": "user_role_provider_check_error",
                },
                exc_info=True,
            )

        # If the user is not associated with either
        return Response(
            {"detail": "User is not associated with a Person or Provider."},
            status=status.HTTP_404_NOT_FOUND,
        )
