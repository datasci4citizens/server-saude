import logging

from django.contrib.auth import authenticate, get_user_model
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from app_saude.serializers import AuthSerializer
from libs.google import GoogleUserData, google_get_user_data

from ..models import *
from ..serializers import *
from ..utils.provider import *

User = get_user_model()
logger = logging.getLogger("app_saude")


class GoogleLoginView(APIView):
    """
    Google OAuth2 Login Endpoint

    Authenticates users using Google OAuth2 tokens and returns JWT tokens.
    Creates new users automatically on first login.
    """

    serializer_class = AuthSerializer
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Google OAuth2 Login",
        description="""
        Authenticates a user using Google OAuth2 access token.
        
        **Flow:**
        1. Client obtains Google OAuth2 token from Google
        2. Client sends token to this endpoint
        3. Server validates token with Google
        4. Server creates user if first time login
        5. Server returns JWT tokens and user profile data
        
        **User Creation:**
        - New users are automatically created on first login
        - User data is fetched from Google profile
        - Existing users have their profile updated with latest Google data
        
        **Role Detection:**
        The system automatically detects if the user is registered as:
        - Provider: Service provider in the platform
        - Person: Regular user/customer
        - None: New user not yet assigned a role
        """,
        request=AuthSerializer,
        responses={
            200: AuthTokenResponseSerializer,
            400: {
                "description": "Invalid request data",
            },
            401: {
                "description": "Authentication failed",
            },
            500: {
                "description": "Server error",
            },
        },
        examples=[
            OpenApiExample(
                name="Successful login response",
                value={
                    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                    "provider_id": "PROV123",
                    "person_id": None,
                    "role": "provider",
                    "user_id": 42,
                    "full_name": "João Silva",
                    "email": "joao.silva@example.com",
                    "social_name": "João",
                    "profile_picture": "https://lh3.googleusercontent.com/...",
                    "use_dark_mode": False,
                },
            )
        ],
        tags=["Authentication"],
    )
    def post(self, request, *args, **kwargs):
        try:
            logger.info(f"Google login attempt from IP: {request.META.get('REMOTE_ADDR')}")

            auth_serializer = self.serializer_class(data=request.data)
            auth_serializer.is_valid(raise_exception=True)

            validated_data = auth_serializer.validated_data
            logger.debug(f"Auth serializer validation successful for data: {validated_data}")

            # Get user data from google
            try:
                user_data: GoogleUserData = google_get_user_data(validated_data)
                logger.info(f"Successfully retrieved Google user data for email: {user_data.email}")
            except Exception as e:
                logger.error(f"Failed to get Google user data: {str(e)}", exc_info=True)
                return Response({"detail": "Failed to authenticate with Google"}, status=status.HTTP_401_UNAUTHORIZED)

            # Creates user in DB if first time login
            try:
                user, created = User.objects.get_or_create(
                    email=user_data.email,
                    username=user_data.email,
                    defaults={
                        "first_name": user_data.given_name,
                        "last_name": user_data.family_name,
                    },
                )

                if created:
                    logger.info(f"New user created: {user.email} (ID: {user.pk})")
                else:
                    logger.info(f"Existing user login: {user.email} (ID: {user.pk})")
                    # Update user data from Google
                    user.first_name = user_data.given_name
                    user.last_name = user_data.family_name
                    user.save()
                    logger.debug(f"Updated user profile data for: {user.email}")

            except Exception as e:
                logger.error(f"Failed to create/update user {user_data.email}: {str(e)}", exc_info=True)
                return Response(
                    {"detail": "Failed to create user account"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            # Check if user is already registered as a provider or person
            provider_id = None
            person_id = None
            social_name = None
            use_dark_mode = False
            profile_picture = user_data.picture
            role = "none"

            try:
                # Check if user is already registered as a provider
                if Provider.objects.filter(user=user).exists():
                    provider = Provider.objects.get(user=user)
                    social_name = getattr(provider, "social_name", None)
                    use_dark_mode = provider.use_dark_mode
                    if profile_picture:
                        provider.profile_picture = profile_picture
                        provider.save(update_fields=["profile_picture"])
                        logger.debug(f"Updated provider profile picture for: {user.email}")
                    provider_id = provider.provider_id
                    role = "provider"
                    logger.info(f"User {user.email} authenticated as provider: {provider_id}")

                # Check if user is already registered as a person
                elif Person.objects.filter(user=user).exists():
                    person = Person.objects.get(user=user)
                    social_name = getattr(person, "social_name", None)
                    use_dark_mode = person.use_dark_mode
                    if profile_picture:
                        person.profile_picture = profile_picture
                        person.save(update_fields=["profile_picture"])
                        logger.debug(f"Updated person profile picture for: {user.email}")
                    person_id = person.person_id
                    role = "person"
                    logger.info(f"User {user.email} authenticated as person: {person_id}")
                else:
                    logger.info(f"User {user.email} has no specific role assigned")

            except Exception as e:
                logger.error(f"Error checking user role for {user.email}: {str(e)}", exc_info=True)
                # Continue without role information rather than failing

            # Generate jwt token for the user
            try:
                token = RefreshToken.for_user(user)
                logger.info(f"JWT tokens generated successfully for user: {user.email}")
            except Exception as e:
                logger.error(f"Failed to generate JWT tokens for user {user.email}: {str(e)}", exc_info=True)
                return Response(
                    {"detail": "Failed to generate authentication tokens"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            # Name could be in social_name or associated user
            name = social_name
            if not name and user:
                name = f"{user.first_name} {user.last_name}".strip()
                if not name:
                    name = user.username

            response = {
                "access": str(token.access_token),
                "refresh": str(token),
                "provider_id": provider_id,
                "person_id": person_id,
                "role": role,
                "user_id": user.pk,
                "full_name": name,
                "email": user_data.email,
                "social_name": social_name,
                "profile_picture": profile_picture,
                "use_dark_mode": use_dark_mode,
            }

            logger.info(f"Google login successful for user: {user.email}, role: {role}")
            return Response(response, status=200)

        except Exception as e:
            logger.error(f"Unexpected error in Google login: {str(e)}", exc_info=True)
            return Response({"detail": "An unexpected error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminLoginView(APIView):
    """
    Admin Authentication Endpoints

    Provides two authentication methods for administrators:
    1. GET: Admin impersonation - Admin authenticates and gets token for another user
    2. POST: Direct admin login - Admin gets token for themselves
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Admin User Impersonation",
        description="""
        Allows administrators to obtain JWT tokens for any user in the system.
        
        **Use Cases:**
        - Customer support requiring access to user accounts
        - Testing user-specific features
        - Administrative operations on behalf of users
        
        **Security Requirements:**
        - Requires valid admin credentials (username + password)
        - Admin user must have `is_staff = True`
        - Target user must exist in the system
        
        **Process:**
        1. Admin provides their own username and password
        2. Admin specifies target user's email
        3. System validates admin credentials
        4. System returns JWT tokens for the target user
        
        **Important:** This endpoint should be used carefully and logged for security auditing.
        """,
        parameters=[
            OpenApiParameter(
                "email",
                OpenApiTypes.STR,
                description="Email of the target user to impersonate",
                required=True,
                examples=[OpenApiExample(name="User email", value="usuario@exemplo.com")],
            ),
            OpenApiParameter(
                "username",
                OpenApiTypes.STR,
                description="Admin username for authentication",
                required=True,
                examples=[OpenApiExample(name="Admin username", value="admin_user")],
            ),
            OpenApiParameter(
                "password",
                OpenApiTypes.STR,
                description="Admin password for authentication",
                required=True,
                examples=[OpenApiExample(name="Admin password", value="secure_password_123")],
            ),
        ],
        responses={
            200: {
                "description": "Successful impersonation",
            },
            400: {
                "description": "Missing email parameter",
            },
            401: {
                "description": "Invalid admin credentials",
            },
            404: {
                "description": "Target user not found",
            },
        },
        tags=["Admin Authentication"],
    )
    def get(self, request):
        try:
            logger.info(f"Admin impersonation attempt from IP: {request.META.get('REMOTE_ADDR')}")

            email = request.query_params.get("email")
            username = request.query_params.get("username")
            password = request.query_params.get("password")

            # Log admin authentication attempt
            logger.info(f"Admin impersonation attempt by username: {username} for target email: {email}")

            # Authenticate the user using admin credentials
            try:
                admin_user = authenticate(username=username, password=password)
            except Exception as e:
                logger.error(f"Authentication error for admin {username}: {str(e)}", exc_info=True)
                return Response(
                    {"detail": "Authentication service error."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            if not admin_user:
                logger.warning(f"Failed admin authentication attempt for username: {username}")
                return Response(
                    {"detail": "Invalid credentials or insufficient permissions."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            if not admin_user.is_staff:
                logger.warning(f"Non-staff user {username} attempted admin impersonation")
                return Response(
                    {"detail": "Invalid credentials or insufficient permissions."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            logger.info(f"Admin {username} successfully authenticated for impersonation")

            if not email:
                logger.warning(f"Admin {username} attempted impersonation without target email")
                return Response(
                    {"detail": "Email is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Find target user
            try:
                user = User.objects.filter(email=email).first()
            except Exception as e:
                logger.error(f"Database error while searching for user {email}: {str(e)}", exc_info=True)
                return Response(
                    {"detail": "Database error occurred."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            if not user:
                logger.warning(f"Admin {username} attempted to impersonate non-existent user: {email}")
                return Response(
                    {"detail": "User with this email does not exist."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Generate tokens for target user
            try:
                refresh = RefreshToken.for_user(user)
                logger.info(f"Admin {username} successfully impersonated user: {email} (ID: {user.id})")
            except Exception as e:
                logger.error(f"Failed to generate tokens for impersonated user {email}: {str(e)}", exc_info=True)
                return Response(
                    {"detail": "Failed to generate authentication tokens."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            # Get user role information
            person_id = None
            provider_id = None

            try:
                if hasattr(user, "person"):
                    person_id = getattr(user.person, "person_id", None)
                if hasattr(user, "provider"):
                    provider_id = getattr(user.provider, "provider_id", None)
            except Exception as e:
                logger.warning(f"Error getting role info for impersonated user {email}: {str(e)}")
                # Continue without role info

            return Response(
                {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                    "user_id": user.id,
                    "username": user.username,
                    "person_id": person_id,
                    "provider_id": provider_id,
                }
            )

        except Exception as e:
            logger.error(f"Unexpected error in admin impersonation: {str(e)}", exc_info=True)
            return Response(
                {"detail": "An unexpected error occurred"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        summary="Direct Admin Login",
        description="""
        Direct authentication endpoint for administrators.
        
        **Purpose:**
        - Allows admin users to log into their own accounts
        - Returns JWT tokens for the admin user themselves
        - Used for admin panel access and administrative operations
        
        **Requirements:**
        - Valid admin username and password
        - Admin user must have `is_staff = True`
        
        **Response:**
        Returns JWT tokens and basic admin user information.
        """,
        request=AdminLoginSerializer,
        responses={
            200: {
                "description": "Successful admin login",
            },
            401: {
                "description": "Invalid credentials",
            },
            403: {
                "description": "Insufficient permissions",
            },
        },
        tags=["Admin Authentication"],
    )
    def post(self, request, *args, **kwargs):
        try:
            logger.info(f"Direct admin login attempt from IP: {request.META.get('REMOTE_ADDR')}")

            username = request.data.get("username")
            password = request.data.get("password")

            logger.info(f"Direct admin login attempt for username: {username}")

            try:
                user = authenticate(username=username, password=password)
            except Exception as e:
                logger.error(f"Authentication error for admin {username}: {str(e)}", exc_info=True)
                return Response(
                    {"detail": "Authentication service error."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            if not user:
                logger.warning(f"Failed direct admin login for username: {username}")
                return Response(
                    {"detail": "Invalid credentials."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            if not user.is_staff:
                logger.warning(f"Non-staff user {username} attempted direct admin login")
                return Response(
                    {"detail": "You do not have permission to access this endpoint."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            try:
                refresh = RefreshToken.for_user(user)
                logger.info(f"Direct admin login successful for: {username} (ID: {user.id})")
            except Exception as e:
                logger.error(f"Failed to generate tokens for admin {username}: {str(e)}", exc_info=True)
                return Response(
                    {"detail": "Failed to generate authentication tokens."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            return Response(
                {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                    "user_id": user.id,
                    "username": user.username,
                }
            )

        except Exception as e:
            logger.error(f"Unexpected error in direct admin login: {str(e)}", exc_info=True)
            return Response(
                {"detail": "An unexpected error occurred"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@extend_schema(
    summary="User Logout",
    description="""
    Logs out the authenticated user by blacklisting their refresh token.
    
    **Process:**
    1. Client sends refresh token to be invalidated
    2. Server blacklists the token (if blacklisting is enabled)
    3. Server returns success confirmation
    
    **Security Notes:**
    - Blacklisted tokens cannot be used to generate new access tokens
    - Access tokens remain valid until they expire naturally
    - For complete security, clients should also clear stored tokens
    
    **Token Blacklisting:**
    This endpoint requires django-rest-framework-simplejwt token blacklisting to be enabled.
    If not enabled, returns 501 Not Implemented.
    """,
    request=LogoutSerializer,
    responses={
        205: {
            "description": "Logout successful - Reset Content",
        },
        400: {
            "description": "Invalid token or token already blacklisted",
        },
        401: {
            "description": "Authentication required",
        },
        501: {
            "description": "Token blacklisting not enabled",
        },
    },
    tags=["Authentication"],
)
class LogoutView(APIView):
    """
    User Logout Endpoint

    Safely logs out authenticated users by blacklisting their refresh tokens.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            user_id = getattr(request.user, "id", "Unknown")
            logger.info(f"Logout attempt for user ID: {user_id}")

            refresh_token = request.data.get("refresh")

            if not refresh_token:
                logger.warning(f"Logout attempt without refresh token for user ID: {user_id}")
                return Response({"detail": "Refresh token is required."}, status=status.HTTP_400_BAD_REQUEST)

            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
                logger.info(f"Logout successful for user ID: {user_id}")
                return Response({"detail": "Logout successful."}, status=status.HTTP_205_RESET_CONTENT)
            except AttributeError as e:
                logger.error(f"Token blacklisting not enabled - logout failed for user ID: {user_id}: {str(e)}")
                return Response({"detail": "Token blacklisting not enabled."}, status=status.HTTP_501_NOT_IMPLEMENTED)
            except Exception as e:
                logger.warning(f"Invalid or already blacklisted token for user ID: {user_id}: {str(e)}")
                return Response(
                    {"detail": "Invalid token or token already blacklisted."}, status=status.HTTP_400_BAD_REQUEST
                )

        except Exception as e:
            logger.error(f"Unexpected error during logout: {str(e)}", exc_info=True)
            return Response(
                {"detail": "An unexpected error occurred during logout"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@extend_schema(
    tags=["Development Tools"],
    summary="Development Login as Provider",
    description="""
    **🚨 DEVELOPMENT ONLY - NOT AVAILABLE IN PRODUCTION 🚨**
    
    Quick authentication endpoint for development and testing purposes.
    
    **Development Purpose:**
    - Rapid testing of Provider-specific features
    - UI/UX development without manual login
    - Integration testing and debugging
    - Demo and presentation purposes
    
    **Security Notice:**
    - Only works when DEBUG=True in Django settings
    - Returns 403 Forbidden in production environments
    - Uses hardcoded mock provider account
    - Should never be deployed to production
    
    **Mock Account Details:**
    - Email: mock-provider@email.com
    - Role: Provider
    - Has complete provider profile for testing
    
    **Returns:**
    - JWT access token (short-lived)
    - JWT refresh token (for token renewal)
    - Same token format as production login endpoints
    """,
    responses={
        200: {"description": "Development login successful"},
        403: {"description": "Not available in production"},
    },
)
@api_view(["POST"])
@permission_classes([AllowAny])
def dev_login_as_provider(request):
    """
    Development-only quick login as Provider.
    """
    if not settings.DEBUG:
        logger.warning(
            "Development provider login attempted in production environment",
            extra={
                "ip_address": request.META.get("REMOTE_ADDR", "Unknown"),
                "user_agent": request.META.get("HTTP_USER_AGENT", "Unknown"),
                "action": "dev_login_provider_production_attempt",
            },
        )
        return Response({"detail": "Not available in production"}, status=status.HTTP_403_FORBIDDEN)

    try:
        User = get_user_model()
        user = User.objects.get(email="mock-provider@email.com")
        refresh = RefreshToken.for_user(user)

        logger.info(
            "Development provider login successful",
            extra={
                "user_id": user.id,
                "email": user.email,
                "ip_address": request.META.get("REMOTE_ADDR", "Unknown"),
                "action": "dev_login_provider_success",
            },
        )

        return Response(
            {"access": str(refresh.access_token), "refresh": str(refresh), "user_id": user.id, "email": user.email}
        )

    except User.DoesNotExist:
        logger.error(
            "Development provider login failed - mock user not found",
            extra={"email": "mock-provider@email.com", "action": "dev_login_provider_user_not_found"},
        )
        return Response(
            {"error": "Mock provider account not found. Please run development fixtures."},
            status=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:
        logger.error(
            "Development provider login error",
            extra={"error": str(e), "error_type": type(e).__name__, "action": "dev_login_provider_error"},
            exc_info=True,
        )
        return Response({"error": "Development login failed."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    tags=["Development Tools"],
    summary="Development Login as Person",
    description="""
    **🚨 DEVELOPMENT ONLY - NOT AVAILABLE IN PRODUCTION 🚨**
    
    Quick authentication endpoint for development and testing purposes.
    
    **Development Purpose:**
    - Rapid testing of Person-specific features
    - UI/UX development without manual login
    - Integration testing and debugging
    - Demo and presentation purposes
    
    **Security Notice:**
    - Only works when DEBUG=True in Django settings
    - Returns 403 Forbidden in production environments
    - Uses hardcoded mock person account
    - Should never be deployed to production
    
    **Mock Account Details:**
    - Email: mock-person@email.com
    - Role: Person
    - Has complete person profile for testing
    
    **Returns:**
    - JWT access token (short-lived)
    - JWT refresh token (for token renewal)
    - Same token format as production login endpoints
    """,
    responses={
        200: {"description": "Development login successful"},
        403: {"description": "Not available in production"},
    },
)
@api_view(["POST"])
@permission_classes([AllowAny])
def dev_login_as_person(request):
    """
    Development-only quick login as Person.
    """
    if not settings.DEBUG:
        logger.warning(
            "Development person login attempted in production environment",
            extra={
                "ip_address": request.META.get("REMOTE_ADDR", "Unknown"),
                "user_agent": request.META.get("HTTP_USER_AGENT", "Unknown"),
                "action": "dev_login_person_production_attempt",
            },
        )
        return Response({"detail": "Not available in production"}, status=status.HTTP_403_FORBIDDEN)

    try:
        User = get_user_model()
        user = User.objects.get(email="mock-person@email.com")
        refresh = RefreshToken.for_user(user)

        logger.info(
            "Development person login successful",
            extra={
                "user_id": user.id,
                "email": user.email,
                "ip_address": request.META.get("REMOTE_ADDR", "Unknown"),
                "action": "dev_login_person_success",
            },
        )

        return Response(
            {"access": str(refresh.access_token), "refresh": str(refresh), "user_id": user.id, "email": user.email}
        )

    except User.DoesNotExist:
        logger.error(
            "Development person login failed - mock user not found",
            extra={"email": "mock-person@email.com", "action": "dev_login_person_user_not_found"},
        )
        return Response(
            {"error": "Mock person account not found. Please run development fixtures."},
            status=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:
        logger.error(
            "Development person login error",
            extra={"error": str(e), "error_type": type(e).__name__, "action": "dev_login_person_error"},
            exc_info=True,
        )
        return Response({"error": "Development login failed."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
