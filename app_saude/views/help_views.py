import json
import logging

from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import Http404
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


def get_provider_and_linked_persons(request_user):
    """
    Retorna o provider logado e os IDs das pessoas vinculadas a ele.
    """
    provider = get_object_or_404(Provider, user=request_user)

    linked_persons_ids = FactRelationship.objects.filter(
        fact_id_2=provider.provider_id,
        domain_concept_1_id=get_concept_by_code("PERSON").concept_id,
        domain_concept_2_id=get_concept_by_code("PROVIDER").concept_id,
        relationship_concept_id=get_concept_by_code("PERSON_PROVIDER").concept_id,
    ).values_list("fact_id_1", flat=True)

    return provider, set(linked_persons_ids)


def get_provider_and_linked_person_or_404(request_user, person_id):
    """
    Valida se a pessoa está vinculada ao provider logado. Retorna a pessoa ou 404.
    """
    provider, linked_ids = get_provider_and_linked_persons(request_user)
    if int(person_id) not in linked_ids:
        raise Http404("Esta pessoa não está vinculada a este profissional.")
    return provider, Person.objects.get(pk=person_id)


def get_person_and_linked_providers(request_user):
    """
    Retorna o person logado e os IDs dos providers vinculados a ele.
    """
    person = get_object_or_404(Person, user=request_user)

    linked_providers_ids = FactRelationship.objects.filter(
        fact_id_1=person.person_id,
        domain_concept_1_id=get_concept_by_code("PERSON").concept_id,
        domain_concept_2_id=get_concept_by_code("PROVIDER").concept_id,
        relationship_concept_id=get_concept_by_code("PERSON_PROVIDER").concept_id,
    ).values_list("fact_id_2", flat=True)

    return person, set(linked_providers_ids)


@extend_schema(
    tags=["Help System"],
    summary="Get Active Help Count",
    description="""
    Returns the total count of active help requests for all persons linked to the authenticated provider.
    
    **Security Features:**
    - Provider authentication required
    - Counts only help requests from linked persons
    - Filtered by authenticated provider only
    - No access to other providers' help counts
    
    **Help Count Calculation:**
    - Counts only ACTIVE help observations
    - Includes help requests from all linked persons
    - Filters by the specific provider ID
    - Real-time count (not cached)
    
    **Use Cases:**
    - **Dashboard Badge**: Show notification count in provider UI
    - **Workload Management**: Track current help request volume
    - **Priority Alerts**: Trigger notifications for high help counts
    - **Performance Metrics**: Monitor help response patterns
    """,
    responses={
        200: HelpCountSerializer,
        401: {"description": "Authentication required"},
        404: {"description": "Provider profile not found"},
    },
)
class HelpCountView(APIView):
    """
    Active Help Count for Provider with Security

    Returns count of pending help requests for the authenticated provider only.
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
            # SECURITY: Get provider and linked persons using utility function
            provider, linked_persons_ids = get_provider_and_linked_persons(request.user)

            logger.debug(
                "Provider and linked persons identified for help count",
                extra={
                    "user_id": user.id,
                    "provider_id": provider.provider_id,
                    "provider_name": provider.social_name,
                    "linked_persons_count": len(linked_persons_ids),
                    "action": "help_count_provider_identified",
                },
            )

            # SECURITY: Count active helps only from linked persons to this provider
            help_count = Observation.objects.filter(
                person_id__in=linked_persons_ids,  # CRITICAL: Only from linked persons
                provider_id=provider.provider_id,  # CRITICAL: Only to this provider
                observation_concept_id=get_concept_by_code("HELP").concept_id,
                value_as_concept_id=get_concept_by_code("ACTIVE").concept_id,
            ).count()

            # Use serializer for response data validation and formatting
            serializer = HelpCountSerializer({"help_count": help_count})

            logger.info(
                "Help count retrieval completed successfully",
                extra={
                    "user_id": user.id,
                    "provider_id": provider.provider_id,
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
    Creates new help requests from authenticated Person to linked Providers only.
    
    **Security Requirements:**
    - Person must be authenticated and have Person profile
    - Can only send help requests to linked Providers
    - Cannot send help requests to non-linked Providers
    - Validates Provider relationship before creating requests
    
    **Help Request System:**
    - Persons can send help requests to their linked Providers
    - Multiple help requests can be sent in a single API call
    - Each help request is stored as an Observation with ACTIVE status
    - Providers receive notifications about new help requests
    
    **Request Processing:**
    1. **Person Verification**: Confirms user has valid Person profile
    2. **Provider Validation**: Ensures all target providers are linked
    3. **Bulk Creation**: Processes multiple help requests atomically
    4. **Auto-Timestamps**: Sets observation_date to current time
    5. **Status Setting**: Marks all new requests as ACTIVE
    
    **Security Features:**
    - Validates Person-Provider relationships before creating requests
    - Cannot send help to unlinked providers
    - Atomic transaction ensures data consistency
    - Complete audit logging of all operations
    """,
    request=HelpCreateSerializer(many=True),
    responses={
        201: ObservationRetrieveSerializer(many=True),
        400: {"description": "Validation error in help request data"},
        401: {"description": "Authentication required"},
        403: {"description": "Cannot send help to non-linked providers"},
        404: {"description": "Person profile not found"},
    },
)
class SendHelpView(APIView):
    """
    Send Help Requests with Security Validation

    Creates help requests from Person to linked Providers with relationship validation.
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
            # SECURITY: Get person and linked providers using utility function
            person, linked_providers_ids = get_person_and_linked_providers(request.user)

            logger.debug(
                "Person and linked providers identified for help request",
                extra={
                    "user_id": user.id,
                    "person_id": person.person_id,
                    "person_name": person.social_name,
                    "linked_providers_count": len(linked_providers_ids),
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

            # SECURITY: Validate all target providers are linked to this person
            requested_provider_ids = set()
            for data in data_list:
                provider_id = data.get("provider_id")
                if provider_id:
                    requested_provider_ids.add(str(provider_id))

            # Convert linked_providers_ids to strings for comparison
            linked_providers_str = {str(pid) for pid in linked_providers_ids}
            unauthorized_providers = requested_provider_ids - linked_providers_str

            if unauthorized_providers:
                logger.warning(
                    "Send help request denied - attempting to send to non-linked providers",
                    extra={
                        "user_id": user.id,
                        "person_id": person.person_id,
                        "requested_providers": list(requested_provider_ids),
                        "linked_providers": list(linked_providers_str),
                        "unauthorized_providers": list(unauthorized_providers),
                        "ip_address": ip_address,
                        "action": "send_help_unauthorized_providers",
                    },
                )
                return Response(
                    {
                        "error": f"Cannot send help requests to non-linked providers: {', '.join(unauthorized_providers)}"
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            observations = []
            current_time = timezone.now()

            # Create help observations in bulk with security validation passed
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
                            "Individual help request created with security validation",
                            extra={
                                "user_id": user.id,
                                "person_id": person.person_id,
                                "observation_id": obs.observation_id,
                                "provider_id": data.get("provider_id"),
                                "relationship_validated": True,
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
                "Send help request completed successfully with security validation",
                extra={
                    "user_id": user.id,
                    "person_id": person.person_id,
                    "person_name": person.social_name,
                    "help_requests_created": len(observations),
                    "observation_ids": [obs.observation_id for obs in observations],
                    "provider_ids": [data.get("provider_id") for data in data_list],
                    "all_providers_validated": True,
                    "ip_address": ip_address,
                    "action": "send_help_success",
                },
            )

            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except Http404:
            logger.warning(
                "Send help request failed - person profile not found",
                extra={
                    "user_id": user.id,
                    "email": user.email,
                    "ip_address": ip_address,
                    "action": "send_help_no_person_profile",
                },
            )
            return Response({"error": "Person profile not found."}, status=status.HTTP_404_NOT_FOUND)
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
    Retrieves all help requests received by the authenticated Provider from linked Persons only.
    
    **Security Features:**
    - Provider authentication required
    - Returns only help requests directed to this Provider
    - Includes only requests from linked Persons
    - Cannot access other providers' help requests
    
    **Help Request Retrieval:**
    - Returns all help observations directed to this Provider
    - Includes both ACTIVE and RESOLVED help requests
    - Ordered by most recent first (latest observation_date)
    - Includes complete help request details and Person information
    
    **Use Cases:**
    - **Provider Dashboard**: Central view of all incoming help requests
    - **Request Management**: Track and manage help request queue
    - **Response Planning**: Prioritize and organize responses
    - **Service History**: Review past help requests and resolutions
    """,
    responses={
        200: ObservationRetrieveSerializer(many=True),
        401: {"description": "Authentication required"},
        404: {"description": "Provider profile not found"},
    },
)
class ReceivedHelpsView(APIView):
    """
    Received Help Requests with Security

    Retrieves all help requests received by the authenticated provider with security validation.
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
            # SECURITY: Get provider and linked persons using utility function
            provider, linked_persons_ids = get_provider_and_linked_persons(request.user)

            logger.debug(
                "Provider and linked persons identified for received helps",
                extra={
                    "user_id": user.id,
                    "provider_id": provider.provider_id,
                    "provider_name": provider.social_name,
                    "linked_persons_count": len(linked_persons_ids),
                    "action": "received_helps_provider_identified",
                },
            )

            # SECURITY: Get help observations directed to this provider from linked persons only
            helps = (
                Observation.objects.filter(
                    provider_id=provider.provider_id,  # CRITICAL: Only to this provider
                    person_id__in=linked_persons_ids,  # CRITICAL: Only from linked persons
                    observation_concept_id=get_concept_by_code("HELP").concept_id,
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
                    "total_helps_count": helps.count(),
                    "active_helps_count": active_count,
                    "resolved_helps_count": resolved_count,
                    "linked_persons_count": len(linked_persons_ids),
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
    Updates a help request status from ACTIVE to RESOLVED with security validation.
    
    **Security Requirements:**
    - Provider must be authenticated with valid Provider profile
    - Help request must be directed to this Provider
    - Help request must be from a linked Person
    - Cannot resolve other providers' help requests
    
    **Resolution Process:**
    1. **Provider Verification**: Confirms user has valid Provider profile
    2. **Help Authorization**: Ensures help request belongs to this Provider
    3. **Relationship Validation**: Verifies help is from linked Person
    4. **Status Update**: Changes value_as_concept_id from ACTIVE to RESOLVED
    5. **Audit Logging**: Records resolution action with full context
    
    **Business Rules:**
    - Only ACTIVE help requests can be resolved
    - Provider must be the original recipient of the help request
    - Help request must be from a linked Person
    - Resolution action is permanent (cannot be undone via API)
    """,
    responses={
        200: ObservationRetrieveSerializer,
        401: {"description": "Authentication required"},
        403: {"description": "Cannot resolve help from non-linked person"},
        404: {"description": "Help request not found"},
        400: {"description": "Help request cannot be resolved (wrong status)"},
    },
)
class MarkHelpAsResolvedView(APIView):
    """
    Mark Help Request as Resolved with Security

    Updates help request status to resolved with comprehensive security validation.
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
            # SECURITY: Get provider and linked persons using utility function
            provider, linked_persons_ids = get_provider_and_linked_persons(request.user)

            logger.debug(
                "Provider and linked persons verified for help resolution",
                extra={
                    "user_id": user.id,
                    "provider_id": provider.provider_id,
                    "provider_name": provider.social_name,
                    "help_id": help_id,
                    "linked_persons_count": len(linked_persons_ids),
                    "action": "mark_help_resolved_provider_verified",
                },
            )

            # SECURITY: Get the help observation with comprehensive authorization check
            help_observation = get_object_or_404(
                Observation,
                observation_id=help_id,
                observation_concept_id=get_concept_by_code("HELP").concept_id,
                provider_id=provider.provider_id,  # CRITICAL: Must be directed to this provider
                person_id__in=linked_persons_ids,  # CRITICAL: Must be from linked person
            )

            logger.debug(
                "Help request found and security validated",
                extra={
                    "user_id": user.id,
                    "provider_id": provider.provider_id,
                    "help_id": help_id,
                    "help_person_id": help_observation.person_id,
                    "person_is_linked": help_observation.person_id in linked_persons_ids,
                    "current_status_id": help_observation.value_as_concept_id,
                    "action": "mark_help_resolved_help_found",
                },
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
            with transaction.atomic():
                help_observation.value_as_concept_id = get_concept_by_code("RESOLVED").concept_id
                help_observation.save(update_fields=["value_as_concept_id"])

                serializer = ObservationRetrieveSerializer(help_observation)

                logger.info(
                    "Mark help as resolved completed successfully with security validation",
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
                        "relationship_validated": True,
                        "ip_address": ip_address,
                        "action": "mark_help_resolved_success",
                    },
                )

                return Response(serializer.data, status=status.HTTP_200_OK)

        except Http404:
            logger.warning(
                "Mark help as resolved failed - help request not found or access denied",
                extra={
                    "user_id": user.id,
                    "help_id": help_id,
                    "ip_address": ip_address,
                    "action": "mark_help_resolved_not_found",
                },
            )
            return Response(
                {"error": "Help request not found, not directed to you, or from non-linked person."},
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
