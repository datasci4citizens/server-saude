import logging

from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema

from ..models import *
from ..serializers import *
from ..utils.provider import *
from .commons import FlexibleViewSet

User = get_user_model()
logger = logging.getLogger("app_saude")


@extend_schema(tags=["Location Management"])
class LocationViewSet(FlexibleViewSet):
    """
    Location Management

    Manages geographic locations including addresses, facilities, and service areas.
    Used for location-based services and geographic data organization.
    """

    queryset = Location.objects.all()


@extend_schema(tags=["Healthcare Facilities"])
class CareSiteViewSet(FlexibleViewSet):
    """
    Care Site Management

    Manages healthcare facilities and service locations where care is provided.
    Links providers to specific locations and facilities.
    """

    queryset = CareSite.objects.all()


@extend_schema(tags=["Clinical Data"])
class DrugExposureViewSet(FlexibleViewSet):
    """
    Drug Exposure Management

    Manages records of drug/medication exposures and prescriptions.
    Tracks medication history and drug-related events.
    """

    queryset = DrugExposure.objects.all()


@extend_schema(tags=["Clinical Data"])
class ObservationViewSet(FlexibleViewSet):
    """
    Observation Management

    Manages clinical observations, assessments, and findings.
    Includes vital signs, symptoms, and other observed clinical data.
    """

    queryset = Observation.objects.all()


@extend_schema(tags=["Clinical Data"])
class VisitOccurrenceViewSet(FlexibleViewSet):
    """
    Visit Occurrence Management

    Manages records of healthcare visits and encounters.
    Tracks when and where patients receive care services.
    """

    queryset = VisitOccurrence.objects.all()


@extend_schema(tags=["Clinical Data"])
class MeasurementViewSet(FlexibleViewSet):
    """
    Measurement Management

    Manages quantitative clinical measurements and test results.
    Includes lab values, vital signs, and other measured clinical data.
    """

    queryset = Measurement.objects.all()


@extend_schema(tags=["Data Relationships"])
class FactRelationshipViewSet(FlexibleViewSet):
    """
    Fact Relationship Management

    Manages relationships between different clinical/service facts.
    Enables complex data modeling and relationship tracking across entities.
    """

    queryset = FactRelationship.objects.all()
