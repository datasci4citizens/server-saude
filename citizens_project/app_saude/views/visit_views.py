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


@extend_schema(
    tags=["Visit Management"],
    summary="Get Next Scheduled Visit",
    description="""
    **⚠️ LEGACY FEATURE - LIMITED FRONTEND SUPPORT ⚠️**
    
    Retrieves the next scheduled visit for the authenticated provider.
    
    **Feature Status:**
    - **Backend**: Fully implemented and functional
    - **Frontend**: Limited support, feature partially abandoned
    - **Future**: Kept for potential reimplementation
    - **Usage**: Mainly for API completeness and future development
    
    **Visit Scheduling Logic:**
    - Finds next future visit (after current datetime)
    - Filters by authenticated provider
    - Returns earliest upcoming appointment
    - Includes patient name and visit datetime
    
    **Patient Name Resolution:**
    1. **Primary**: Uses person.social_name if available
    2. **Fallback**: Combines first_name + last_name from user
    3. **Final Fallback**: Uses username if names not available
    
    **Use Cases (Future Implementation):**
    - **Provider Dashboard**: Show next appointment
    - **Calendar Integration**: Sync with external calendars
    - **Notification System**: Appointment reminders
    - **Schedule Management**: Provider schedule overview
    
    **Technical Notes:**
    - Queries are optimized with proper filtering
    - Handles edge cases (no upcoming visits)
    - Returns null when no visits scheduled
    - Timezone-aware date comparisons
    
    **For Future Teams:**
    This endpoint is maintained for potential frontend reimplementation.
    The backend logic is solid and can be leveraged when visit management
    features are prioritized for frontend development.
    """,
    responses={
        200: {"description": "Next visit information retrieved (may be null if no visits scheduled)"},
        401: {"description": "Authentication required"},
        404: {"description": "Provider profile not found"},
    },
)
class NextScheduledVisitView(APIView):
    """
    Next Scheduled Visit (Legacy Feature)

    Returns next upcoming visit for the provider. Feature has limited frontend support
    but is maintained for potential future reimplementation.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        ip_address = request.META.get("REMOTE_ADDR", "Unknown")

        logger.info(
            "Next scheduled visit retrieval requested",
            extra={
                "user_id": user.id,
                "ip_address": ip_address,
                "feature_status": "legacy_limited_frontend_support",
                "action": "next_visit_requested",
            },
        )

        try:
            # Check if user is a provider and get ID
            provider = get_object_or_404(Provider, user=request.user)
            provider_id = provider.provider_id

            logger.debug(
                "Provider identified for next visit lookup",
                extra={
                    "user_id": user.id,
                    "provider_id": provider_id,
                    "provider_name": provider.social_name,
                    "action": "next_visit_provider_identified",
                },
            )

            # Find the next scheduled visit for this provider
            # Only consider future visits (from current datetime)
            current_time = timezone.now()
            next_visit = (
                VisitOccurrence.objects.filter(provider_id=provider_id, visit_start_date__gt=current_time)
                .select_related("person__user")
                .order_by("visit_start_date")
                .first()
            )

            if not next_visit:
                logger.info(
                    "No upcoming visits found for provider",
                    extra={
                        "user_id": user.id,
                        "provider_id": provider_id,
                        "provider_name": provider.social_name,
                        "current_time": current_time.isoformat(),
                        "action": "next_visit_none_found",
                    },
                )
                serializer = NextVisitSerializer({"next_visit": None})
                return Response(serializer.data)

            # Get patient name with fallback logic
            person = next_visit.person
            person_name = person.social_name
            if not person_name and person.user:
                person_name = f"{person.user.first_name} {person.user.last_name}".strip()
                if not person_name:
                    person_name = person.user.username

            # Prepare response data
            visit_data = {
                "next_visit": {
                    "person_name": person_name or "Name not available",
                    "visit_date": next_visit.visit_start_date,
                    "person_id": person.person_id,
                    "visit_id": next_visit.visit_occurrence_id,
                }
            }

            serializer = NextVisitSerializer(visit_data)

            logger.info(
                "Next scheduled visit retrieved successfully",
                extra={
                    "user_id": user.id,
                    "provider_id": provider_id,
                    "provider_name": provider.social_name,
                    "next_visit_date": next_visit.visit_start_date.isoformat(),
                    "next_visit_person_name": person_name,
                    "next_visit_person_id": person.person_id,
                    "visit_id": next_visit.visit_occurrence_id,
                    "ip_address": ip_address,
                    "action": "next_visit_success",
                },
            )

            return Response(serializer.data)

        except Http404:
            logger.warning(
                "Next visit retrieval failed - provider profile not found",
                extra={
                    "user_id": user.id,
                    "email": user.email,
                    "ip_address": ip_address,
                    "action": "next_visit_no_provider_profile",
                },
            )
            return Response({"error": "Provider profile not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(
                "Error retrieving next scheduled visit",
                extra={
                    "user_id": user.id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "ip_address": ip_address,
                    "action": "next_visit_error",
                },
                exc_info=True,
            )
            return Response(
                {"error": "An unexpected error occurred while retrieving next visit."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
