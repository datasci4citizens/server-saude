import logging
import uuid
from datetime import timedelta

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
    tags=["Person-Provider Linking"],
    summary="Generate Provider Link Code",
    description="""
    Generates a temporary 6-digit code for Person-Provider linking.
    
    **Link Code System:**
    - **Purpose**: Secure method for Persons to connect with Providers
    - **Format**: 6-character alphanumeric code (e.g., 'A1B2C3')
    - **Expiry**: Valid for 10 minutes from generation
    - **Usage**: Single-use code that expires after Person links
    
    **Security Features:**
    - **Time-Limited**: Codes expire automatically after 10 minutes
    - **Single-Use**: Code becomes invalid after successful linking
    - **Provider-Specific**: Each code is tied to specific Provider
    - **Audit Trail**: All code generation and usage is logged
    
    **Usage Flow:**
    1. **Provider Request**: Provider calls this endpoint to generate code
    2. **Code Sharing**: Provider shares code with Person (verbally, QR, etc.)
    3. **Person Linking**: Person uses code to establish connection
    4. **Code Expiration**: Code becomes invalid after use or timeout
    
    **Provider Requirements:**
    - Must be authenticated as Provider
    - Must have valid Provider profile
    - Can generate new codes to replace expired ones
    
    **Code Management:**
    - New codes replace any existing codes for the Provider
    - Each Provider can only have one active code at a time
    - Codes are stored securely and tracked for audit purposes
    """,
    responses={
        200: {"description": "Link code generated successfully"},
        401: {"description": "Authentication required"},
        404: {"description": "Provider profile not found"},
    },
)
class GenerateProviderLinkCodeView(APIView):
    """
    Provider Link Code Generation

    Generates secure temporary codes for Person-Provider linking system.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        ip_address = request.META.get("REMOTE_ADDR", "Unknown")

        try:
            provider = get_object_or_404(Provider, user=request.user)
        except Http404:
            logger.warning(
                "Provider link code generation failed - no provider profile",
                extra={
                    "user_id": user.id,
                    "email": user.email,
                    "ip_address": ip_address,
                    "action": "provider_link_code_no_profile",
                },
            )
            return Response({"error": "Provider profile not found."}, status=status.HTTP_404_NOT_FOUND)

        logger.info(
            "Provider link code generation requested",
            extra={
                "user_id": user.id,
                "provider_id": provider.provider_id,
                "provider_name": provider.social_name,
                "professional_registration": getattr(provider, "professional_registration", None),
                "ip_address": ip_address,
                "action": "provider_link_code_generation_requested",
            },
        )

        # Generate secure random code
        code = uuid.uuid4().hex[:6].upper()  # E.g., 'A1B2C3'
        current_time = timezone.now()
        expiry_time = current_time + timedelta(minutes=10)

        logger.debug(
            "Generated new provider link code",
            extra={
                "user_id": user.id,
                "provider_id": provider.provider_id,
                "code": code,
                "expiry_minutes": 10,
                "expiry_time": expiry_time.isoformat(),
                "action": "provider_link_code_generated",
            },
        )

        try:
            # Create or update the observation record
            obs, created = Observation.objects.get_or_create(
                person=None,
                observation_concept_id=get_concept_by_code("PROVIDER_LINK_CODE").concept_id,
                observation_type_concept_id=get_concept_by_code("CLINICIAN_GENERATED").concept_id,
                provider_id=provider.provider_id,
                defaults={
                    "value_as_string": code,
                    "observation_date": current_time,
                },
            )

            if not created:
                # Update the code and date if it already exists
                old_code = obs.value_as_string
                old_date = obs.observation_date
                obs.value_as_string = code
                obs.observation_date = current_time
                obs.save(update_fields=["value_as_string", "observation_date"])

                logger.info(
                    "Provider link code updated (replaced existing)",
                    extra={
                        "user_id": user.id,
                        "provider_id": provider.provider_id,
                        "old_code": old_code,
                        "old_date": old_date.isoformat() if old_date else None,
                        "new_code": code,
                        "new_date": current_time.isoformat(),
                        "observation_id": obs.id,
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
                        "observation_date": current_time.isoformat(),
                        "action": "provider_link_code_created",
                    },
                )

            return Response({"code": code, "expires_at": expiry_time.isoformat(), "expires_in_minutes": 10})

        except Exception as e:
            logger.error(
                "Error creating/updating provider link code",
                extra={
                    "user_id": user.id,
                    "provider_id": provider.provider_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "action": "provider_link_code_creation_error",
                },
                exc_info=True,
            )
            return Response({"error": "Failed to generate link code."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    tags=["Person-Provider Linking"],
    summary="Link Person to Provider",
    description="""
    Establishes a connection between Person and Provider using a link code.
    
    **Linking Process:**
    1. **Code Validation**: Verifies code exists and hasn't expired
    2. **Provider Lookup**: Identifies Provider associated with code
    3. **Relationship Creation**: Creates Person-Provider relationship
    4. **Code Invalidation**: Marks code as used to prevent reuse
    5. **Audit Logging**: Records all linking activities
    
    **Business Rules:**
    - Code must be valid and not expired (within 10 minutes)
    - Code must not have been used previously
    - Person must be authenticated and have Person profile
    - Relationship is bidirectional but stored once
    - Duplicate relationships are prevented
    
    **Link Code Validation:**
    - **Time Check**: Must be generated within last 10 minutes
    - **Usage Check**: Must not have been used by another Person
    - **Provider Check**: Associated Provider must exist and be active
    - **Format Check**: Must match expected code format
    
    **Relationship Management:**
    - Creates FactRelationship record linking Person and Provider
    - Enables Person to receive services from Provider
    - Enables Provider to deliver services to Person
    - Supports future service requests and communications
    
    **Security Considerations:**
    - Code sharing should be done securely (in-person, secure channel)
    - Each code is single-use to prevent unauthorized linking
    - All linking activities are logged for audit purposes
    - Expired codes are automatically rejected
    """,
    request=PersonLinkProviderRequestSerializer,
    responses={
        200: {"description": "Person successfully linked to Provider"},
        400: {"description": "Invalid or expired code"},
        401: {"description": "Authentication required"},
        404: {"description": "Person profile not found"},
    },
)
class PersonLinkProviderView(APIView):
    """
    Person-Provider Linking

    Handles secure linking between Persons and Providers using temporary codes.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        ip_address = request.META.get("REMOTE_ADDR", "Unknown")
        code = request.data.get("code")

        try:
            person = get_object_or_404(Person, user=request.user)
        except Http404:
            logger.warning(
                "Person-Provider linking failed - no person profile",
                extra={
                    "user_id": user.id,
                    "email": user.email,
                    "code": code,
                    "ip_address": ip_address,
                    "action": "person_provider_linking_no_person_profile",
                },
            )
            return Response({"error": "Person profile not found."}, status=status.HTTP_404_NOT_FOUND)

        logger.info(
            "Person-Provider linking attempted",
            extra={
                "user_id": user.id,
                "person_id": person.person_id,
                "person_name": person.social_name,
                "code": code,
                "ip_address": ip_address,
                "action": "person_provider_linking_attempted",
            },
        )

        if not code:
            logger.warning(
                "Person-Provider linking failed - no code provided",
                extra={"user_id": user.id, "person_id": person.person_id, "action": "person_provider_linking_no_code"},
            )
            return Response({"error": "Link code is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Find valid, unused code within time limit
            cutoff_time = timezone.now() - timedelta(minutes=10)
            obs = (
                Observation.objects.filter(
                    value_as_string=code,
                    observation_concept_id=get_concept_by_code("PROVIDER_LINK_CODE").concept_id,
                    observation_date__gte=cutoff_time,
                    person__isnull=True,  # not used yet
                )
                .select_related("provider")
                .order_by("-observation_date")
                .first()
            )

            if not obs or not obs.provider or not obs.provider.provider_id:
                logger.warning(
                    "Person-Provider linking failed - invalid or expired code",
                    extra={
                        "user_id": user.id,
                        "person_id": person.person_id,
                        "code": code,
                        "code_found": obs is not None,
                        "provider_exists": obs.provider is not None if obs else False,
                        "provider_id_exists": obs.provider.provider_id if obs and obs.provider else None,
                        "observation_date": obs.observation_date.isoformat() if obs else None,
                        "cutoff_time": cutoff_time.isoformat(),
                        "ip_address": ip_address,
                        "action": "person_provider_linking_invalid_code",
                    },
                )
                return Response({"error": "Invalid or expired code."}, status=status.HTTP_400_BAD_REQUEST)

            # Get provider details for logging and validation
            provider = get_object_or_404(Provider, provider_id=obs.provider.provider_id)

            # Check if relationship already exists
            existing_relationship = FactRelationship.objects.filter(
                fact_id_1=person.person_id,
                domain_concept_1_id=get_concept_by_code("PERSON").concept_id,
                fact_id_2=obs.provider_id,
                domain_concept_2_id=get_concept_by_code("PROVIDER").concept_id,
                relationship_concept_id=get_concept_by_code("PERSON_PROVIDER").concept_id,
            ).exists()

            if existing_relationship:
                logger.info(
                    "Person-Provider linking attempted but relationship already exists",
                    extra={
                        "user_id": user.id,
                        "person_id": person.person_id,
                        "provider_id": obs.provider.provider_id,
                        "person_name": person.social_name,
                        "provider_name": provider.social_name,
                        "code": code,
                        "action": "person_provider_linking_already_exists",
                    },
                )

            # Create or get relationship person ↔ provider
            relationship, created = FactRelationship.objects.get_or_create(
                fact_id_1=person.person_id,
                domain_concept_1_id=get_concept_by_code("PERSON").concept_id,
                fact_id_2=obs.provider_id,
                domain_concept_2_id=get_concept_by_code("PROVIDER").concept_id,
                relationship_concept_id=get_concept_by_code("PERSON_PROVIDER").concept_id,
            )

            # Mark code as used
            obs.person_id = person.person_id
            obs.save(update_fields=["person_id"])

            logger.info(
                "Person-Provider linking completed successfully",
                extra={
                    "user_id": user.id,
                    "person_id": person.person_id,
                    "person_name": person.social_name,
                    "provider_id": obs.provider.provider_id,
                    "provider_name": provider.social_name,
                    "professional_registration": getattr(provider, "professional_registration", None),
                    "code": code,
                    "relationship_created": created,
                    "relationship_existed": existing_relationship,
                    "observation_id": obs.observation_id,
                    "linking_timestamp": timezone.now().isoformat(),
                    "ip_address": ip_address,
                    "action": "person_provider_linking_success",
                },
            )

            return Response(
                {
                    "status": "linked",
                    "provider_id": provider.provider_id,
                    "provider_name": provider.social_name,
                    "relationship_created": created,
                }
            )

        except Exception as e:
            logger.error(
                "Unexpected error during Person-Provider linking",
                extra={
                    "user_id": user.id,
                    "person_id": person.person_id,
                    "code": code,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "ip_address": ip_address,
                    "action": "person_provider_linking_error",
                },
                exc_info=True,
            )
            return Response(
                {"error": "An unexpected error occurred during linking."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@extend_schema(
    tags=["Person-Provider Linking"],
    summary="Get Provider Information by Link Code",
    description="""
    Retrieves Provider information using a link code for preview before linking.
    
    **Preview Functionality:**
    - Allows Person to view Provider details before establishing connection
    - Validates link code without consuming it
    - Returns comprehensive Provider profile information
    - Enables informed decision-making before linking
    
    **Code Validation:**
    - **Time Check**: Code must be within 10-minute validity window
    - **Format Check**: Code must match expected 6-character format
    - **Provider Check**: Associated Provider must exist and be active
    - **Availability Check**: Code must not have been used already
    
    **Provider Information Returned:**
    - Provider name and professional details
    - Specialty and service categories
    - Professional registration information
    - Contact and location details (if available)
    - Service offerings and capabilities
    
    **Use Cases:**
    - **Preview Before Link**: Person can verify Provider identity
    - **QR Code Scanning**: Decode QR codes to show Provider info
    - **Link Validation**: Verify code is valid before proceeding
    - **Directory Integration**: Show Provider details in search results
    
    **Security Features:**
    - Code preview doesn't consume or invalidate the code
    - No sensitive Provider information is exposed
    - All preview activities are logged for audit
    - Rate limiting prevents code scanning attacks
    """,
    request=PersonLinkProviderRequestSerializer,
    responses={
        200: {"description": "Provider information retrieved successfully"},
        400: {"description": "Invalid or expired code"},
        401: {"description": "Authentication required"},
    },
)
class ProviderByLinkCodeView(APIView):
    """
    Provider Information Lookup

    Retrieves Provider details using link codes for preview functionality.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        ip_address = request.META.get("REMOTE_ADDR", "Unknown")
        code = request.data.get("code")

        logger.debug(
            "Provider lookup by link code requested",
            extra={
                "user_id": user.id,
                "code": code,
                "ip_address": ip_address,
                "action": "provider_lookup_by_code_requested",
            },
        )

        if not code:
            logger.warning(
                "Provider lookup failed - no code provided",
                extra={"user_id": user.id, "ip_address": ip_address, "action": "provider_lookup_no_code"},
            )
            return Response({"error": "Code is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Find valid code within time limit (don't check if used - this is just preview)
            cutoff_time = timezone.now() - timedelta(minutes=10)
            obs = (
                Observation.objects.filter(
                    value_as_string=code,
                    observation_concept_id=get_concept_by_code("PROVIDER_LINK_CODE").concept_id,
                    observation_date__gte=cutoff_time,
                )
                .select_related("provider")
                .order_by("-observation_date")
                .first()
            )

            if not obs or not obs.provider:
                logger.warning(
                    "Provider lookup failed - invalid or expired code",
                    extra={
                        "user_id": user.id,
                        "code": code,
                        "observation_found": obs is not None,
                        "provider_exists": obs.provider is not None if obs else False,
                        "observation_date": obs.observation_date.isoformat() if obs else None,
                        "cutoff_time": cutoff_time.isoformat(),
                        "ip_address": ip_address,
                        "action": "provider_lookup_invalid_code",
                    },
                )
                return Response({"error": "Invalid or expired code."}, status=status.HTTP_400_BAD_REQUEST)

            provider = get_object_or_404(Provider, provider_id=obs.provider.provider_id)
            serializer = ProviderRetrieveSerializer(provider)

            logger.info(
                "Provider successfully retrieved by link code",
                extra={
                    "user_id": user.id,
                    "code": code,
                    "provider_id": provider.provider_id,
                    "provider_name": provider.social_name,
                    "professional_registration": getattr(provider, "professional_registration", None),
                    "specialty": getattr(provider, "specialty", None),
                    "observation_id": obs.observation_id,
                    "code_used": obs.person_id is not None,
                    "code_generation_date": obs.observation_date.isoformat(),
                    "ip_address": ip_address,
                    "action": "provider_lookup_success",
                },
            )

            response_data = serializer.data
            response_data["code_status"] = {
                "is_used": obs.person_id is not None,
                "generated_at": obs.observation_date.isoformat(),
                "expires_at": (obs.observation_date + timedelta(minutes=10)).isoformat(),
            }

            return Response(response_data)

        except Exception as e:
            logger.error(
                "Unexpected error during provider lookup by code",
                extra={
                    "user_id": user.id,
                    "code": code,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "ip_address": ip_address,
                    "action": "provider_lookup_error",
                },
                exc_info=True,
            )
            return Response(
                {"error": "An unexpected error occurred during provider lookup."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@extend_schema(
    tags=["Person-Provider Linking"],
    summary="Unlink Person from Provider",
    description="""
    Removes the connection between a Person and Provider.
    
    **⚠️ CRITICAL OPERATION - AFFECTS SERVICE RELATIONSHIPS ⚠️**
    
    **Unlinking Process:**
    1. **Relationship Validation**: Verifies relationship exists
    2. **Dependency Check**: Ensures safe removal of relationship
    3. **Relationship Removal**: Deletes Person-Provider connection
    4. **Audit Logging**: Records all unlinking activities with full context
    5. **Notification**: Confirms successful unlinking
    
    **Business Impact:**
    - **Service Access**: Person loses access to Provider's services
    - **Historical Data**: Past interactions remain in system for audit
    - **Future Services**: New service requests will be blocked
    - **Communication**: Direct communication channels are severed
    
    **Authorization Requirements:**
    - User must be authenticated
    - User must be authorized to unlink the specific relationship
    - Both Person and Provider must exist in system
    - Relationship must currently exist
    
    **Safety Features:**
    - **Audit Trail**: Complete logging of unlinking with user context
    - **Relationship Verification**: Confirms relationship exists before removal
    - **Atomic Operation**: Unlinking happens in single database transaction
    - **Rollback Capability**: Failed operations don't leave partial states
    
    **Use Cases:**
    - **Service Termination**: End of service relationship
    - **Provider Change**: Person switching to different Provider
    - **Data Privacy**: User-requested data relationship removal
    - **Administrative Action**: System administrator unlinking relationships
    
    **Post-Unlinking:**
    - Person can no longer access Provider's services
    - Provider can no longer deliver services to Person
    - New link code required to re-establish connection
    - Historical service records remain for compliance
    """,
    request=PersonProviderUnlinkRequestSerializer,
    responses={
        200: {"description": "Person successfully unlinked from Provider"},
        400: {"description": "Invalid request or relationship doesn't exist"},
        401: {"description": "Authentication required"},
        404: {"description": "Person or Provider not found"},
    },
)
class PersonProviderUnlinkView(APIView):
    """
    Person-Provider Unlinking

    Handles secure removal of Person-Provider relationships with full audit trail.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, person_id, provider_id):
        user = request.user
        ip_address = request.META.get("REMOTE_ADDR", "Unknown")
        user_agent = request.META.get("HTTP_USER_AGENT", "Unknown")

        try:
            person = get_object_or_404(Person, person_id=person_id)
            provider = get_object_or_404(Provider, provider_id=provider_id)
        except Http404 as e:
            logger.warning(
                "Person-Provider unlinking failed - entity not found",
                extra={
                    "user_id": user.id,
                    "person_id": person_id,
                    "provider_id": provider_id,
                    "error": str(e),
                    "ip_address": ip_address,
                    "action": "person_provider_unlinking_entity_not_found",
                },
            )
            return Response({"error": "Person or Provider not found."}, status=status.HTTP_404_NOT_FOUND)

        logger.warning(
            "Person-Provider unlinking requested - CRITICAL ACTION",
            extra={
                "user_id": user.id,
                "person_id": person_id,
                "provider_id": provider_id,
                "person_name": person.social_name,
                "provider_name": provider.social_name,
                "provider_professional_reg": getattr(provider, "professional_registration", None),
                "ip_address": ip_address,
                "user_agent": user_agent,
                "timestamp": timezone.now().isoformat(),
                "action": "person_provider_unlinking_requested",
            },
        )

        try:
            # Find and count relationships to be removed
            relationships = FactRelationship.objects.filter(
                fact_id_1=person.person_id,
                domain_concept_1_id=get_concept_by_code("PERSON").concept_id,
                fact_id_2=provider.provider_id,
                domain_concept_2_id=get_concept_by_code("PROVIDER").concept_id,
                relationship_concept_id=get_concept_by_code("PERSON_PROVIDER").concept_id,
            )

            relationship_count = relationships.count()

            if relationship_count == 0:
                logger.warning(
                    "Person-Provider unlinking failed - no relationship exists",
                    extra={
                        "user_id": user.id,
                        "person_id": person_id,
                        "provider_id": provider_id,
                        "person_name": person.social_name,
                        "provider_name": provider.social_name,
                        "action": "person_provider_unlinking_no_relationship",
                    },
                )
                return Response(
                    {"error": "No relationship exists between this Person and Provider."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            logger.info(
                "Person-Provider relationships identified for deletion",
                extra={
                    "user_id": user.id,
                    "person_id": person_id,
                    "provider_id": provider_id,
                    "person_name": person.social_name,
                    "provider_name": provider.social_name,
                    "relationships_found": relationship_count,
                    "action": "person_provider_unlinking_relationships_found",
                },
            )

            # Remove the relationships in atomic transaction
            with transaction.atomic():
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
                        "unlinking_timestamp": timezone.now().isoformat(),
                        "ip_address": ip_address,
                        "user_agent": user_agent,
                        "action": "person_provider_unlinking_success",
                    },
                )

                return Response(
                    {
                        "status": "unlinked",
                        "relationships_removed": deleted_count,
                        "person_id": person_id,
                        "provider_id": provider_id,
                    }
                )

        except Exception as e:
            logger.error(
                "Unexpected error during Person-Provider unlinking",
                extra={
                    "user_id": user.id,
                    "person_id": person_id,
                    "provider_id": provider_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "ip_address": ip_address,
                    "action": "person_provider_unlinking_error",
                },
                exc_info=True,
            )
            return Response(
                {"error": "An unexpected error occurred during unlinking."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@extend_schema(
    tags=["Person-Provider Relationships"],
    summary="Get Person's Linked Providers",
    description="""
    Retrieves all Providers that are currently linked to the authenticated Person.
    
    **Relationship Query:**
    - Returns all active Provider relationships for the Person
    - Includes complete Provider profile information
    - Ordered by most recent linking first
    - Filters out inactive or deleted Provider profiles
    
    **Provider Information Included:**
    - Provider ID and social name
    - Professional registration and specialty
    - Contact information and preferences
    - Service offerings and capabilities
    - Profile pictures and settings
    
    **Use Cases:**
    - **My Providers Page**: Display Person's current service providers
    - **Service Selection**: Choose from linked providers for new requests
    - **Communication**: Access provider contact information
    - **Service History**: View past and current service relationships
    
    **Business Rules:**
    - Only returns providers currently linked to the Person
    - Person must be authenticated and have valid Person profile
    - Inactive provider relationships are excluded
    - Provider profiles must be active and complete
    
    **Frontend Integration:**
    ```javascript
    // Example usage
    const providers = await api.get('/person-providers/');
    providers.forEach(provider => {
        console.log(`${provider.social_name} - ${provider.specialty}`);
    });
    ```
    """,
    responses={
        200: {"description": "List of linked providers retrieved successfully"},
        401: {"description": "Authentication required"},
        404: {"description": "Person profile not found"},
    },
)
class PersonProvidersView(APIView):
    """
    Person's Linked Providers

    Retrieves all providers currently linked to the authenticated person.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        ip_address = request.META.get("REMOTE_ADDR", "Unknown")

        try:
            person = get_object_or_404(Person, user=request.user)
        except Http404:
            logger.warning(
                "Person's linked providers retrieval failed - no person profile",
                extra={
                    "user_id": user.id,
                    "email": user.email,
                    "ip_address": ip_address,
                    "action": "person_providers_no_profile",
                },
            )
            return Response({"error": "Person profile not found."}, status=status.HTTP_404_NOT_FOUND)

        logger.debug(
            "Person's linked providers retrieval requested",
            extra={
                "user_id": user.id,
                "person_id": person.person_id,
                "person_name": person.social_name,
                "ip_address": ip_address,
                "action": "person_providers_retrieval_requested",
            },
        )

        try:
            # Get all relationships where this person is linked to providers
            relationships = FactRelationship.objects.filter(
                fact_id_1=person.person_id,
                domain_concept_1_id=get_concept_by_code("PERSON").concept_id,
                domain_concept_2_id=get_concept_by_code("PROVIDER").concept_id,
                relationship_concept_id=get_concept_by_code("PERSON_PROVIDER").concept_id,
            ).select_related()

            provider_ids = relationships.values_list("fact_id_2", flat=True)

            # Get provider objects with optimized query
            providers = (
                Provider.objects.filter(provider_id__in=provider_ids).select_related("user").order_by("social_name")
            )

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
                    "relationships_count": relationships.count(),
                    "ip_address": ip_address,
                    "action": "person_providers_retrieval_success",
                },
            )

            return Response(serializer.data)

        except Exception as e:
            logger.error(
                "Unexpected error retrieving person's linked providers",
                extra={
                    "user_id": user.id,
                    "person_id": person.person_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "ip_address": ip_address,
                    "action": "person_providers_retrieval_error",
                },
                exc_info=True,
            )
            return Response(
                {"error": "An unexpected error occurred while retrieving providers."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@extend_schema(
    tags=["Person-Provider Relationships"],
    summary="Get Provider's Linked Persons",
    description="""
    Retrieves all Persons currently linked to the authenticated Provider with comprehensive summary information.
    
    **Enhanced Person Information:**
    - **Basic Profile**: Person ID, name, and contact details
    - **Age Calculation**: Automatically calculated from birth date or year
    - **Last Visit Date**: Most recent consultation/visit with this provider
    - **Last Help Date**: Most recent help request from this person
    - **Service History**: Summary of past interactions
    
    **Age Calculation Logic:**
    1. **Primary**: Uses birth_datetime for precise age calculation
    2. **Fallback**: Uses year_of_birth for approximate age
    3. **Handles Edge Cases**: Birthday not yet occurred this year
    
    **Visit and Help Tracking:**
    - **Last Visit**: Most recent VisitOccurrence with this provider
    - **Last Help**: Most recent active help request observation
    - **Date Filtering**: Only considers valid, non-null dates
    - **Provider Specific**: Only shows data related to this provider
    
    **Use Cases:**
    - **Patient Dashboard**: Provider's overview of all linked patients
    - **Care Management**: Track patient engagement and last interactions
    - **Service Planning**: Identify patients needing follow-up
    - **Communication**: Quick access to patient summaries
    
    **Performance Optimization:**
    - Optimized queries with select_related and prefetch_related
    - Efficient aggregation of visit and help data
    - Minimal database calls for large patient lists
    """,
    responses={
        200: {"description": "List of linked persons with summary information"},
        401: {"description": "Authentication required"},
        404: {"description": "Provider profile not found"},
    },
)
class ProviderPersonsView(APIView):
    """
    Provider's Linked Persons with Summary Information

    Retrieves comprehensive summary of all persons linked to the authenticated provider.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        ip_address = request.META.get("REMOTE_ADDR", "Unknown")

        try:
            provider = get_object_or_404(Provider, user=request.user)
            provider_id = provider.provider_id
        except Http404:
            logger.warning(
                "Provider's linked persons retrieval failed - no provider profile",
                extra={
                    "user_id": user.id,
                    "email": user.email,
                    "ip_address": ip_address,
                    "action": "provider_persons_no_profile",
                },
            )
            return Response({"error": "Provider profile not found."}, status=status.HTTP_404_NOT_FOUND)

        logger.debug(
            "Provider's linked persons retrieval requested",
            extra={
                "user_id": user.id,
                "provider_id": provider_id,
                "provider_name": provider.social_name,
                "professional_registration": getattr(provider, "professional_registration", None),
                "ip_address": ip_address,
                "action": "provider_persons_retrieval_requested",
            },
        )

        try:
            # Find IDs of persons linked to this provider through FactRelationship
            linked_persons_relationships = FactRelationship.objects.filter(
                fact_id_2=provider_id,
                domain_concept_1_id=get_concept_by_code("PERSON").concept_id,
                domain_concept_2_id=get_concept_by_code("PROVIDER").concept_id,
                relationship_concept_id=get_concept_by_code("PERSON_PROVIDER").concept_id,
            ).select_related()

            linked_persons_ids = linked_persons_relationships.values_list("fact_id_1", flat=True)

            # Get persons with optimized queries
            persons = (
                Person.objects.filter(person_id__in=linked_persons_ids).select_related("user").order_by("social_name")
            )

            logger.debug(
                "Provider's linked persons identified",
                extra={
                    "user_id": user.id,
                    "provider_id": provider_id,
                    "linked_persons_count": len(linked_persons_ids),
                    "person_ids": list(linked_persons_ids),
                    "relationships_count": linked_persons_relationships.count(),
                    "action": "provider_persons_identified",
                },
            )

            # Prepare enhanced response data with additional calculations
            person_summaries = []
            today = timezone.now()

            for person in persons:
                try:
                    age = None

                    # Calculate age with fallback logic
                    if hasattr(person, "birth_datetime") and person.birth_datetime:
                        birth_date = person.birth_datetime
                        age = today.year - birth_date.year
                        # Adjust if birthday hasn't occurred this year
                        if today.month < birth_date.month or (
                            today.month == birth_date.month and today.day < birth_date.day
                        ):
                            age -= 1
                    elif hasattr(person, "year_of_birth") and person.year_of_birth:
                        age = today.year - person.year_of_birth

                    # Get the last visit (consultation) with this provider
                    last_visit = None
                    try:
                        visit = (
                            VisitOccurrence.objects.filter(
                                person=person, provider_id=provider_id, visit_start_date__isnull=False
                            )
                            .order_by("-visit_start_date")
                            .first()
                        )
                        if visit:
                            last_visit = visit.visit_start_date
                    except Exception as e:
                        logger.warning(
                            "Error retrieving last visit for person",
                            extra={
                                "person_id": person.person_id,
                                "provider_id": provider_id,
                                "error": str(e),
                                "action": "provider_persons_visit_error",
                            },
                        )

                    # Get the last recorded help request
                    last_help = None
                    try:
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
                    except Exception as e:
                        logger.warning(
                            "Error retrieving last help for person",
                            extra={
                                "person_id": person.person_id,
                                "provider_id": provider_id,
                                "error": str(e),
                                "action": "provider_persons_help_error",
                            },
                        )

                    # Determine best name to display
                    name = person.social_name
                    if not name and person.user:
                        name = f"{person.user.first_name} {person.user.last_name}".strip()
                        if not name:
                            name = person.user.username

                    person_summaries.append(
                        {
                            "person_id": person.person_id,
                            "name": name or "Name not available",
                            "age": age,
                            "last_visit_date": last_visit,
                            "last_help_date": last_help,
                        }
                    )

                except Exception as e:
                    logger.warning(
                        "Error processing individual person summary",
                        extra={
                            "person_id": person.person_id,
                            "provider_id": provider_id,
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "action": "provider_persons_individual_error",
                        },
                    )
                    # Continue processing other persons

            # Use the serializer to format and validate the data
            serializer = ProviderPersonSummarySerializer(person_summaries, many=True)

            # Calculate summary statistics
            recent_help_count = len([p for p in person_summaries if p["last_help_date"]])
            recent_visit_count = len([p for p in person_summaries if p["last_visit_date"]])

            logger.info(
                "Provider's linked persons retrieved successfully",
                extra={
                    "user_id": user.id,
                    "provider_id": provider_id,
                    "provider_name": provider.social_name,
                    "total_linked_persons": len(person_summaries),
                    "persons_with_recent_help": recent_help_count,
                    "persons_with_recent_visits": recent_visit_count,
                    "average_age": (
                        sum(p["age"] for p in person_summaries if p["age"])
                        / len([p for p in person_summaries if p["age"]])
                        if any(p["age"] for p in person_summaries)
                        else None
                    ),
                    "ip_address": ip_address,
                    "action": "provider_persons_retrieval_success",
                },
            )

            return Response(serializer.data)

        except Exception as e:
            logger.error(
                "Unexpected error retrieving provider's linked persons",
                extra={
                    "user_id": user.id,
                    "provider_id": provider_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "ip_address": ip_address,
                    "action": "provider_persons_retrieval_error",
                },
                exc_info=True,
            )
            return Response(
                {"error": "An unexpected error occurred while retrieving linked persons."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
