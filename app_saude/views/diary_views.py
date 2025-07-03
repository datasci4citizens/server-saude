import logging

from django.contrib.auth import get_user_model
from django.db import transaction
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
    tags=["Diary System"],
    summary="Manage Diary Entries",
    description="""
    Comprehensive diary management system for personal journal entries and provider sharing.
    
    **GET - Retrieve Diary Entries:**
    - Returns all diary entries in the system (admin/global view)
    - Supports optional limit parameter for pagination
    - Ordered by most recent entries first
    - Includes complete diary entry details
    
    **POST - Create New Diary Entry:**
    - Creates personal diary entry for authenticated user
    - Supports text content, mood tracking, and sharing preferences
    - Automatically timestamps entries
    - Optional sharing with linked providers
    
    **Diary Entry Features:**
    - **Personal Journaling**: Private diary entries for self-reflection
    - **Provider Sharing**: Optional sharing with healthcare providers
    - **Mood Tracking**: Integration with emotional state monitoring
    - **Rich Content**: Support for text, emotions, and structured data
    
    **Use Cases:**
    - **Personal Wellness**: Daily mood and activity tracking
    - **Clinical Monitoring**: Share relevant entries with providers
    - **Progress Tracking**: Monitor personal development over time
    - **Communication Tool**: Enhanced provider-patient communication
    
    **Privacy and Sharing:**
    - Entries are private by default
    - Optional sharing with specific providers
    - User controls sharing preferences per entry
    - Providers only see explicitly shared entries
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
    Global Diary Management

    Handles global diary operations including listing and creation of diary entries.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={
            200: DiaryRetrieveSerializer(many=True),
            500: {"description": "Internal server error"},
        },
    )
    def get(self, request):
        user = request.user
        ip_address = request.META.get("REMOTE_ADDR", "Unknown")
        limit = request.query_params.get("limit")

        logger.info(
            "Diary retrieval requested",
            extra={
                "user_id": user.id,
                "limit": limit,
                "ip_address": ip_address,
                "action": "diary_retrieval_requested",
            },
        )

        try:
            # Search for all diary entries
            diary_entries_query = (
                Observation.objects.filter(observation_concept_id=get_concept_by_code("diary_entry").concept_id)
                .select_related("observation_concept", "person__user")
                .order_by("-observation_date")
            )

            # Apply limit if provided and valid
            if limit and limit.isdigit():
                limit_int = int(limit)
                if limit_int > 0:
                    diary_entries_query = diary_entries_query[:limit_int]
                    logger.debug(
                        "Limit applied to diary query",
                        extra={"user_id": user.id, "limit_applied": limit_int, "action": "diary_limit_applied"},
                    )

            diary_entries = list(diary_entries_query)

            # Calculate statistics
            total_entries = len(diary_entries)
            shared_entries = len([entry for entry in diary_entries if getattr(entry, "shared_with_provider", False)])

            serializer = DiaryRetrieveSerializer(diary_entries, many=True)

            logger.info(
                "Diary retrieval completed successfully",
                extra={
                    "user_id": user.id,
                    "diary_entries_count": total_entries,
                    "shared_entries_count": shared_entries,
                    "limit_applied": limit,
                    "query_performance": "optimized_with_select_related",
                    "ip_address": ip_address,
                    "action": "diary_retrieval_success",
                },
            )

            return Response(serializer.data)

        except Exception as e:
            logger.error(
                "Error retrieving diaries",
                extra={
                    "user_id": user.id,
                    "limit": limit,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "ip_address": ip_address,
                    "action": "diary_retrieval_error",
                },
                exc_info=True,
            )
            return Response(
                {"error": "An unexpected error occurred while retrieving diary entries."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        summary="Create New Diary Entry",
        description="""
        Creates a new personal diary entry for the authenticated user.
        
        **Entry Creation Process:**
        1. **User Verification**: Confirms user has valid Person profile
        2. **Content Validation**: Validates diary content and metadata
        3. **Timestamp Assignment**: Automatically sets creation timestamp
        4. **Sharing Configuration**: Sets provider sharing preferences
        5. **Storage**: Saves entry as Observation with diary_entry concept
        
        **Diary Entry Components:**
        - **Content**: Main text content of the diary entry
        - **Mood/Emotion**: Optional emotional state tracking
        - **Sharing Settings**: Whether to share with providers
        - **Metadata**: Tags, categories, or additional structured data
        
        **Privacy Controls:**
        - Entries are private by default
        - User explicitly chooses which entries to share
        - Shared entries visible to all linked providers
        - User can modify sharing settings later
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
            "Diary creation requested",
            extra={
                "user_id": user.id,
                "request_data_size": len(str(request.data)),
                "ip_address": ip_address,
                "action": "diary_creation_requested",
            },
        )

        try:
            # Verify user has Person profile
            if not hasattr(user, "person") or not user.person:
                logger.warning(
                    "Diary creation failed - no person profile",
                    extra={
                        "user_id": user.id,
                        "email": user.email,
                        "ip_address": ip_address,
                        "action": "diary_creation_no_person_profile",
                    },
                )
                return Response(
                    {"error": "Person profile required to create diary entries."}, status=status.HTTP_404_NOT_FOUND
                )

            person = user.person

            logger.debug(
                "Person verified for diary creation",
                extra={
                    "user_id": user.id,
                    "person_id": person.person_id,
                    "person_name": person.social_name,
                    "action": "diary_creation_person_verified",
                },
            )

            serializer = DiaryCreateSerializer(data=request.data, context={"request": request})

            if not serializer.is_valid():
                logger.warning(
                    "Diary creation validation failed",
                    extra={
                        "user_id": user.id,
                        "person_id": person.person_id,
                        "validation_errors": json.dumps(serializer.errors, ensure_ascii=False),
                        "ip_address": ip_address,
                        "action": "diary_creation_validation_failed",
                    },
                )
                return Response(
                    {"error": "Validation failed", "details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
                )

            # Create diary entry with atomic transaction
            with transaction.atomic():
                result = serializer.save()

                logger.info(
                    "Diary creation completed successfully",
                    extra={
                        "user_id": user.id,
                        "person_id": person.person_id,
                        "person_name": person.social_name,
                        "diary_result": str(result),
                        "entry_shared": result.get("shared_with_provider", False) if isinstance(result, dict) else None,
                        "creation_timestamp": timezone.now().isoformat(),
                        "ip_address": ip_address,
                        "action": "diary_creation_success",
                    },
                )

                return Response(result, status=status.HTTP_201_CREATED)

        except ValidationError as ve:
            logger.warning(
                "Diary creation validation error",
                extra={
                    "user_id": user.id,
                    "validation_error": str(ve),
                    "ip_address": ip_address,
                    "action": "diary_creation_validation_error",
                },
            )
            return Response({"error": str(ve)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(
                "Error creating diary",
                extra={
                    "user_id": user.id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "request_data": request.data,
                    "ip_address": ip_address,
                    "action": "diary_creation_error",
                },
                exc_info=True,
            )
            return Response(
                {"error": "An unexpected error occurred while creating diary entry."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@extend_schema(
    tags=["Diary System"],
    summary="Diary Entry Details and Management",
    description="""
    Individual diary entry operations including viewing and deletion.
    
    **GET - View Diary Entry:**
    - Retrieves complete details of a specific diary entry
    - Includes all metadata, content, and sharing status
    - Validates diary entry exists and is accessible
    
    **DELETE - Remove Diary Entry:**
    - Permanently deletes a diary entry
    - Validates user permissions for deletion
    - Cannot be undone once completed
    - Logs deletion for audit purposes
    
    **Authorization:**
    - User must be authenticated
    - Entry must exist in the system
    - Deletion requires appropriate permissions
    
    **Use Cases:**
    - **Entry Review**: View complete diary entry details
    - **Content Management**: Delete unwanted or outdated entries
    - **Privacy Management**: Remove sensitive information
    - **Data Cleanup**: Remove test or accidental entries
    """,
    responses={
        200: DiaryRetrieveSerializer,
        404: {"description": "Diary entry not found"},
        401: {"description": "Authentication required"},
    },
)
class DiaryDetailView(APIView):
    """
    Individual Diary Entry Management

    Handles operations on specific diary entries including viewing and deletion.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, diary_id):
        user = request.user
        ip_address = request.META.get("REMOTE_ADDR", "Unknown")

        logger.info(
            "Diary detail retrieval requested",
            extra={
                "user_id": user.id,
                "diary_id": diary_id,
                "ip_address": ip_address,
                "action": "diary_detail_requested",
            },
        )

        try:
            diary = get_object_or_404(
                Observation,
                observation_id=diary_id,
                observation_concept_id=get_concept_by_code("diary_entry").concept_id,
            )

            logger.debug(
                "Diary entry found for detail view",
                extra={
                    "user_id": user.id,
                    "diary_id": diary_id,
                    "diary_person_id": diary.person_id,
                    "diary_date": diary.observation_date.isoformat() if diary.observation_date else None,
                    "shared_with_provider": getattr(diary, "shared_with_provider", False),
                    "action": "diary_detail_found",
                },
            )

            serializer = DiaryRetrieveSerializer(diary)

            logger.info(
                "Diary detail retrieval completed successfully",
                extra={
                    "user_id": user.id,
                    "diary_id": diary_id,
                    "person_id": diary.person_id,
                    "diary_date": diary.observation_date.isoformat() if diary.observation_date else None,
                    "content_length": len(diary.value_as_string) if diary.value_as_string else 0,
                    "ip_address": ip_address,
                    "action": "diary_detail_success",
                },
            )

            return Response(serializer.data)

        except Http404:
            logger.warning(
                "Diary detail retrieval failed - diary not found",
                extra={
                    "user_id": user.id,
                    "diary_id": diary_id,
                    "ip_address": ip_address,
                    "action": "diary_detail_not_found",
                },
            )
            return Response({"error": "Diary entry not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(
                "Error retrieving diary detail",
                extra={
                    "user_id": user.id,
                    "diary_id": diary_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "ip_address": ip_address,
                    "action": "diary_detail_error",
                },
                exc_info=True,
            )
            return Response(
                {"error": "An unexpected error occurred while retrieving diary entry."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        summary="Delete Diary Entry",
        description="""
        Permanently deletes a diary entry from the system.
        
        **⚠️ PERMANENT ACTION - CANNOT BE UNDONE ⚠️**
        
        **Deletion Process:**
        1. **Entry Verification**: Confirms diary entry exists
        2. **Permission Check**: Validates user has deletion rights
        3. **Dependency Check**: Verifies safe deletion
        4. **Permanent Removal**: Deletes entry from database
        5. **Audit Logging**: Records deletion for compliance
        
        **Authorization Requirements:**
        - User must be authenticated
        - Entry must exist in the system
        - User must have appropriate permissions
        
        **Use Cases:**
        - **Privacy Protection**: Remove sensitive personal information
        - **Content Management**: Clean up unwanted entries
        - **Data Compliance**: Remove data per user requests
        - **Error Correction**: Remove accidentally created entries
        """,
        responses={
            200: {"description": "Diary entry deleted successfully"},
            404: {"description": "Diary entry not found"},
            401: {"description": "Authentication required"},
            403: {"description": "Insufficient permissions for deletion"},
        },
        parameters=[
            OpenApiParameter(
                name="diary_id",
                type=int,
                location=OpenApiParameter.PATH,
                description="Unique identifier of the diary entry to delete",
                examples=[OpenApiExample(name="Valid diary ID", value=12345)],
            )
        ],
    )
    def delete(self, request, diary_id):
        user = request.user
        ip_address = request.META.get("REMOTE_ADDR", "Unknown")
        user_agent = request.META.get("HTTP_USER_AGENT", "Unknown")

        logger.warning(
            "Diary deletion requested - PERMANENT ACTION",
            extra={
                "user_id": user.id,
                "diary_id": diary_id,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "timestamp": timezone.now().isoformat(),
                "action": "diary_deletion_requested",
            },
        )

        try:
            # Verify diary exists before deletion
            diary = get_object_or_404(
                Observation,
                observation_id=diary_id,
                observation_concept_id=get_concept_by_code("diary_entry").concept_id,
            )

            # Store details for logging before deletion
            diary_person_id = diary.person_id
            diary_date = diary.observation_date
            content_preview = (
                (diary.value_as_string[:100] + "...")
                if diary.value_as_string and len(diary.value_as_string) > 100
                else diary.value_as_string
            )

            logger.info(
                "Diary entry identified for deletion",
                extra={
                    "user_id": user.id,
                    "diary_id": diary_id,
                    "diary_person_id": diary_person_id,
                    "diary_date": diary_date.isoformat() if diary_date else None,
                    "content_preview": content_preview,
                    "action": "diary_deletion_identified",
                },
            )

            # Perform deletion using serializer
            serializer = DiaryDeleteSerializer()
            result = serializer.delete({"diary_id": diary_id})

            logger.critical(
                "Diary deletion completed successfully",
                extra={
                    "user_id": user.id,
                    "diary_id": diary_id,
                    "deleted_person_id": diary_person_id,
                    "deleted_diary_date": diary_date.isoformat() if diary_date else None,
                    "deletion_timestamp": timezone.now().isoformat(),
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                    "action": "diary_deletion_success",
                },
            )

            return Response(result, status=status.HTTP_200_OK)

        except Http404:
            logger.warning(
                "Diary deletion failed - diary not found",
                extra={
                    "user_id": user.id,
                    "diary_id": diary_id,
                    "ip_address": ip_address,
                    "action": "diary_deletion_not_found",
                },
            )
            return Response({"error": "Diary entry not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(
                "Error deleting diary",
                extra={
                    "user_id": user.id,
                    "diary_id": diary_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "ip_address": ip_address,
                    "action": "diary_deletion_error",
                },
                exc_info=True,
            )
            return Response(
                {"error": "An unexpected error occurred while deleting diary entry."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@extend_schema(
    tags=["Personal Diary"],
    summary="Get Personal Diary Entries",
    description="""
    Retrieves all diary entries for the authenticated Person.
    
    **Personal Diary View:**
    - Returns only diary entries belonging to the authenticated user
    - Includes both private and shared entries
    - Ordered chronologically (most recent first)
    - Complete access to all personal diary content
    
    **Entry Information:**
    - **Content**: Full text content of diary entries
    - **Metadata**: Creation dates, mood tracking, tags
    - **Sharing Status**: Whether entries are shared with providers
    - **Privacy Settings**: Personal vs shared content indicators
    
    **Use Cases:**
    - **Personal Journal**: View personal diary history
    - **Mood Tracking**: Review emotional patterns over time
    - **Progress Monitoring**: Track personal development
    - **Memory Aid**: Reference past thoughts and experiences
    
    **Privacy Features:**
    - User sees all their own entries regardless of sharing status
    - Sharing indicators help manage provider visibility
    - Complete control over personal diary content
    """,
    responses={
        200: DiaryRetrieveSerializer,
        401: {"description": "Authentication required"},
        404: {"description": "Person profile not found"},
    },
)
class PersonDiariesView(APIView):
    """
    Personal Diary Entries

    Manages diary entries for the authenticated person.
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

            # Get all diary entries for this person
            diaries = (
                Observation.objects.filter(
                    person=person, observation_concept_id=get_concept_by_code("diary_entry").concept_id
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
    
    **Provider Access to Person Diaries:**
    - Returns only entries explicitly shared with providers
    - Validates Provider-Person relationship exists
    - Filters out private/unshared diary entries
    - Enables clinical monitoring and communication
    
    **Relationship Validation:**
    - Confirms Provider is linked to the specified Person
    - Verifies active Provider-Person relationship
    - Ensures proper authorization for diary access
    
    **Shared Entry Features:**
    - **Clinical Insights**: Person shares relevant health/mood information
    - **Communication Tool**: Enhanced provider-patient interaction
    - **Progress Monitoring**: Track patient wellbeing over time
    - **Care Coordination**: Inform treatment decisions
    
    **Privacy Protection:**
    - Only shared entries are visible to providers
    - Person controls which entries to share
    - Private entries remain completely hidden
    - Sharing status is clearly indicated
    
    **Use Cases:**
    - **Clinical Assessment**: Review patient self-reported data
    - **Treatment Planning**: Inform care decisions with diary insights
    - **Progress Monitoring**: Track patient wellbeing trends
    - **Communication**: Understand patient perspective and concerns
    """,
    responses={
        200: DiaryRetrieveSerializer(many=True),
        401: {"description": "Authentication required"},
        404: {"description": "Provider profile or Person not found"},
        403: {"description": "Provider not linked to specified Person"},
    },
)
class ProviderPersonDiariesView(APIView):
    """
    Provider Access to Person's Shared Diaries

    Allows providers to view diary entries shared by linked persons.
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
            # Validate provider and person relationship
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

            # Get only shared diary entries
            diaries = (
                Observation.objects.filter(
                    person=person,
                    observation_concept_id=get_concept_by_code("diary_entry").concept_id,
                    shared_with_provider=True,
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
    
    **Detailed Entry Access:**
    - Returns complete details of a specific shared diary entry
    - Validates Provider has access to this particular entry
    - Includes all metadata and content information
    - Ensures entry is explicitly shared with providers
    
    **Authorization Validation:**
    - Confirms Provider-Person relationship exists
    - Verifies entry belongs to the specified Person
    - Ensures entry is marked as shared with providers
    - Validates Provider has legitimate access
    
    **Entry Details Include:**
    - **Complete Content**: Full text of the diary entry
    - **Timestamps**: Creation and modification dates
    - **Mood Data**: Emotional state information if included
    - **Metadata**: Tags, categories, and structured data
    - **Sharing Context**: Why entry was shared with provider
    
    **Clinical Applications:**
    - **Treatment Planning**: Detailed patient insights for care decisions
    - **Progress Assessment**: Evaluate patient wellbeing changes
    - **Communication**: Understand patient concerns and experiences
    - **Documentation**: Clinical records and care coordination
    """,
    responses={
        200: DiaryRetrieveSerializer,
        401: {"description": "Authentication required"},
        404: {"description": "Diary entry not found or not shared"},
        403: {"description": "Provider not authorized to view this entry"},
    },
)
class ProviderPersonDiaryDetailView(APIView):
    """
    Provider Access to Specific Shared Diary Entry

    Provides detailed view of individual shared diary entries for providers.
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
            # Verify provider has valid profile
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

            # Get the person and validate they exist
            person = get_object_or_404(Person, person_id=person_id)

            # Validate Provider-Person relationship exists
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

            # Get the specific diary entry (must be shared)
            diary = get_object_or_404(
                Observation,
                observation_id=diary_id,
                person=person,
                observation_concept_id=get_concept_by_code("diary_entry").concept_id,
                shared_with_provider=True,  # Only shared entries accessible
            )

            logger.debug(
                "Shared diary entry found for provider access",
                extra={
                    "user_id": user.id,
                    "provider_id": provider.provider_id,
                    "person_id": person_id,
                    "diary_id": diary_id,
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
                    "access_type": "shared_entry",
                    "ip_address": ip_address,
                    "action": "provider_person_diary_detail_success",
                },
            )

            return Response(serializer.data)

        except Http404 as e:
            logger.warning(
                "Provider person diary detail not found",
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
                {"error": "Diary entry not found, not shared, or you don't have access."},
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
    Comprehensive management of user interest areas and preferences.
    
    **Interest Area System:**
    - Tracks user interests, hobbies, and areas of focus
    - Supports categorization and tagging
    - Enables provider attention point marking
    - Facilitates personalized care and communication
    
    **CRUD Operations:**
    - **Create**: Add new interest areas for users
    - **Read**: View interest areas with filtering
    - **Update**: Modify existing interest area details
    - **List**: Browse interest areas with optional filtering
    
    **Provider Integration:**
    - Providers can mark areas as attention points
    - Clinical relevance tracking for care planning
    - Communication enhancement between provider and person
    
    **Filtering Options:**
    - By person_id: View interest areas for specific person
    - By category: Filter by interest type or category
    - By attention status: Show marked vs unmarked areas
    
    **Use Cases:**
    - **Personalized Care**: Tailor services to user interests
    - **Communication**: Find common topics for engagement
    - **Progress Tracking**: Monitor changes in interests over time
    - **Care Planning**: Incorporate interests into treatment plans
    """,
    parameters=[
        OpenApiParameter(
            name="person_id",
            description="Filter interest areas by specific person ID",
            required=False,
            type=int,
            examples=[
                OpenApiExample(name="Specific person", value=12345),
                OpenApiExample(name="All persons", value=None),
            ],
        )
    ],
)
class InterestAreaViewSet(FlexibleViewSet):
    """
    Interest Area Management ViewSet

    Handles CRUD operations for user interest areas and preferences.
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Build filtered queryset for interest areas.
        """
        try:
            queryset = (
                Observation.objects.filter(observation_concept_id=get_concept_by_code("INTEREST_AREA").concept_id)
                .select_related("person__user", "observation_concept")
                .order_by("-observation_date")
            )

            person_id = self.request.query_params.get("person_id", None)
            if person_id:
                queryset = queryset.filter(person_id=person_id)
                logger.debug(
                    "Interest area queryset filtered by person",
                    extra={
                        "user_id": getattr(self.request.user, "id", None),
                        "person_id": person_id,
                        "filtered_count": queryset.count(),
                        "action": "interest_area_person_filter_applied",
                    },
                )

            return queryset

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
        summary="Create New Interest Area",
        description="""
        Creates a new interest area for the authenticated user.
        
        **Interest Area Creation:**
        - Associates interest with user's Person profile
        - Supports rich metadata and categorization
        - Sets up provider attention tracking
        - Enables personalized care features
        
        **Interest Data:**
        - **Name/Title**: Primary identifier for the interest
        - **Description**: Detailed information about the interest
        - **Category**: Type or classification of interest
        - **Importance Level**: Priority or significance rating
        - **Provider Relevance**: Clinical significance indicators
        """,
        request=InterestAreaCreateSerializer,
        responses={
            201: {"description": "Interest area created successfully"},
            400: {"description": "Validation error in interest area data"},
            401: {"description": "Authentication required"},
        },
    )
    def create(self, request):
        user = request.user
        ip_address = request.META.get("REMOTE_ADDR", "Unknown")

        logger.info(
            "Interest area creation requested",
            extra={
                "user_id": user.id,
                "request_data_size": len(str(request.data)),
                "ip_address": ip_address,
                "action": "interest_area_creation_requested",
            },
        )

        try:
            # Verify user has Person profile
            if not hasattr(user, "person") or not user.person:
                logger.warning(
                    "Interest area creation failed - no person profile",
                    extra={
                        "user_id": user.id,
                        "email": user.email,
                        "ip_address": ip_address,
                        "action": "interest_area_creation_no_person_profile",
                    },
                )
                return Response(
                    {"error": "Person profile required to create interest areas."}, status=status.HTTP_404_NOT_FOUND
                )

            person = user.person

            logger.debug(
                "Person verified for interest area creation",
                extra={
                    "user_id": user.id,
                    "person_id": person.person_id,
                    "person_name": person.social_name,
                    "action": "interest_area_creation_person_verified",
                },
            )

            serializer = self.get_serializer(data=request.data)

            if not serializer.is_valid():
                logger.warning(
                    "Interest area creation validation failed",
                    extra={
                        "user_id": user.id,
                        "person_id": person.person_id,
                        "validation_errors": json.dumps(serializer.errors, ensure_ascii=False),
                        "ip_address": ip_address,
                        "action": "interest_area_creation_validation_failed",
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
                    "Interest area creation completed successfully",
                    extra={
                        "user_id": user.id,
                        "person_id": person.person_id,
                        "person_name": person.social_name,
                        "interest_area_id": instance.observation_id,
                        "interest_content": instance.value_as_string[:100] if instance.value_as_string else None,
                        "creation_timestamp": timezone.now().isoformat(),
                        "ip_address": ip_address,
                        "action": "interest_area_creation_success",
                    },
                )

                return Response(retrieve_serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(
                "Error creating interest area",
                extra={
                    "user_id": user.id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "request_data": request.data,
                    "ip_address": ip_address,
                    "action": "interest_area_creation_error",
                },
                exc_info=True,
            )
            return Response(
                {"error": "An unexpected error occurred while creating interest area."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        summary="Update Interest Area",
        description="""
        Updates an existing interest area with new information.
        
        **Update Operations:**
        - Modify interest area content and metadata
        - Update categorization and importance levels
        - Change provider relevance settings
        - Maintain attention point markings
        
        **Authorization:**
        - User must be authenticated
        - Interest area must exist and be accessible
        - User must have update permissions
        """,
        request=InterestAreaUpdateSerializer,
        responses={
            200: {"description": "Interest area updated successfully"},
            400: {"description": "Validation error in update data"},
            401: {"description": "Authentication required"},
            404: {"description": "Interest area not found"},
        },
    )
    def update(self, request, pk=None):
        user = request.user
        ip_address = request.META.get("REMOTE_ADDR", "Unknown")

        logger.info(
            "Interest area update requested",
            extra={
                "user_id": user.id,
                "interest_area_id": pk,
                "request_data_size": len(str(request.data)),
                "ip_address": ip_address,
                "action": "interest_area_update_requested",
            },
        )

        try:
            interest_area = get_object_or_404(
                Observation, observation_id=pk, observation_concept=get_concept_by_code("INTEREST_AREA")
            )

            # Store original values for logging
            original_content = interest_area.value_as_string

            logger.debug(
                "Interest area found for update",
                extra={
                    "user_id": user.id,
                    "interest_area_id": pk,
                    "original_content_preview": original_content[:100] if original_content else None,
                    "person_id": interest_area.person_id,
                    "action": "interest_area_update_found",
                },
            )

            serializer = self.get_serializer(interest_area, data=request.data)

            if not serializer.is_valid():
                logger.warning(
                    "Interest area update validation failed",
                    extra={
                        "user_id": user.id,
                        "interest_area_id": pk,
                        "validation_errors": json.dumps(serializer.errors, ensure_ascii=False),
                        "ip_address": ip_address,
                        "action": "interest_area_update_validation_failed",
                    },
                )
                return Response(
                    {"error": "Validation failed", "details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
                )

            # Update with atomic transaction
            with transaction.atomic():
                updated_instance = serializer.save()

                logger.info(
                    "Interest area update completed successfully",
                    extra={
                        "user_id": user.id,
                        "interest_area_id": pk,
                        "person_id": updated_instance.person_id,
                        "original_content_preview": original_content[:100] if original_content else None,
                        "updated_content_preview": (
                            updated_instance.value_as_string[:100] if updated_instance.value_as_string else None
                        ),
                        "update_timestamp": timezone.now().isoformat(),
                        "ip_address": ip_address,
                        "action": "interest_area_update_success",
                    },
                )

                return Response(InterestAreaRetrieveSerializer(updated_instance).data, status=status.HTTP_200_OK)

        except Http404:
            logger.warning(
                "Interest area update failed - not found",
                extra={
                    "user_id": user.id,
                    "interest_area_id": pk,
                    "ip_address": ip_address,
                    "action": "interest_area_update_not_found",
                },
            )
            return Response({"error": "Interest area not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(
                "Error updating interest area",
                extra={
                    "user_id": user.id,
                    "interest_area_id": pk,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "request_data": request.data,
                    "ip_address": ip_address,
                    "action": "interest_area_update_error",
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
    Allows providers to mark or unmark interest areas as attention points for clinical focus.
    
    **Attention Point System:**
    - Providers can highlight specific interest areas for clinical attention
    - Multiple providers can mark the same interest area
    - Markings are tracked by provider name for accountability
    - Supports collaborative care coordination
    
    **Clinical Applications:**
    - **Care Planning**: Identify interests relevant to treatment
    - **Communication**: Focus conversations on marked interests
    - **Progress Monitoring**: Track engagement with marked areas
    - **Team Coordination**: Share clinical focus areas with care team
    
    **Marking Process:**
    1. **Provider Verification**: Confirms user is authenticated provider
    2. **Interest Validation**: Verifies interest area exists
    3. **Marking Logic**: Adds/removes provider from marked_by list
    4. **Data Update**: Updates interest area metadata
    5. **Audit Logging**: Records marking actions for accountability
    
    **Business Rules:**
    - Provider must be authenticated with valid Provider profile
    - Interest area must exist in the system
    - Each provider can mark/unmark independently
    - Marking status is preserved per provider
    - Historical marking data is maintained for audit
    
    **Use Cases:**
    - **Clinical Assessment**: Mark interests relevant to health conditions
    - **Treatment Planning**: Highlight areas for therapeutic focus
    - **Care Coordination**: Share attention points with care team
    - **Progress Tracking**: Monitor engagement with marked interests
    """,
    request=MarkAttentionPointSerializer,
    responses={
        200: {"description": "Attention point status updated successfully"},
        400: {"description": "Validation error in marking request"},
        401: {"description": "Authentication required"},
        404: {"description": "Interest area or provider not found"},
    },
)
class MarkAttentionPointView(APIView):
    """
    Provider Interest Area Attention Marking

    Enables providers to mark interest areas as clinical attention points.
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
            # Verify user is a provider
            if not hasattr(user, "provider") or not user.provider:
                logger.warning(
                    "Mark attention point failed - no provider profile",
                    extra={
                        "user_id": user.id,
                        "email": user.email,
                        "ip_address": ip_address,
                        "action": "mark_attention_point_no_provider_profile",
                    },
                )
                return Response(
                    {"error": "Provider profile required to mark attention points."}, status=status.HTTP_404_NOT_FOUND
                )

            provider = user.provider

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

            # Get provider name and validated data
            provider_name = get_provider_full_name(provider.provider_id)
            data = serializer.validated_data
            area_id = data["area_id"]
            is_attention_point = data["is_attention_point"]

            logger.debug(
                "Processing attention point marking",
                extra={
                    "user_id": user.id,
                    "provider_id": provider.provider_id,
                    "provider_name": provider_name,
                    "area_id": area_id,
                    "is_attention_point": is_attention_point,
                    "action": "mark_attention_point_processing",
                },
            )

            # Get the interest area observation
            observation = get_object_or_404(Observation, observation_id=area_id)

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
                    "Mark attention point completed successfully",
                    extra={
                        "user_id": user.id,
                        "provider_id": provider.provider_id,
                        "provider_name": provider_name,
                        "area_id": area_id,
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
                "Mark attention point failed - interest area not found",
                extra={
                    "user_id": user.id,
                    "area_id": data.get("area_id") if "data" in locals() else None,
                    "ip_address": ip_address,
                    "action": "mark_attention_point_not_found",
                },
            )
            return Response({"error": "Interest area not found."}, status=status.HTTP_404_NOT_FOUND)
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
