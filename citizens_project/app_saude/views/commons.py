import logging

from django.contrib.auth import get_user_model
from rest_framework import viewsets

from ..models import *
from ..serializers import *
from ..utils.provider import *

User = get_user_model()
logger = logging.getLogger("app_saude")


class UserRole:
    """
    Utility class to determine user roles within the system.

    Provides methods to identify whether a user is a Provider, Person, or has no specific role.
    """

    def get_role(self, request):
        """
        Determine the role of the authenticated user.

        Args:
            request: Django request object with authenticated user

        Returns:
            str: "provider", "person", or "none"
        """
        try:
            user_id = getattr(request.user, "id", "Unknown")
            logger.debug(f"Determining role for user ID: {user_id}")

            role = "none"
            if Provider.objects.filter(user=request.user).exists():
                role = "provider"
                logger.debug(f"User ID {user_id} identified as provider")
            elif Person.objects.filter(user=request.user).exists():
                role = "person"
                logger.debug(f"User ID {user_id} identified as person")
            else:
                logger.debug(f"User ID {user_id} has no specific role")

            return role

        except Exception as e:
            logger.error(f"Error determining user role: {str(e)}", exc_info=True)
            return "none"  # Default to "none" on error


class FlexibleViewSet(viewsets.ModelViewSet):
    """
    Flexible ViewSet that dynamically selects serializers based on action.

    Convention: Serializers should be named as {ClassName}CreateSerializer,
    {ClassName}UpdateSerializer, {ClassName}RetrieveSerializer.
    """

    def get_serializer_class(self):
        """
        Dynamically determine serializer class based on action and naming convention.

        Returns:
            Serializer class for the current action
        """
        try:
            prefix = self.__class__.__name__.replace("ViewSet", "")
            action = getattr(self, "action", "retrieve")

            logger.debug(f"Selecting serializer for ViewSet: {prefix}, Action: {action}")

            if action == "create":
                serializer_name = f"{prefix}CreateSerializer"
            elif action in ["update", "partial_update"]:
                serializer_name = f"{prefix}UpdateSerializer"
            else:
                serializer_name = f"{prefix}RetrieveSerializer"

            try:
                serializer_class = globals()[serializer_name]
                logger.debug(f"Selected serializer: {serializer_name}")
                return serializer_class
            except KeyError:
                logger.error(f"Serializer {serializer_name} not found in globals()")
                raise AttributeError(f"Serializer {serializer_name} not found")

        except Exception as e:
            logger.error(f"Error selecting serializer class: {str(e)}", exc_info=True)
            raise
