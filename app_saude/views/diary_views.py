import json
import logging

from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework import status
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


@extend_schema(
    tags=["Personal Diary"],
    summary="Manage Personal Diary Entries",
    description="""
    Personal diary management system for authenticated users.
    
    **GET - Retrieve Personal Diary Entries:**
    - Returns ONLY diary entries belonging to the authenticated user
    - Supports optional limit parameter for pagination
    - Ordered by most recent entries first
    - Complete access to personal diary content
    
    **POST - Create New Diary Entry:**
    - Creates personal diary entry for authenticated user
    - Supports text content, mood tracking, and sharing preferences
    - Automatically timestamps entries
    - Optional sharing with linked providers
    
    **Security:**
    - Users can only see their own diary entries
    - Private by default with optional provider sharing
    - Complete access control per user
    
    **Privacy Controls:**
    - Entries are private by default
    - User explicitly chooses which entries to share
    - Shared entries visible to linked providers only
    - User maintains full control over personal data
    """,
    parameters=[
        OpenApiParameter(
            name="limit",
            description="Maximum number of diary entries to return",
            required=False,
            type=int,
            examples=[
                OpenApiExample(name="First 10 entries", value=10),
                OpenApiExample(name="First 50 entries", value=50),
                OpenApiExample(name="All entries", value=None),
            ],
        )
    ],
)
class DiaryView(APIView):
    """
    Personal Diary Management

    Handles personal diary operations for the authenticated user only.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={
            200: DiaryRetrieveSerializer(many=True),
            404: {"description": "Person profile not found"},
            500: {"description": "Internal server error"},
        },
    )
    def get(self, request):
        user = request.user
        ip_address = request.META.get("REMOTE_ADDR", "Unknown")
        limit = request.query_params.get("limit")

        logger.info(
            "Personal diary retrieval requested",
            extra={
                "user_id": user.id,
                "limit": limit,
                "ip_address": ip_address,
                "action": "personal_diary_retrieval_requested",
            },
        )

        try:
            # Verify user has Person profile - SECURITY: Only Person users can access diaries
            person = get_object_or_404(Person, user=user)

            logger.debug(
                "Person verified for personal diary access",
                extra={
                    "user_id": user.id,
                    "person_id": person.person_id,
                    "person_name": person.social_name,
                    "action": "personal_diary_person_verified",
                },
            )

            # SECURITY: Filter by person to ensure user only sees their own diaries
            diary_entries_query = (
                Observation.objects.filter(
                    observation_concept_id=get_concept_by_code("diary_entry").concept_id,
                    person=person,  # CRITICAL: Only this person's diaries
                )
                .select_related("observation_concept")
                .order_by("-observation_date")
            )

            # Apply limit if provided and valid
            if limit and limit.isdigit():
                limit_int = int(limit)
                if limit_int > 0:
                    diary_entries_query = diary_entries_query[:limit_int]
                    logger.debug(
                        "Limit applied to personal diary query",
                        extra={
                            "user_id": user.id,
                            "limit_applied": limit_int,
                            "action": "personal_diary_limit_applied",
                        },
                    )

            diary_entries = list(diary_entries_query)

            # Calculate statistics
            total_entries = len(diary_entries)
            shared_entries = len([entry for entry in diary_entries if getattr(entry, "shared_with_provider", False)])

            serializer = DiaryRetrieveSerializer(diary_entries, many=True)

            logger.info(
                "Personal diary retrieval completed successfully",
                extra={
                    "user_id": user.id,
                    "person_id": person.person_id,
                    "diary_entries_count": total_entries,
                    "shared_entries_count": shared_entries,
                    "private_entries_count": total_entries - shared_entries,
                    "limit_applied": limit,
                    "ip_address": ip_address,
                    "action": "personal_diary_retrieval_success",
                },
            )

            return Response(serializer.data)

        except Http404:
            logger.warning(
                "Personal diary retrieval failed - person profile not found",
                extra={
                    "user_id": user.id,
                    "email": user.email,
                    "ip_address": ip_address,
                    "action": "personal_diary_no_person_profile",
                },
            )
            return Response({"error": "Person profile not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(
                "Error retrieving personal diaries",
                extra={
                    "user_id": user.id,
                    "limit": limit,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "ip_address": ip_address,
                    "action": "personal_diary_retrieval_error",
                },
                exc_info=True,
            )
            return Response(
                {"error": "An unexpected error occurred while retrieving diary entries."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        summary="Create New Personal Diary Entry",
        description="""
        Creates a new personal diary entry for the authenticated user.
        
        **Security Requirements:**
        - User must have valid Person profile
        - Entry is automatically linked to authenticated user
        - Cannot create entries for other users
        
        **Entry Creation Process:**
        1. **User Verification**: Confirms user has valid Person profile
        2. **Content Validation**: Validates diary content and metadata
        3. **Auto-Association**: Links entry to authenticated user's Person profile
        4. **Timestamp Assignment**: Automatically sets creation timestamp
        5. **Privacy Configuration**: Sets sharing preferences
        """,
        request=DiaryCreateSerializer,
        responses={
            201: {"description": "Diary entry created successfully"},
            400: {"description": "Validation error in diary entry data"},
            401: {"description": "Authentication required"},
            404: {"description": "Person profile not found"},
        },
    )
    def post(self, request):
        user = request.user
        ip_address = request.META.get("REMOTE_ADDR", "Unknown")

        logger.info(
            "Personal diary creation requested",
            extra={
                "user_id": user.id,
                "request_data_size": len(str(request.data)),
                "ip_address": ip_address,
                "action": "personal_diary_creation_requested",
            },
        )

        try:
            # SECURITY: Verify user has Person profile
            person = get_object_or_404(Person, user=user)

            logger.debug(
                "Person verified for diary creation",
                extra={
                    "user_id": user.id,
                    "person_id": person.person_id,
                    "person_name": person.social_name,
                    "action": "personal_diary_creation_person_verified",
                },
            )

            serializer = DiaryCreateSerializer(data=request.data, context={"request": request})

            if not serializer.is_valid():
                logger.warning(
                    "Personal diary creation validation failed",
                    extra={
                        "user_id": user.id,
                        "person_id": person.person_id,
                        "validation_errors": json.dumps(serializer.errors, ensure_ascii=False),
                        "ip_address": ip_address,
                        "action": "personal_diary_creation_validation_failed",
                    },
                )
                return Response(
                    {"error": "Validation failed", "details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
                )

            # Create diary entry with atomic transaction
            with transaction.atomic():
                result = serializer.save()

                logger.info(
                    "Personal diary creation completed successfully",
                    extra={
                        "user_id": user.id,
                        "person_id": person.person_id,
                        "person_name": person.social_name,
                        "diary_result": str(result),
                        "entry_shared": result.get("shared_with_provider", False) if isinstance(result, dict) else None,
                        "creation_timestamp": timezone.now().isoformat(),
                        "ip_address": ip_address,
                        "action": "personal_diary_creation_success",
                    },
                )

                return Response(result, status=status.HTTP_201_CREATED)

        except Http404:
            logger.warning(
                "Personal diary creation failed - person profile not found",
                extra={
                    "user_id": user.id,
                    "email": user.email,
                    "ip_address": ip_address,
                    "action": "personal_diary_creation_no_person_profile",
                },
            )
            return Response({"error": "Person profile not found."}, status=status.HTTP_404_NOT_FOUND)
        except ValidationError as ve:
            logger.warning(
                "Personal diary creation validation error",
                extra={
                    "user_id": user.id,
                    "validation_error": str(ve),
                    "ip_address": ip_address,
                    "action": "personal_diary_creation_validation_error",
                },
            )
            return Response({"error": str(ve)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(
                "Error creating personal diary",
                extra={
                    "user_id": user.id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "request_data": request.data,
                    "ip_address": ip_address,
                    "action": "personal_diary_creation_error",
                },
                exc_info=True,
            )
            return Response(
                {"error": "An unexpected error occurred while creating diary entry."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@extend_schema(
    tags=["Personal Diary"],
    summary="Personal Diary Entry Details and Management",
    description="""
    Individual diary entry operations with strict ownership validation.
    
    **GET - View Personal Diary Entry:**
    - Retrieves complete details of user's own diary entry
    - Validates entry belongs to authenticated user
    - Includes all metadata, content, and sharing status
    
    **DELETE - Remove Personal Diary Entry:**
    - Permanently deletes user's own diary entry
    - Validates ownership before deletion
    - Cannot delete other users' entries
    - Audit logging for deletion tracking
    
    **Security Requirements:**
    - User must own the diary entry
    - Entry must exist and be accessible to user
    - Cannot access other users' diary entries
    """,
    responses={
        200: DiaryRetrieveSerializer,
        403: {"description": "Access denied - not your diary entry"},
        404: {"description": "Diary entry not found"},
        401: {"description": "Authentication required"},
    },
)
class DiaryDetailView(APIView):
    """
    Personal Diary Entry Management with Ownership Validation

    Handles operations on user's own diary entries with strict access control.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, diary_id):
        user = request.user
        ip_address = request.META.get("REMOTE_ADDR", "Unknown")

        logger.info(
            "Personal diary detail retrieval requested",
            extra={
                "user_id": user.id,
                "diary_id": diary_id,
                "ip_address": ip_address,
                "action": "personal_diary_detail_requested",
            },
        )

        try:
            # SECURITY: Verify user has Person profile
            person = get_object_or_404(Person, user=user)

            # SECURITY: Get diary entry and verify ownership
            diary = get_object_or_404(
                Observation,
                observation_id=diary_id,
                observation_concept_id=get_concept_by_code("diary_entry").concept_id,
                person=person,  # CRITICAL: Must belong to this person
            )

            logger.debug(
                "Personal diary entry found and ownership verified",
                extra={
                    "user_id": user.id,
                    "person_id": person.person_id,
                    "diary_id": diary_id,
                    "diary_date": diary.observation_date.isoformat() if diary.observation_date else None,
                    "shared_with_provider": getattr(diary, "shared_with_provider", False),
                    "action": "personal_diary_detail_found",
                },
            )

            serializer = DiaryRetrieveSerializer(diary)

            logger.info(
                "Personal diary detail retrieval completed successfully",
                extra={
                    "user_id": user.id,
                    "person_id": person.person_id,
                    "diary_id": diary_id,
                    "diary_date": diary.observation_date.isoformat() if diary.observation_date else None,
                    "content_length": len(diary.value_as_string) if diary.value_as_string else 0,
                    "ip_address": ip_address,
                    "action": "personal_diary_detail_success",
                },
            )

            return Response(serializer.data)

        except Http404:
            logger.warning(
                "Personal diary detail access denied - not found or not owned by user",
                extra={
                    "user_id": user.id,
                    "diary_id": diary_id,
                    "ip_address": ip_address,
                    "action": "personal_diary_detail_access_denied",
                },
            )
            return Response(
                {"error": "Diary entry not found or you don't have permission to access it."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(
                "Error retrieving personal diary detail",
                extra={
                    "user_id": user.id,
                    "diary_id": diary_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "ip_address": ip_address,
                    "action": "personal_diary_detail_error",
                },
                exc_info=True,
            )
            return Response(
                {"error": "An unexpected error occurred while retrieving diary entry."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        summary="Delete Personal Diary Entry",
        description="""
        Permanently deletes user's own diary entry with ownership validation.
        
        **⚠️ PERMANENT ACTION - CANNOT BE UNDONE ⚠️**
        
        **Security Process:**
        1. **User Verification**: Confirms user has Person profile
        2. **Ownership Validation**: Verifies diary belongs to user
        3. **Permission Check**: Ensures user can delete this entry
        4. **Permanent Removal**: Deletes entry from database
        5. **Audit Logging**: Records deletion for compliance
        """,
        responses={
            200: {"description": "Diary entry deleted successfully"},
            403: {"description": "Access denied - not your diary entry"},
            404: {"description": "Diary entry not found"},
            401: {"description": "Authentication required"},
        },
        parameters=[
            OpenApiParameter(
                name="diary_id",
                type=int,
                location=OpenApiParameter.PATH,
                description="Unique identifier of your diary entry to delete",
                examples=[OpenApiExample(name="Valid diary ID", value=12345)],
            )
        ],
    )
    def delete(self, request, diary_id):
        user = request.user
        ip_address = request.META.get("REMOTE_ADDR", "Unknown")
        user_agent = request.META.get("HTTP_USER_AGENT", "Unknown")

        logger.warning(
            "Personal diary deletion requested - PERMANENT ACTION",
            extra={
                "user_id": user.id,
                "diary_id": diary_id,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "timestamp": timezone.now().isoformat(),
                "action": "personal_diary_deletion_requested",
            },
        )

        try:
            # SECURITY: Verify user has Person profile
            person = get_object_or_404(Person, user=user)

            # SECURITY: Verify diary exists and belongs to user
            diary = get_object_or_404(
                Observation,
                observation_id=diary_id,
                observation_concept_id=get_concept_by_code("diary_entry").concept_id,
                person=person,  # CRITICAL: Must belong to this person
            )

            # Store details for logging before deletion
            diary_date = diary.observation_date
            content_preview = (
                (diary.value_as_string[:100] + "...")
                if diary.value_as_string and len(diary.value_as_string) > 100
                else diary.value_as_string
            )

            logger.info(
                "Personal diary entry identified for deletion with ownership verified",
                extra={
                    "user_id": user.id,
                    "person_id": person.person_id,
                    "diary_id": diary_id,
                    "diary_date": diary_date.isoformat() if diary_date else None,
                    "content_preview": content_preview,
                    "action": "personal_diary_deletion_identified",
                },
            )

            # Perform deletion using serializer
            serializer = DiaryDeleteSerializer()
            result = serializer.delete({"diary_id": diary_id})

            logger.critical(
                "Personal diary deletion completed successfully",
                extra={
                    "user_id": user.id,
                    "person_id": person.person_id,
                    "diary_id": diary_id,
                    "deleted_diary_date": diary_date.isoformat() if diary_date else None,
                    "deletion_timestamp": timezone.now().isoformat(),
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                    "action": "personal_diary_deletion_success",
                },
            )

            return Response(result, status=status.HTTP_200_OK)

        except Http404:
            logger.warning(
                "Personal diary deletion failed - not found or access denied",
                extra={
                    "user_id": user.id,
                    "diary_id": diary_id,
                    "ip_address": ip_address,
                    "action": "personal_diary_deletion_access_denied",
                },
            )
            return Response(
                {"error": "Diary entry not found or you don't have permission to delete it."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(
                "Error deleting personal diary",
                extra={
                    "user_id": user.id,
                    "diary_id": diary_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "ip_address": ip_address,
                    "action": "personal_diary_deletion_error",
                },
                exc_info=True,
            )
            return Response(
                {"error": "An unexpected error occurred while deleting diary entry."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@extend_schema(
    tags=["Personal Diary"],
    summary="Get Personal Diary Entries (Alternative Endpoint)",
    description="""
    Alternative endpoint for retrieving personal diary entries.
    
    **Functionality:**
    - Returns only diary entries belonging to the authenticated Person
    - Includes both private and shared entries
    - Ordered chronologically (most recent first)
    - Complete access to all personal diary content
    
    **Security:**
    - Strict ownership validation
    - Cannot access other users' diaries
    - Person profile required
    """,
    responses={
        200: DiaryRetrieveSerializer(many=True),
        401: {"description": "Authentication required"},
        404: {"description": "Person profile not found"},
    },
)
class PersonDiariesView(APIView):
    """
    Personal Diary Entries (Alternative Endpoint)

    Manages diary entries for the authenticated person with strict access control.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        ip_address = request.META.get("REMOTE_ADDR", "Unknown")

        logger.info(
            "Person diaries retrieval requested",
            extra={"user_id": user.id, "ip_address": ip_address, "action": "person_diaries_requested"},
        )

        try:
            # SECURITY: Verify user has Person profile
            person = get_object_or_404(Person, user=request.user)

            logger.debug(
                "Person identified for diary retrieval",
                extra={
                    "user_id": user.id,
                    "person_id": person.person_id,
                    "person_name": person.social_name,
                    "action": "person_diaries_person_identified",
                },
            )

            # SECURITY: Get only this person's diary entries
            diaries = (
                Observation.objects.filter(
                    person=person,  # CRITICAL: Only this person's diaries
                    observation_concept_id=get_concept_by_code("diary_entry").concept_id,
                )
                .select_related("observation_concept")
                .order_by("-observation_date")
            )

            # Calculate statistics
            total_entries = diaries.count()
            shared_entries = diaries.filter(shared_with_provider=True).count()
            private_entries = total_entries - shared_entries

            # Get date range if entries exist
            date_range = None
            if total_entries > 0:
                earliest = diaries.last().observation_date
                latest = diaries.first().observation_date
                date_range = {
                    "earliest": earliest.isoformat() if earliest else None,
                    "latest": latest.isoformat() if latest else None,
                }

            serializer = DiaryRetrieveSerializer(diaries, many=True)

            logger.info(
                "Person diaries retrieval completed successfully",
                extra={
                    "user_id": user.id,
                    "person_id": person.person_id,
                    "person_name": person.social_name,
                    "total_diaries_count": total_entries,
                    "shared_diaries_count": shared_entries,
                    "private_diaries_count": private_entries,
                    "date_range": date_range,
                    "ip_address": ip_address,
                    "action": "person_diaries_success",
                },
            )

            return Response(serializer.data)

        except Http404:
            logger.warning(
                "Person diaries retrieval failed - person profile not found",
                extra={
                    "user_id": user.id,
                    "email": user.email,
                    "ip_address": ip_address,
                    "action": "person_diaries_no_person_profile",
                },
            )
            return Response({"error": "Person profile not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(
                "Error retrieving person diaries",
                extra={
                    "user_id": user.id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "ip_address": ip_address,
                    "action": "person_diaries_error",
                },
                exc_info=True,
            )
            return Response(
                {"error": "An unexpected error occurred while retrieving diary entries."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@extend_schema(
    tags=["Provider Diary Access"],
    summary="Get Person's Shared Diary Entries",
    description="""
    Retrieves diary entries shared by a specific Person with the authenticated Provider.
    
    **Security Requirements:**
    - Provider must be authenticated and have valid Provider profile
    - Provider must be linked to the specified Person
    - Only entries explicitly shared with providers are returned
    - Strict validation of Provider-Person relationship
    
    **Access Control:**
    - Validates Provider-Person relationship exists
    - Filters out private/unshared diary entries
    - Cannot access entries from non-linked Persons
    - Ensures proper authorization for diary access
    """,
    responses={
        200: DiaryRetrieveSerializer(many=True),
        401: {"description": "Authentication required"},
        403: {"description": "Provider not linked to specified Person"},
        404: {"description": "Provider profile or Person not found"},
    },
)
class ProviderPersonDiariesView(APIView):
    """
    Provider Access to Person's Shared Diaries

    Allows providers to view diary entries shared by linked persons only.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, person_id):
        user = request.user
        ip_address = request.META.get("REMOTE_ADDR", "Unknown")

        logger.info(
            "Provider person diaries retrieval requested",
            extra={
                "user_id": user.id,
                "person_id": person_id,
                "ip_address": ip_address,
                "action": "provider_person_diaries_requested",
            },
        )

        try:
            # SECURITY: Validate provider and person relationship
            provider, person = get_provider_and_linked_person_or_404(request.user, person_id)

            logger.debug(
                "Provider-Person relationship validated for diary access",
                extra={
                    "user_id": user.id,
                    "provider_id": provider.provider_id,
                    "provider_name": provider.social_name,
                    "person_id": person_id,
                    "person_name": person.social_name,
                    "action": "provider_person_diaries_relationship_validated",
                },
            )

            # SECURITY: Get only shared diary entries from this specific person
            diaries = (
                Observation.objects.filter(
                    person=person,  # CRITICAL: Only this specific person's diaries
                    observation_concept_id=get_concept_by_code("diary_entry").concept_id,
                    shared_with_provider=True,  # CRITICAL: Only shared entries
                )
                .select_related("observation_concept", "person__user")
                .order_by("-observation_date")
            )

            # Calculate statistics
            shared_count = diaries.count()

            # Get date range for shared entries
            date_range = None
            if shared_count > 0:
                earliest = diaries.last().observation_date
                latest = diaries.first().observation_date
                date_range = {
                    "earliest": earliest.isoformat() if earliest else None,
                    "latest": latest.isoformat() if latest else None,
                }

            serializer = DiaryRetrieveSerializer(diaries, many=True)

            logger.info(
                "Provider person diaries retrieval completed successfully",
                extra={
                    "user_id": user.id,
                    "provider_id": provider.provider_id,
                    "provider_name": provider.social_name,
                    "person_id": person_id,
                    "person_name": person.social_name,
                    "shared_diaries_count": shared_count,
                    "date_range": date_range,
                    "access_type": "shared_only",
                    "ip_address": ip_address,
                    "action": "provider_person_diaries_success",
                },
            )

            return Response(serializer.data)

        except Http404 as e:
            logger.warning(
                "Provider person diaries access failed - relationship not found",
                extra={
                    "user_id": user.id,
                    "person_id": person_id,
                    "error": str(e),
                    "ip_address": ip_address,
                    "action": "provider_person_diaries_not_found",
                },
            )
            return Response(
                {"error": "Provider-Person relationship not found or person does not exist."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(
                "Error retrieving provider person diaries",
                extra={
                    "user_id": user.id,
                    "person_id": person_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "ip_address": ip_address,
                    "action": "provider_person_diaries_error",
                },
                exc_info=True,
            )
            return Response(
                {"error": "An unexpected error occurred while retrieving shared diary entries."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@extend_schema(
    tags=["Provider Diary Access"],
    summary="Get Specific Shared Diary Entry",
    description="""
    Retrieves details of a specific diary entry shared by a Person with the Provider.
    
    **Multi-Layer Security Validation:**
    1. **Provider Authentication**: User must be authenticated Provider
    2. **Person Existence**: Specified Person must exist
    3. **Relationship Validation**: Provider must be linked to Person
    4. **Entry Ownership**: Diary must belong to specified Person
    5. **Sharing Permission**: Entry must be marked as shared with providers
    
    **Access Control Flow:**
    - Validates Provider has valid profile
    - Confirms Person exists in system
    - Verifies active Provider-Person relationship
    - Ensures diary belongs to specified Person
    - Checks entry is explicitly shared with providers
    """,
    responses={
        200: DiaryRetrieveSerializer,
        401: {"description": "Authentication required"},
        403: {"description": "Provider not authorized to view this entry"},
        404: {"description": "Diary entry not found or not shared"},
    },
)
class ProviderPersonDiaryDetailView(APIView):
    """
    Provider Access to Specific Shared Diary Entry

    Provides detailed view of individual shared diary entries with strict validation.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, person_id, diary_id):
        user = request.user
        ip_address = request.META.get("REMOTE_ADDR", "Unknown")

        logger.info(
            "Provider person diary detail requested",
            extra={
                "user_id": user.id,
                "person_id": person_id,
                "diary_id": diary_id,
                "ip_address": ip_address,
                "action": "provider_person_diary_detail_requested",
            },
        )

        try:
            # SECURITY: Verify provider has valid profile
            provider = get_object_or_404(Provider, user=request.user)

            logger.debug(
                "Provider verified for diary detail access",
                extra={
                    "user_id": user.id,
                    "provider_id": provider.provider_id,
                    "provider_name": provider.social_name,
                    "person_id": person_id,
                    "diary_id": diary_id,
                    "action": "provider_person_diary_detail_provider_verified",
                },
            )

            # SECURITY: Get the person and validate they exist
            person = get_object_or_404(Person, person_id=person_id)

            # SECURITY: Validate Provider-Person relationship exists
            relationship_exists = FactRelationship.objects.filter(
                fact_id_1=person.person_id,
                domain_concept_1_id=get_concept_by_code("PERSON").concept_id,
                fact_id_2=provider.provider_id,
                domain_concept_2_id=get_concept_by_code("PROVIDER").concept_id,
                relationship_concept_id=get_concept_by_code("PERSON_PROVIDER").concept_id,
            ).exists()

            if not relationship_exists:
                logger.warning(
                    "Provider person diary detail access denied - no relationship",
                    extra={
                        "user_id": user.id,
                        "provider_id": provider.provider_id,
                        "person_id": person_id,
                        "diary_id": diary_id,
                        "action": "provider_person_diary_detail_no_relationship",
                    },
                )
                return Response({"error": "Provider is not linked to this person."}, status=status.HTTP_403_FORBIDDEN)

            # SECURITY: Get the specific diary entry with all validations
            diary = get_object_or_404(
                Observation,
                observation_id=diary_id,
                person=person,  # CRITICAL: Must belong to specified person
                observation_concept_id=get_concept_by_code("diary_entry").concept_id,
                shared_with_provider=True,  # CRITICAL: Only shared entries accessible
            )

            logger.debug(
                "Shared diary entry found for provider access with all validations passed",
                extra={
                    "user_id": user.id,
                    "provider_id": provider.provider_id,
                    "person_id": person_id,
                    "diary_id": diary_id,
                    "diary_person_id": diary.person_id,
                    "diary_date": diary.observation_date.isoformat() if diary.observation_date else None,
                    "content_length": len(diary.value_as_string) if diary.value_as_string else 0,
                    "action": "provider_person_diary_detail_found",
                },
            )

            serializer = DiaryRetrieveSerializer(diary, context={"person_id": person.person_id})

            logger.info(
                "Provider person diary detail completed successfully",
                extra={
                    "user_id": user.id,
                    "provider_id": provider.provider_id,
                    "provider_name": provider.social_name,
                    "person_id": person_id,
                    "person_name": person.social_name,
                    "diary_id": diary_id,
                    "diary_date": diary.observation_date.isoformat() if diary.observation_date else None,
                    "access_type": "shared_entry_validated",
                    "ip_address": ip_address,
                    "action": "provider_person_diary_detail_success",
                },
            )

            return Response(serializer.data)

        except Http404 as e:
            logger.warning(
                "Provider person diary detail not found or access denied",
                extra={
                    "user_id": user.id,
                    "person_id": person_id,
                    "diary_id": diary_id,
                    "error": str(e),
                    "ip_address": ip_address,
                    "action": "provider_person_diary_detail_not_found",
                },
            )
            return Response(
                {"error": "Diary entry not found, not shared, person not found, or you don't have access."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(
                "Error retrieving provider person diary detail",
                extra={
                    "user_id": user.id,
                    "person_id": person_id,
                    "diary_id": diary_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "ip_address": ip_address,
                    "action": "provider_person_diary_detail_error",
                },
                exc_info=True,
            )
            return Response(
                {"error": "An unexpected error occurred while retrieving diary entry."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@extend_schema(
    tags=["Interest Areas"],
    summary="Interest Area Management",
    description="""
    Personal interest area management with strict access control.
    
    **Security Requirements:**
    - User must have valid Person profile to manage interest areas
    - Users can only access their own interest areas
    - Filtering by person_id restricts to authenticated user's data
    
    **Access Control:**
    - Person profile validation required
    - Interest areas filtered by authenticated user
    - Cannot access other users' interest areas
    """,
    parameters=[
        OpenApiParameter(
            name="person_id",
            description="Filter interest areas by person ID (restricted to your own)",
            required=False,
            type=int,
            examples=[
                OpenApiExample(name="Your person ID", value=12345),
            ],
        )
    ],
)
class InterestAreaViewSet(FlexibleViewSet):
    """
    Interest Area Management ViewSet with Security

    Handles CRUD operations for user interest areas with strict access control.
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Build securely filtered queryset for interest areas.
        """
        try:
            # SECURITY: Verify user has Person profile
            person = get_object_or_404(Person, user=self.request.user)

            # SECURITY: Base queryset filtered by authenticated user's person
            queryset = (
                Observation.objects.filter(
                    observation_concept_id=get_concept_by_code("INTEREST_AREA").concept_id,
                    person=person,  # CRITICAL: Only this person's interest areas
                )
                .select_related("person__user", "observation_concept")
                .order_by("-observation_date")
            )

            # Additional filtering by person_id (redundant but explicit)
            person_id = self.request.query_params.get("person_id", None)
            if person_id:
                # SECURITY: Ensure person_id matches authenticated user's person
                if str(person.person_id) != str(person_id):
                    logger.warning(
                        "Interest area access denied - person_id mismatch",
                        extra={
                            "user_id": self.request.user.id,
                            "user_person_id": person.person_id,
                            "requested_person_id": person_id,
                            "action": "interest_area_person_id_mismatch",
                        },
                    )
                    return Observation.objects.none()  # Return empty queryset

                logger.debug(
                    "Interest area queryset confirmed for authenticated user",
                    extra={
                        "user_id": self.request.user.id,
                        "person_id": person_id,
                        "filtered_count": queryset.count(),
                        "action": "interest_area_person_filter_validated",
                    },
                )

            return queryset

        except Http404:
            logger.warning(
                "Interest area access denied - no person profile",
                extra={"user_id": getattr(self.request.user, "id", None), "action": "interest_area_no_person_profile"},
            )
            return Observation.objects.none()
        except Exception as e:
            logger.error(
                "Error building interest area queryset",
                extra={
                    "user_id": getattr(self.request.user, "id", None),
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "action": "interest_area_queryset_error",
                },
                exc_info=True,
            )
            return Observation.objects.none()

    @extend_schema(
        summary="Create New Personal Interest Area",
        description="""
        Creates a new interest area for the authenticated user only.
        
        **Security Features:**
        - Automatically associates with authenticated user's Person profile
        - Cannot create interest areas for other users
        - Person profile validation required
        """,
        request=InterestAreaCreateSerializer,
        responses={
            201: InterestAreaRetrieveSerializer,
            400: {"description": "Validation error in interest area data"},
            401: {"description": "Authentication required"},
            404: {"description": "Person profile not found"},
        },
    )
    def create(self, request):
        user = request.user
        ip_address = request.META.get("REMOTE_ADDR", "Unknown")

        logger.info(
            "Personal interest area creation requested",
            extra={
                "user_id": user.id,
                "request_data_size": len(str(request.data)),
                "ip_address": ip_address,
                "action": "personal_interest_area_creation_requested",
            },
        )

        try:
            # SECURITY: Verify user has Person profile
            person = get_object_or_404(Person, user=user)

            logger.debug(
                "Person verified for interest area creation",
                extra={
                    "user_id": user.id,
                    "person_id": person.person_id,
                    "person_name": person.social_name,
                    "action": "personal_interest_area_creation_person_verified",
                },
            )

            serializer = self.get_serializer(data=request.data)

            if not serializer.is_valid():
                logger.warning(
                    "Personal interest area creation validation failed",
                    extra={
                        "user_id": user.id,
                        "person_id": person.person_id,
                        "validation_errors": json.dumps(serializer.errors, ensure_ascii=False),
                        "ip_address": ip_address,
                        "action": "personal_interest_area_creation_validation_failed",
                    },
                )
                return Response(
                    {"error": "Validation failed", "details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
                )

            # Create interest area with atomic transaction
            with transaction.atomic():
                instance = serializer.save()
                retrieve_serializer = InterestAreaRetrieveSerializer(instance)

                logger.info(
                    "Personal interest area creation completed successfully",
                    extra={
                        "user_id": user.id,
                        "person_id": person.person_id,
                        "person_name": person.social_name,
                        "interest_area_id": instance.observation_id,
                        "interest_content": instance.value_as_string[:100] if instance.value_as_string else None,
                        "creation_timestamp": timezone.now().isoformat(),
                        "ip_address": ip_address,
                        "action": "personal_interest_area_creation_success",
                    },
                )

                return Response(retrieve_serializer.data, status=status.HTTP_201_CREATED)

        except Http404:
            logger.warning(
                "Personal interest area creation failed - person profile not found",
                extra={
                    "user_id": user.id,
                    "email": user.email,
                    "ip_address": ip_address,
                    "action": "personal_interest_area_creation_no_person_profile",
                },
            )
            return Response({"error": "Person profile not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(
                "Error creating personal interest area",
                extra={
                    "user_id": user.id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "request_data": request.data,
                    "ip_address": ip_address,
                    "action": "personal_interest_area_creation_error",
                },
                exc_info=True,
            )
            return Response(
                {"error": "An unexpected error occurred while creating interest area."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        summary="Update Personal Interest Area",
        description="""
        Updates an existing interest area with ownership validation.
        
        **Security Features:**
        - Validates interest area belongs to authenticated user
        - Cannot update other users' interest areas
        - Ownership verification required
        """,
        request=InterestAreaUpdateSerializer,
        responses={
            200: InterestAreaRetrieveSerializer,
            400: {"description": "Validation error in update data"},
            401: {"description": "Authentication required"},
            403: {"description": "Access denied - not your interest area"},
            404: {"description": "Interest area not found"},
        },
    )
    def update(self, request, pk=None):
        user = request.user
        ip_address = request.META.get("REMOTE_ADDR", "Unknown")

        logger.info(
            "Personal interest area update requested",
            extra={
                "user_id": user.id,
                "interest_area_id": pk,
                "request_data_size": len(str(request.data)),
                "ip_address": ip_address,
                "action": "personal_interest_area_update_requested",
            },
        )

        try:
            # SECURITY: Verify user has Person profile
            person = get_object_or_404(Person, user=user)

            # SECURITY: Get interest area and verify ownership
            interest_area = get_object_or_404(
                Observation,
                observation_id=pk,
                observation_concept=get_concept_by_code("INTEREST_AREA"),
                person=person,  # CRITICAL: Must belong to this person
            )

            # Store original values for logging
            original_content = interest_area.value_as_string

            logger.debug(
                "Personal interest area found for update with ownership verified",
                extra={
                    "user_id": user.id,
                    "person_id": person.person_id,
                    "interest_area_id": pk,
                    "original_content_preview": original_content[:100] if original_content else None,
                    "action": "personal_interest_area_update_found",
                },
            )

            serializer = self.get_serializer(interest_area, data=request.data)

            if not serializer.is_valid():
                logger.warning(
                    "Personal interest area update validation failed",
                    extra={
                        "user_id": user.id,
                        "person_id": person.person_id,
                        "interest_area_id": pk,
                        "validation_errors": json.dumps(serializer.errors, ensure_ascii=False),
                        "ip_address": ip_address,
                        "action": "personal_interest_area_update_validation_failed",
                    },
                )
                return Response(
                    {"error": "Validation failed", "details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
                )

            # Update with atomic transaction
            with transaction.atomic():
                updated_instance = serializer.save()

                logger.info(
                    "Personal interest area update completed successfully",
                    extra={
                        "user_id": user.id,
                        "person_id": person.person_id,
                        "interest_area_id": pk,
                        "original_content_preview": original_content[:100] if original_content else None,
                        "updated_content_preview": (
                            updated_instance.value_as_string[:100] if updated_instance.value_as_string else None
                        ),
                        "update_timestamp": timezone.now().isoformat(),
                        "ip_address": ip_address,
                        "action": "personal_interest_area_update_success",
                    },
                )

                return Response(InterestAreaRetrieveSerializer(updated_instance).data, status=status.HTTP_200_OK)

        except Http404:
            logger.warning(
                "Personal interest area update failed - not found or access denied",
                extra={
                    "user_id": user.id,
                    "interest_area_id": pk,
                    "ip_address": ip_address,
                    "action": "personal_interest_area_update_access_denied",
                },
            )
            return Response(
                {"error": "Interest area not found or you don't have permission to update it."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(
                "Error updating personal interest area",
                extra={
                    "user_id": user.id,
                    "interest_area_id": pk,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "request_data": request.data,
                    "ip_address": ip_address,
                    "action": "personal_interest_area_update_error",
                },
                exc_info=True,
            )
            return Response(
                {"error": "An unexpected error occurred while updating interest area."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@extend_schema(
    tags=["Provider Interest Management"],
    summary="Mark Interest Area as Attention Point",
    description="""
    Allows providers to mark interest areas as attention points with relationship validation.
    
    **Security Requirements:**
    - Provider must be authenticated with valid Provider profile
    - Interest area must exist and be accessible
    - Provider must be linked to the Person who owns the interest area
    - Cannot mark interest areas from non-linked Persons
    
    **Validation Process:**
    1. **Provider Authentication**: Confirms valid Provider profile
    2. **Interest Area Validation**: Verifies interest area exists
    3. **Relationship Check**: Ensures Provider is linked to interest area owner
    4. **Marking Authorization**: Validates Provider can mark this area
    """,
    request=MarkAttentionPointSerializer,
    responses={
        200: {"description": "Attention point status updated successfully"},
        400: {"description": "Validation error in marking request"},
        401: {"description": "Authentication required"},
        403: {"description": "Provider not linked to interest area owner"},
        404: {"description": "Interest area or provider not found"},
    },
)
class MarkAttentionPointView(APIView):
    """
    Provider Interest Area Attention Marking with Security

    Enables providers to mark interest areas with strict relationship validation.
    """

    permission_classes = [IsAuthenticated]

    def patch(self, request):
        user = request.user
        ip_address = request.META.get("REMOTE_ADDR", "Unknown")

        logger.info(
            "Mark attention point requested",
            extra={
                "user_id": user.id,
                "request_data": request.data,
                "ip_address": ip_address,
                "action": "mark_attention_point_requested",
            },
        )

        try:
            # SECURITY: Verify user is a provider
            provider = get_object_or_404(Provider, user=user)

            logger.debug(
                "Provider verified for attention point marking",
                extra={
                    "user_id": user.id,
                    "provider_id": provider.provider_id,
                    "provider_name": provider.social_name,
                    "action": "mark_attention_point_provider_verified",
                },
            )

            # Validate request data
            serializer = MarkAttentionPointSerializer(data=request.data, context={"request": request})

            if not serializer.is_valid():
                logger.warning(
                    "Mark attention point validation failed",
                    extra={
                        "user_id": user.id,
                        "provider_id": provider.provider_id,
                        "validation_errors": json.dumps(serializer.errors, ensure_ascii=False),
                        "ip_address": ip_address,
                        "action": "mark_attention_point_validation_failed",
                    },
                )
                return Response(
                    {"error": "Validation failed", "details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
                )

            # Get validated data
            data = serializer.validated_data
            area_id = data["area_id"]
            is_attention_point = data["is_attention_point"]

            # SECURITY: Get the interest area observation and verify it exists
            observation = get_object_or_404(
                Observation,
                observation_id=area_id,
                observation_concept_id=get_concept_by_code("INTEREST_AREA").concept_id,
            )

            # SECURITY: Verify Provider is linked to the Person who owns this interest area
            if observation.person:
                relationship_exists = FactRelationship.objects.filter(
                    fact_id_1=observation.person.person_id,
                    domain_concept_1_id=get_concept_by_code("PERSON").concept_id,
                    fact_id_2=provider.provider_id,
                    domain_concept_2_id=get_concept_by_code("PROVIDER").concept_id,
                    relationship_concept_id=get_concept_by_code("PERSON_PROVIDER").concept_id,
                ).exists()

                if not relationship_exists:
                    logger.warning(
                        "Mark attention point access denied - provider not linked to interest area owner",
                        extra={
                            "user_id": user.id,
                            "provider_id": provider.provider_id,
                            "area_id": area_id,
                            "area_person_id": observation.person.person_id,
                            "action": "mark_attention_point_no_relationship",
                        },
                    )
                    return Response(
                        {"error": "You can only mark attention points for interest areas of linked persons."},
                        status=status.HTTP_403_FORBIDDEN,
                    )

            # Get provider name for marking
            provider_name = get_provider_full_name(provider.provider_id)

            logger.debug(
                "Processing attention point marking with relationship validated",
                extra={
                    "user_id": user.id,
                    "provider_id": provider.provider_id,
                    "provider_name": provider_name,
                    "area_id": area_id,
                    "area_person_id": observation.person.person_id if observation.person else None,
                    "is_attention_point": is_attention_point,
                    "action": "mark_attention_point_processing",
                },
            )

            # Parse existing interest data
            try:
                interest_data = json.loads(observation.value_as_string) if observation.value_as_string else {}
            except json.JSONDecodeError:
                logger.warning(
                    "Invalid JSON in interest area, creating new structure",
                    extra={
                        "user_id": user.id,
                        "area_id": area_id,
                        "original_value": observation.value_as_string,
                        "action": "mark_attention_point_json_error",
                    },
                )
                interest_data = {}

            # Initialize marked_by list if it doesn't exist
            interest_data["marked_by"] = interest_data.get("marked_by", [])
            original_marked_by = interest_data["marked_by"].copy()

            # Update marking status
            if is_attention_point:
                if provider_name not in interest_data["marked_by"]:
                    interest_data["marked_by"].append(provider_name)
                    marking_action = "added"
                else:
                    marking_action = "already_marked"
            else:
                if provider_name in interest_data["marked_by"]:
                    interest_data["marked_by"].remove(provider_name)
                    marking_action = "removed"
                else:
                    marking_action = "not_marked"

            # Update the observation with atomic transaction
            with transaction.atomic():
                observation.value_as_string = json.dumps(interest_data, ensure_ascii=False)
                observation.save(update_fields=["value_as_string"])

                logger.info(
                    "Mark attention point completed successfully with security validation",
                    extra={
                        "user_id": user.id,
                        "provider_id": provider.provider_id,
                        "provider_name": provider_name,
                        "area_id": area_id,
                        "area_person_id": observation.person.person_id if observation.person else None,
                        "is_attention_point": is_attention_point,
                        "marking_action": marking_action,
                        "original_marked_by": original_marked_by,
                        "updated_marked_by": interest_data["marked_by"],
                        "total_providers_marking": len(interest_data["marked_by"]),
                        "update_timestamp": timezone.now().isoformat(),
                        "ip_address": ip_address,
                        "action": "mark_attention_point_success",
                    },
                )

                return Response(
                    {
                        "provider_name": provider_name,
                        "is_marked": is_attention_point,
                        "total_markers": len(interest_data["marked_by"]),
                        "marking_action": marking_action,
                    },
                    status=status.HTTP_200_OK,
                )

        except Http404:
            logger.warning(
                "Mark attention point failed - interest area or provider not found",
                extra={
                    "user_id": user.id,
                    "area_id": data.get("area_id") if "data" in locals() else None,
                    "ip_address": ip_address,
                    "action": "mark_attention_point_not_found",
                },
            )
            return Response({"error": "Interest area or provider not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(
                "Error marking attention point",
                extra={
                    "user_id": user.id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "request_data": request.data,
                    "ip_address": ip_address,
                    "action": "mark_attention_point_error",
                },
                exc_info=True,
            )
            return Response(
                {"error": "An unexpected error occurred while marking attention point."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
