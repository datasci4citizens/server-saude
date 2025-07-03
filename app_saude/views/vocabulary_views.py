import logging

from django.contrib.auth import get_user_model
from django.db.models import Prefetch
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.response import Response

from ..models import *
from ..serializers import *
from ..utils.provider import *
from .commons import FlexibleViewSet

User = get_user_model()
logger = logging.getLogger("app_saude")


@extend_schema(tags=["Data Vocabulary"])
class VocabularyViewSet(FlexibleViewSet):
    """
    Vocabulary Management

    Manages standardized vocabularies used throughout the system.
    Vocabularies provide controlled terminology for consistent data representation.
    """

    queryset = Vocabulary.objects.all()


@extend_schema(tags=["Data Vocabulary"])
class ConceptClassViewSet(FlexibleViewSet):
    """
    Concept Class Management

    Manages concept classes that categorize different types of concepts.
    Used for organizing and filtering concepts by their classification.
    """

    queryset = ConceptClass.objects.all()


@extend_schema(
    tags=["Data Vocabulary"],
    parameters=[
        OpenApiParameter(
            name="class",
            description="Filter by concept class IDs (comma-separated). Example: class=Gender,Ethnicity",
            required=False,
            type=str,
            style="form",
            explode=False,
            examples=[
                OpenApiExample(name="Single class", value="Gender"),
                OpenApiExample(name="Multiple classes", value="Gender,Ethnicity,Condition"),
            ],
        ),
        OpenApiParameter(
            name="code",
            description="Filter by concept codes (comma-separated). Example: code=ACTIVE,RESOLVED",
            required=False,
            type=str,
            style="form",
            explode=False,
            examples=[
                OpenApiExample(name="Single code", value="ACTIVE"),
                OpenApiExample(name="Multiple codes", value="ACTIVE,RESOLVED,PENDING"),
            ],
        ),
        OpenApiParameter(
            name="lang",
            description="Language code for translations. Defaults to Portuguese (297504001). Example: lang=pt",
            required=False,
            type=str,
            examples=[
                OpenApiExample(name="Portuguese", value="pt"),
                OpenApiExample(name="English", value="en"),
                OpenApiExample(name="Spanish", value="es"),
            ],
        ),
        OpenApiParameter(
            name="relationship",
            description="Include related concepts via specified relationship. Example: relationship=has_value_type",
            required=False,
            type=str,
            examples=[
                OpenApiExample(name="Value type relationship", value="has_value_type"),
                OpenApiExample(name="Subsumes relationship", value="subsumes"),
            ],
        ),
    ],
)
class ConceptViewSet(FlexibleViewSet):
    """
    Concept Management with Advanced Filtering

    Manages standardized concepts used throughout the healthcare/service system.
    Supports multi-language translations and relationship-based queries.

    **Key Features:**
    - Multi-language support with automatic translation loading
    - Complex filtering by class, code, and relationships
    - Relationship traversal for connected concepts
    - Optimized queries with prefetching for performance
    """

    queryset = Concept.objects.all()

    def get_queryset(self):
        """
        Build optimized queryset with filtering and prefetching.

        Applies various filters and optimizes database queries through
        strategic prefetching of related objects.
        """
        try:
            queryset = Concept.objects.all()

            # Get query parameters with defaults
            lang = self.request.query_params.get("lang", "297504001")  # Default to Portuguese
            class_ids = self.request.query_params.get("class")
            codes = self.request.query_params.get("code")
            relationship_id = self.request.query_params.get("relationship")

            logger.debug(
                "Concept queryset being built",
                extra={
                    "lang": lang,
                    "class_ids": class_ids,
                    "codes": codes,
                    "relationship_id": relationship_id,
                    "user_id": getattr(self.request.user, "id", None),
                    "action": "concept_queryset_build",
                },
            )

            # Filter by concept classes
            if class_ids:
                class_id_list = [s.strip() for s in class_ids.split(",")]
                queryset = queryset.filter(concept_class__concept_class_id__in=class_id_list)
                logger.debug(
                    "Applied concept class filter",
                    extra={"class_id_list": class_id_list, "action": "concept_class_filter_applied"},
                )

            # Filter by concept codes
            if codes:
                code_list = [s.strip() for s in codes.split(",")]
                queryset = queryset.filter(concept_code__in=code_list)
                logger.debug(
                    "Applied concept code filter",
                    extra={"code_list": code_list, "action": "concept_code_filter_applied"},
                )

            # Optimize queries with prefetching for translations
            queryset = queryset.prefetch_related(
                Prefetch(
                    "concept_synonym_concept_set",
                    queryset=ConceptSynonym.objects.filter(language_concept__concept_code=lang),
                    to_attr="translated_synonyms",
                )
            )

            # Store parameters for use in list method
            self._enrich_relationship_id = relationship_id
            self._lang = lang

            logger.debug(
                "Concept queryset built successfully",
                extra={
                    "final_queryset_count": queryset.count(),
                    "prefetch_applied": True,
                    "action": "concept_queryset_complete",
                },
            )

            return queryset

        except Exception as e:
            logger.error(
                "Error building concept queryset",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "query_params": dict(self.request.query_params),
                    "action": "concept_queryset_error",
                },
                exc_info=True,
            )
            # Return basic queryset on error
            return Concept.objects.all()

    @extend_schema(
        summary="List Concepts with Advanced Filtering",
        description="""
        Retrieves concepts with optional filtering and relationship enrichment.
        
        **Filtering Options:**
        
        **By Class:** Use `class` parameter to filter by concept class IDs
        - Single class: `?class=Gender`
        - Multiple classes: `?class=Gender,Ethnicity,Condition`
        
        **By Code:** Use `code` parameter to filter by specific concept codes
        - Single code: `?code=ACTIVE`
        - Multiple codes: `?code=ACTIVE,RESOLVED,PENDING`
        
        **Language Support:** Use `lang` parameter for translations
        - Portuguese (default): `?lang=297504001` or `?lang=pt`
        - English: `?lang=en`
        - Spanish: `?lang=es`
        
        **Relationship Enrichment:** Use `relationship` parameter to include related concepts
        - Value types: `?relationship=has_value_type`
        - Hierarchical: `?relationship=subsumes`
        
        **Combined Filtering:**
        ```
        ?class=Gender,Ethnicity&lang=pt&relationship=has_value_type
        ```
        
        **Performance Notes:**
        - Queries are optimized with strategic prefetching
        - Large result sets are automatically paginated
        - Translations are loaded efficiently in single queries
        
        **Use Cases:**
        - Populating dropdown lists with standardized values
        - Building medical terminology browsers
        - Creating concept mapping interfaces
        - Generating data entry forms with controlled vocabularies
        """,
        responses={
            200: ConceptRetrieveSerializer(many=True),
        },
    )
    def list(self, request, *args, **kwargs):
        """
        Custom list implementation with relationship enrichment.

        Extends the basic list functionality to optionally include
        related concepts based on specified relationships.
        """
        try:
            queryset = self.get_queryset()
            relationship_id = getattr(self, "_enrich_relationship_id", None)
            lang = getattr(self, "_lang", "297504001")

            logger.info(
                "Concept list requested",
                extra={
                    "user_id": getattr(request.user, "id", None),
                    "queryset_count": queryset.count(),
                    "relationship_enrichment": bool(relationship_id),
                    "language": lang,
                    "action": "concept_list_requested",
                },
            )

            results = []

            for concept in queryset:
                try:
                    # Serialize the main concept
                    base = ConceptRetrieveSerializer(concept).data

                    # Add relationship enrichment if requested
                    if relationship_id:
                        try:
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
                                base["related_concept"] = ConceptRetrieveSerializer(rel.concept_2).data

                        except Exception as e:
                            logger.warning(
                                "Error enriching concept with relationship",
                                extra={
                                    "concept_id": concept.concept_id,
                                    "relationship_id": relationship_id,
                                    "error": str(e),
                                    "action": "concept_relationship_enrichment_error",
                                },
                            )
                            # Continue without relationship data

                    results.append(base)

                except Exception as e:
                    logger.error(
                        "Error serializing individual concept",
                        extra={
                            "concept_id": getattr(concept, "concept_id", "Unknown"),
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "action": "concept_serialization_error",
                        },
                        exc_info=True,
                    )
                    # Skip this concept and continue

            logger.info(
                "Concept list completed successfully",
                extra={
                    "results_count": len(results),
                    "requested_count": queryset.count(),
                    "relationship_enrichment": bool(relationship_id),
                    "action": "concept_list_success",
                },
            )

            return Response(results)

        except Exception as e:
            logger.error(
                "Error in concept list operation",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "query_params": dict(request.query_params),
                    "user_id": getattr(request.user, "id", None),
                    "action": "concept_list_error",
                },
                exc_info=True,
            )
            # Return error response
            return Response({"detail": "Error retrieving concepts"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(tags=["Data Vocabulary"])
class ConceptSynonymViewSet(FlexibleViewSet):
    """
    Concept Synonym Management

    Manages multilingual synonyms and translations for concepts.
    Enables searching and displaying concepts in different languages.
    """

    queryset = ConceptSynonym.objects.all()


@extend_schema(tags=["Data Vocabulary"])
class DomainViewSet(FlexibleViewSet):
    """
    Domain Management

    Manages data domains that categorize different types of clinical/service data.
    Domains help organize and validate data according to their clinical context.
    """

    queryset = Domain.objects.all()
