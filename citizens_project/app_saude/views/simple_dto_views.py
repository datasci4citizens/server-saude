import logging

from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated

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
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Filter queryset to only return drug exposures for the authenticated user.
        Prevents unauthorized access to other users' medication data.
        """
        try:
            person = Person.objects.get(user=self.request.user)
            return DrugExposure.objects.filter(person=person)
        except Person.DoesNotExist:
            return DrugExposure.objects.none()


@extend_schema(tags=["Clinical Data"])
class ObservationViewSet(FlexibleViewSet):
    """
    Observation Management

    Manages clinical observations, assessments, and findings.
    Includes vital signs, symptoms, and other observed clinical data.
    """

    queryset = Observation.objects.all()
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Filter queryset to only return observations for the authenticated user.
        Supports both Person (patient) and Provider views.
        """
        user = self.request.user
        try:
            # Check if user is a Person (patient)
            person = Person.objects.get(user=user)
            return Observation.objects.filter(person=person)
        except Person.DoesNotExist:
            pass

        try:
            # Check if user is a Provider
            provider = Provider.objects.get(user=user)
            # Providers can only see observations where they are the provider
            # and the person has shared_with_provider=True
            return Observation.objects.filter(provider=provider, shared_with_provider=True)
        except Provider.DoesNotExist:
            pass

        # User is neither Person nor Provider
        return Observation.objects.none()


@extend_schema(tags=["Clinical Data"])
class VisitOccurrenceViewSet(FlexibleViewSet):
    """
    Visit Occurrence Management

    Manages records of healthcare visits and encounters.
    Tracks when and where patients receive care services.
    """

    queryset = VisitOccurrence.objects.all()
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Filter queryset to only return visits for the authenticated user.
        Supports both Person (patient) and Provider views.
        """
        user = self.request.user
        try:
            # Check if user is a Person (patient)
            person = Person.objects.get(user=user)
            return VisitOccurrence.objects.filter(person=person)
        except Person.DoesNotExist:
            pass

        try:
            # Check if user is a Provider
            provider = Provider.objects.get(user=user)
            # Providers can only see visits where they are the provider
            return VisitOccurrence.objects.filter(provider=provider)
        except Provider.DoesNotExist:
            pass

        # User is neither Person nor Provider
        return VisitOccurrence.objects.none()


@extend_schema(tags=["Clinical Data"])
class MeasurementViewSet(FlexibleViewSet):
    """
    Measurement Management

    Manages quantitative clinical measurements and test results.
    Includes lab values, vital signs, and other measured clinical data.
    """

    queryset = Measurement.objects.all()
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Filter queryset to only return measurements for the authenticated user.
        Prevents unauthorized access to other users' clinical data.
        """
        try:
            person = Person.objects.get(user=self.request.user)
            return Measurement.objects.filter(person=person)
        except Person.DoesNotExist:
            return Measurement.objects.none()


@extend_schema(tags=["Data Relationships"])
class FactRelationshipViewSet(FlexibleViewSet):
    """
    Fact Relationship Management

    Manages relationships between different clinical/service facts.
    Enables complex data modeling and relationship tracking across entities.
    """

    queryset = FactRelationship.objects.all()
