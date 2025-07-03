import logging

from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import *
from ..serializers import *
from ..utils.provider import *

User = get_user_model()
logger = logging.getLogger("app_saude")


@extend_schema(
    tags=["Help System"],
    summary="Get Active Help Count",
    description="""
    Returns the total count of active help requests for all persons linked to the authenticated provider.
    
    **Help Count Calculation:**
    - Counts only ACTIVE help observations
    - Includes help requests from all linked persons
    - Filters by the specific provider ID
    - Real-time count (not cached)
    
    **Business Logic:**
    1. **Provider Verification**: Confirms user has valid Provider profile
    2. **Relationship Query**: Finds all persons linked to this provider
    3. **Help Filtering**: Counts only active help observations
    4. **Provider Specificity**: Only counts helps directed to this provider
    
    **Help Request States:**
    - **ACTIVE**: Help request is pending and needs attention
    - **RESOLVED**: Help request has been addressed (not counted)
    - **CANCELLED**: Help request was cancelled (not counted)
    
    **Use Cases:**
    - **Dashboard Badge**: Show notification count in provider UI
    - **Workload Management**: Track current help request volume
    - **Priority Alerts**: Trigger notifications for high help counts
    - **Performance Metrics**: Monitor help response patterns
    
    **Performance Notes:**
    - Optimized query using database aggregation
    - Efficient filtering prevents unnecessary data loading
    - Real-time count for accurate notifications
    """,
    responses={
        200: {"description": "Help count retrieved successfully"},
        401: {"description": "Authentication required"},
        404: {"description": "Provider profile not found"},
    },
)
class HelpCountView(APIView):
    """
    Active Help Count for Provider

    Returns count of pending help requests for the authenticated provider.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        ip_address = request.META.get("REMOTE_ADDR", "Unknown")

        logger.info(
            "Help count retrieval requested",
            extra={"user_id": user.id, "ip_address": ip_address, "action": "help_count_requested"},
        )

        try:
            # Check if user is a provider and get ID
            provider = get_object_or_404(Provider, user=request.user)
            provider_id = provider.provider_id

            logger.debug(
                "Provider identified for help count",
                extra={
                    "user_id": user.id,
                    "provider_id": provider_id,
                    "provider_name": provider.social_name,
                    "action": "help_count_provider_identified",
                },
            )

            # Find IDs of persons linked to the provider through FactRelationship
            linked_persons_ids = FactRelationship.objects.filter(
                fact_id_2=provider_id,
                domain_concept_1_id=get_concept_by_code("PERSON").concept_id,
                domain_concept_2_id=get_concept_by_code("PROVIDER").concept_id,
                relationship_concept_id=get_concept_by_code("PERSON_PROVIDER").concept_id,
            ).values_list("fact_id_1", flat=True)

            # Count active helps for these persons
            help_count = Observation.objects.filter(
                person_id__in=linked_persons_ids,
                provider_id=provider_id,  # Only helps directed to this provider
                observation_concept_id=get_concept_by_code("HELP").concept_id,
                value_as_concept_id=get_concept_by_code("ACTIVE").concept_id,
            ).count()

            # Use serializer for response data validation and formatting
            serializer = HelpCountSerializer({"help_count": help_count})

            logger.info(
                "Help count retrieval completed successfully",
                extra={
                    "user_id": user.id,
                    "provider_id": provider_id,
                    "provider_name": provider.social_name,
                    "help_count": help_count,
                    "linked_persons_count": len(linked_persons_ids),
                    "ip_address": ip_address,
                    "action": "help_count_success",
                },
            )

            return Response(serializer.data)

        except Http404:
            logger.warning(
                "Help count retrieval failed - provider profile not found",
                extra={
                    "user_id": user.id,
                    "email": user.email,
                    "ip_address": ip_address,
                    "action": "help_count_no_provider_profile",
                },
            )
            return Response({"error": "Provider profile not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(
                "Error during help count retrieval",
                extra={
                    "user_id": user.id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "ip_address": ip_address,
                    "action": "help_count_error",
                },
                exc_info=True,
            )
            return Response(
                {"error": "An unexpected error occurred while retrieving help count."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@extend_schema(
    tags=["Help System"],
    summary="Send Help Request",
    description="""
    Creates new help requests from authenticated Person to linked Providers.
    
    **Help Request System:**
    - Persons can send help requests to their linked Providers
    - Multiple help requests can be sent in a single API call
    - Each help request is stored as an Observation with ACTIVE status
    - Providers receive notifications about new help requests
    
    **Request Processing:**
    1. **Person Verification**: Confirms user has valid Person profile
    2. **Bulk Creation**: Processes multiple help requests atomically
    3. **Auto-Timestamps**: Sets observation_date to current time
    4. **Status Setting**: Marks all new requests as ACTIVE
    5. **Audit Logging**: Records all help request creation
    
    **Help Request Data:**
    - **Provider ID**: Target provider for the help request
    - **Help Type**: Category or type of assistance needed
    - **Description**: Optional details about the help needed
    - **Priority**: Urgency level of the request
    
    **Business Rules:**
    - Person must be authenticated and have Person profile
    - Person must be linked to target Provider
    - Help requests are immediately visible to Provider
    - Multiple requests can be active simultaneously
    
    **Use Cases:**
    - **Emergency Requests**: Urgent assistance needs
    - **Routine Support**: Regular service requests
    - **Appointment Scheduling**: Request for appointments
    - **General Inquiries**: Questions or information requests
    """,
    request=HelpCreateSerializer(many=True),
    responses={
        201: {"description": "Help requests created successfully"},
        400: {"description": "Validation error in help request data"},
        401: {"description": "Authentication required"},
        404: {"description": "Person profile not found"},
    },
)
class SendHelpView(APIView):
    """
    Send Help Requests

    Creates help requests from Person to linked Providers.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        ip_address = request.META.get("REMOTE_ADDR", "Unknown")

        logger.info(
            "Send help request received",
            extra={
                "user_id": user.id,
                "request_count": len(request.data) if isinstance(request.data, list) else 1,
                "ip_address": ip_address,
                "action": "send_help_requested",
            },
        )

        try:
            # Verify user has Person profile
            if not hasattr(request.user, "person") or not request.user.person:
                logger.warning(
                    "Send help request failed - no person profile",
                    extra={
                        "user_id": user.id,
                        "email": user.email,
                        "ip_address": ip_address,
                        "action": "send_help_no_person_profile",
                    },
                )
                return Response({"error": "Person profile not found."}, status=status.HTTP_404_NOT_FOUND)

            person = request.user.person

            logger.debug(
                "Person identified for help request",
                extra={
                    "user_id": user.id,
                    "person_id": person.person_id,
                    "person_name": person.social_name,
                    "action": "send_help_person_identified",
                },
            )

            # Validate request data
            serializer = HelpCreateSerializer(data=request.data, many=True)
            if not serializer.is_valid():
                logger.warning(
                    "Send help request validation failed",
                    extra={
                        "user_id": user.id,
                        "person_id": person.person_id,
                        "validation_errors": json.dumps(serializer.errors, ensure_ascii=False),
                        "ip_address": ip_address,
                        "action": "send_help_validation_failed",
                    },
                )
                return Response(
                    {"error": "Validation failed", "details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
                )

            # Process validated data
            data_list = serializer.validated_data
            observations = []
            current_time = timezone.now()

            # Create help observations in bulk
            with transaction.atomic():
                for data in data_list:
                    try:
                        # Set required fields for help observation
                        observation_data = {
                            **data,
                            "person_id": person.person_id,
                            "observation_concept_id": get_concept_by_code("HELP").concept_id,
                            "value_as_concept_id": get_concept_by_code("ACTIVE").concept_id,
                            "observation_date": current_time,
                            "observation_type_concept_id": get_concept_by_code("PERSON_GENERATED").concept_id,
                        }

                        obs = Observation.objects.create(**observation_data)
                        observations.append(obs)

                        logger.debug(
                            "Individual help request created",
                            extra={
                                "user_id": user.id,
                                "person_id": person.person_id,
                                "observation_id": obs.observation_id,
                                "provider_id": data.get("provider_id"),
                                "action": "send_help_individual_created",
                            },
                        )

                    except Exception as e:
                        logger.error(
                            "Error creating individual help request",
                            extra={
                                "user_id": user.id,
                                "person_id": person.person_id,
                                "help_data": data,
                                "error": str(e),
                                "error_type": type(e).__name__,
                                "action": "send_help_individual_error",
                            },
                            exc_info=True,
                        )
                        raise  # Re-raise to trigger transaction rollback

            # Serialize response
            response_serializer = ObservationRetrieveSerializer(observations, many=True)

            logger.info(
                "Send help request completed successfully",
                extra={
                    "user_id": user.id,
                    "person_id": person.person_id,
                    "person_name": person.social_name,
                    "help_requests_created": len(observations),
                    "observation_ids": [obs.observation_id for obs in observations],
                    "provider_ids": [data.get("provider_id") for data in data_list],
                    "ip_address": ip_address,
                    "action": "send_help_success",
                },
            )

            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(
                "Error during send help request",
                extra={
                    "user_id": user.id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "request_data": request.data,
                    "ip_address": ip_address,
                    "action": "send_help_error",
                },
                exc_info=True,
            )
            return Response(
                {"error": "An unexpected error occurred while creating help requests."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@extend_schema(
    tags=["Help System"],
    summary="Get Received Help Requests",
    description="""
    Retrieves all help requests received by the authenticated Provider.
    
    **Help Request Retrieval:**
    - Returns all help observations directed to this Provider
    - Includes both ACTIVE and RESOLVED help requests
    - Ordered by most recent first (latest observation_date)
    - Includes complete help request details and Person information
    
    **Provider Verification:**
    - Confirms user has valid Provider profile
    - Filters help requests specific to this Provider
    - Ensures proper authorization for data access
    
    **Help Request Information:**
    - **Person Details**: Who sent the help request
    - **Request Details**: Type, description, priority
    - **Timestamps**: When help was requested and last updated
    - **Status**: Current status (ACTIVE, RESOLVED, etc.)
    - **Provider Context**: Specific provider receiving the request
    
    **Use Cases:**
    - **Provider Dashboard**: Central view of all incoming help requests
    - **Request Management**: Track and manage help request queue
    - **Response Planning**: Prioritize and organize responses
    - **Service History**: Review past help requests and resolutions
    
    **Sorting and Filtering:**
    - **Default Sort**: Most recent requests first
    - **Status Filter**: Can be extended to filter by status
    - **Date Range**: Can be extended to filter by date ranges
    - **Person Filter**: Can be extended to filter by specific persons
    """,
    responses={
        200: {"description": "Help requests retrieved successfully"},
        401: {"description": "Authentication required"},
        404: {"description": "Provider profile not found"},
    },
)
class ReceivedHelpsView(APIView):
    """
    Received Help Requests

    Retrieves all help requests received by the authenticated provider.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        ip_address = request.META.get("REMOTE_ADDR", "Unknown")

        logger.info(
            "Received helps retrieval requested",
            extra={"user_id": user.id, "ip_address": ip_address, "action": "received_helps_requested"},
        )

        try:
            provider = get_object_or_404(Provider, user=request.user)

            logger.debug(
                "Provider identified for received helps",
                extra={
                    "user_id": user.id,
                    "provider_id": provider.provider_id,
                    "provider_name": provider.social_name,
                    "action": "received_helps_provider_identified",
                },
            )

            # Get all help observations directed to this provider
            helps = (
                Observation.objects.filter(
                    provider_id=provider.provider_id, observation_concept_id=get_concept_by_code("HELP").concept_id
                )
                .select_related("person__user")
                .order_by("-observation_date")
            )

            # Count by status for logging
            active_count = helps.filter(value_as_concept_id=get_concept_by_code("ACTIVE").concept_id).count()
            resolved_count = helps.filter(value_as_concept_id=get_concept_by_code("RESOLVED").concept_id).count()

            serializer = ObservationRetrieveSerializer(helps, many=True)

            logger.info(
                "Received helps retrieval completed successfully",
                extra={
                    "user_id": user.id,
                    "provider_id": provider.provider_id,
                    "provider_name": provider.social_name,
                    "total_helps_count": len(helps),
                    "active_helps_count": active_count,
                    "resolved_helps_count": resolved_count,
                    "help_observation_ids": [help.observation_id for help in helps[:10]],  # First 10 for logging
                    "ip_address": ip_address,
                    "action": "received_helps_success",
                },
            )

            return Response(serializer.data)

        except Http404:
            logger.warning(
                "Received helps retrieval failed - provider profile not found",
                extra={
                    "user_id": user.id,
                    "email": user.email,
                    "ip_address": ip_address,
                    "action": "received_helps_no_provider_profile",
                },
            )
            return Response({"error": "Provider profile not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(
                "Error during received helps retrieval",
                extra={
                    "user_id": user.id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "ip_address": ip_address,
                    "action": "received_helps_error",
                },
                exc_info=True,
            )
            return Response(
                {"error": "An unexpected error occurred while retrieving help requests."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@extend_schema(
    tags=["Help System"],
    summary="Mark Help Request as Resolved",
    description="""
    Updates a help request status from ACTIVE to RESOLVED.
    
    **Resolution Process:**
    1. **Help Verification**: Confirms help request exists and is valid
    2. **Authorization**: Ensures Provider has access to this help request
    3. **Status Update**: Changes value_as_concept_id from ACTIVE to RESOLVED
    4. **Audit Logging**: Records resolution action with full context
    5. **Response**: Returns updated help request details
    
    **Business Rules:**
    - Only ACTIVE help requests can be resolved
    - Provider must be the original recipient of the help request
    - Help request must exist and be accessible
    - Resolution action is permanent (cannot be undone via API)
    
    **Help Request Lifecycle:**
    - **Created**: Person creates help request (ACTIVE status)
    - **Received**: Provider sees help request in their queue
    - **Resolved**: Provider marks help as addressed (RESOLVED status)
    - **Archived**: Resolved helps are kept for audit and history
    
    **Use Cases:**
    - **Complete Service**: Mark completed service requests
    - **Close Inquiry**: Resolve answered questions
    - **Finish Assistance**: Complete provided help
    - **Queue Management**: Clear resolved items from active queue
    
    **Authorization:**
    - Provider must be authenticated
    - Provider must be original recipient of the help request
    - Help request must be in ACTIVE status
    """,
    responses={
        200: {"description": "Help request marked as resolved successfully"},
        401: {"description": "Authentication required"},
        404: {"description": "Help request not found"},
        400: {"description": "Help request cannot be resolved (wrong status or authorization)"},
    },
)
class MarkHelpAsResolvedView(APIView):
    """
    Mark Help Request as Resolved

    Updates help request status to resolved for queue management.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, help_id):
        user = request.user
        ip_address = request.META.get("REMOTE_ADDR", "Unknown")

        logger.info(
            "Mark help as resolved requested",
            extra={
                "user_id": user.id,
                "help_id": help_id,
                "ip_address": ip_address,
                "action": "mark_help_resolved_requested",
            },
        )

        try:
            # Verify user is a provider
            provider = get_object_or_404(Provider, user=request.user)

            logger.debug(
                "Provider verified for help resolution",
                extra={
                    "user_id": user.id,
                    "provider_id": provider.provider_id,
                    "provider_name": provider.social_name,
                    "help_id": help_id,
                    "action": "mark_help_resolved_provider_verified",
                },
            )

            # Get the help observation with authorization check
            help_observation = get_object_or_404(
                Observation,
                observation_id=help_id,
                observation_concept_id=get_concept_by_code("HELP").concept_id,
                provider_id=provider.provider_id,  # Ensure provider owns this help request
            )

            # Check if help is already resolved
            if help_observation.value_as_concept_id == get_concept_by_code("RESOLVED").concept_id:
                logger.warning(
                    "Attempt to resolve already resolved help request",
                    extra={
                        "user_id": user.id,
                        "provider_id": provider.provider_id,
                        "help_id": help_id,
                        "person_id": help_observation.person_id,
                        "current_status": "RESOLVED",
                        "action": "mark_help_resolved_already_resolved",
                    },
                )
                return Response({"error": "Help request is already resolved."}, status=status.HTTP_400_BAD_REQUEST)

            # Store original status for logging
            original_status_id = help_observation.value_as_concept_id

            # Update the help observation to mark it as resolved
            help_observation.value_as_concept_id = get_concept_by_code("RESOLVED").concept_id
            help_observation.save(update_fields=["value_as_concept_id"])

            serializer = ObservationRetrieveSerializer(help_observation)

            logger.info(
                "Mark help as resolved completed successfully",
                extra={
                    "user_id": user.id,
                    "provider_id": provider.provider_id,
                    "provider_name": provider.social_name,
                    "help_id": help_id,
                    "person_id": help_observation.person_id,
                    "original_status_id": original_status_id,
                    "new_status": "RESOLVED",
                    "observation_date": (
                        help_observation.observation_date.isoformat() if help_observation.observation_date else None
                    ),
                    "resolution_timestamp": timezone.now().isoformat(),
                    "ip_address": ip_address,
                    "action": "mark_help_resolved_success",
                },
            )

            return Response(serializer.data, status=status.HTTP_200_OK)

        except Http404:
            logger.warning(
                "Mark help as resolved failed - help request or provider not found",
                extra={
                    "user_id": user.id,
                    "help_id": help_id,
                    "ip_address": ip_address,
                    "action": "mark_help_resolved_not_found",
                },
            )
            return Response(
                {"error": "Help request not found or you don't have permission to resolve it."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(
                "Error marking help as resolved",
                extra={
                    "user_id": user.id,
                    "help_id": help_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "ip_address": ip_address,
                    "action": "mark_help_resolved_error",
                },
                exc_info=True,
            )
            return Response(
                {"error": "An unexpected error occurred while resolving help request."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
