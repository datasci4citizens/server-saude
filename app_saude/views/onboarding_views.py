import json
import logging

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.http import Http404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from ..models import *
from ..serializers import *
from ..utils.provider import *
from .commons import FlexibleViewSet

User = get_user_model()
logger = logging.getLogger("app_saude")


def validate_user_has_no_existing_profiles(user, requested_profile_type="unknown"):
    """
    Valida que o usuário não possui nenhum perfil existente (Person ou Provider).
    Evita conflitos de múltiplos perfis para o mesmo usuário.

    Args:
        user: O usuário a ser validado
        requested_profile_type: Tipo de perfil sendo solicitado ("person" ou "provider")

    Raises:
        Http404: Se o usuário já possui algum perfil
    """
    existing_person = Person.objects.filter(user=user).first()
    existing_provider = Provider.objects.filter(user=user).first()

    if existing_person:
        logger.warning(
            f"Onboarding bloqueado - usuário já possui perfil de Person",
            extra={
                "user_id": user.id,
                "email": user.email,
                "existing_person_id": existing_person.person_id,
                "existing_social_name": existing_person.social_name,
                "requested_profile_type": requested_profile_type,
                "action": "onboarding_blocked_existing_person_profile",
            },
        )
        raise Http404("Você já possui um perfil de paciente no sistema.")

    if existing_provider:
        logger.warning(
            f"Onboarding bloqueado - usuário já possui perfil de Provider",
            extra={
                "user_id": user.id,
                "email": user.email,
                "existing_provider_id": existing_provider.provider_id,
                "existing_social_name": existing_provider.social_name,
                "existing_professional_reg": getattr(existing_provider, "professional_registration", None),
                "requested_profile_type": requested_profile_type,
                "action": "onboarding_blocked_existing_provider_profile",
            },
        )
        raise Http404("Você já possui um perfil de profissional no sistema.")


def validate_person_onboarding_authorization(user):
    """
    Valida se o usuário tem autorização para fazer onboarding como Person.

    Args:
        user: O usuário autenticado

    Raises:
        Http404: Se não autorizado
    """
    if not user.is_authenticated:
        logger.warning(
            "Tentativa de onboarding Person sem autenticação",
            extra={
                "user_authenticated": user.is_authenticated,
                "action": "person_onboarding_no_auth",
            },
        )
        raise Http404("Autenticação necessária para criar perfil de paciente.")

    # Verificar se não possui nenhum perfil existente
    validate_user_has_no_existing_profiles(user, "person")


def validate_provider_registration_data(email, professional_registration):
    """
    Valida dados de registro de Provider para evitar duplicatas.

    Args:
        email: Email do provider
        professional_registration: Registro profissional

    Raises:
        Http404: Se dados duplicados encontrados
    """
    # Verificar email duplicado
    if User.objects.filter(email=email).exists():
        logger.warning(
            "Registro Provider bloqueado - email já existe",
            extra={
                "email": email,
                "action": "provider_registration_email_duplicate",
            },
        )
        raise Http404("Já existe uma conta com este email.")

    # Verificar registro profissional duplicado
    if (
        professional_registration
        and Provider.objects.filter(professional_registration=professional_registration).exists()
    ):
        logger.warning(
            "Registro Provider bloqueado - registro profissional já existe",
            extra={
                "professional_registration": professional_registration,
                "email": email,
                "action": "provider_registration_prof_reg_duplicate",
            },
        )
        raise Http404("Já existe um profissional com este registro.")


def validate_user_registration_limits(email):
    """
    Valida limites de registro por usuário para prevenir spam/abuso.

    Args:
        email: Email sendo registrado
    """
    # Verificar se o domínio do email não está na blacklist (se implementado)
    email_domain = email.split("@")[1].lower() if "@" in email else ""

    # Lista de domínios temporários/suspeitos (exemplo)
    suspicious_domains = ["10minutemail.com", "tempmail.org", "guerrillamail.com", "mailinator.com", "throwaway.email"]

    if email_domain in suspicious_domains:
        logger.warning(
            "Registro bloqueado - domínio de email suspeito",
            extra={
                "email": email,
                "email_domain": email_domain,
                "action": "registration_blocked_suspicious_domain",
            },
        )
        raise Http404("Este domínio de email não é permitido para registro.")


@extend_schema(
    tags=["Complete Onboarding"],
    summary="Complete Person Onboarding",
    description="""
    Completa o processo de onboarding para perfis de Person com todas as informações necessárias.
    
    **RESTRIÇÕES DE SEGURANÇA:**
    - **Autenticação Obrigatória**: Usuário deve estar autenticado
    - **Perfil Único**: Usuário não pode ter perfil existente (Person ou Provider)
    - **Validação Completa**: Todos os dados são validados antes da criação
    
    **Recursos Abrangentes de Onboarding:**
    - Cria perfil completo de Person em uma única requisição
    - Valida todas as informações pessoais necessárias
    - Configura preferências e configurações iniciais
    - Vincula à conta de usuário autenticada
    - Realiza validação completa de dados e verificações de consistência
    
    **Regras de Negócio:**
    - Usuário deve estar autenticado
    - Usuário não pode já ter um perfil de Person
    - Usuário não pode já ter um perfil de Provider
    - Todos os campos obrigatórios devem ser fornecidos
    - Validação de idade e consistência de data de nascimento
    - Nome social deve ser único no sistema
    """,
    request=FullPersonCreateSerializer,
    responses={
        201: {"description": "Onboarding de Person completado com sucesso"},
        400: {"description": "Erro de validação ou registro duplicado"},
        401: {"description": "Autenticação necessária"},
        404: {"description": "Acesso negado ou perfil já existe"},
    },
)
class FullPersonViewSet(FlexibleViewSet):
    """
    Onboarding Completo de Person

    Lida com criação abrangente de perfil de Person com validação completa
    e verificações de consistência de dados em uma única operação atômica.
    """

    http_method_names = ["post"]  # only allow POST
    queryset = Person.objects.none()  # prevents GET from returning anything
    permission_classes = [IsAuthenticated]

    def create(self, request):
        user = request.user
        ip_address = request.META.get("REMOTE_ADDR", "Unknown")
        user_agent = request.META.get("HTTP_USER_AGENT", "Unknown")

        # VALIDAÇÃO DE SEGURANÇA: Verificar autorização para onboarding Person
        try:
            validate_person_onboarding_authorization(user)
        except Http404 as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

        logger.info(
            "Full person onboarding initiated",
            extra={
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "request_data_size": len(str(request.data)),
                "request_fields": list(request.data.keys()) if request.data else [],
                "action": "full_person_onboarding_start",
            },
        )

        serializer: FullPersonCreateSerializer = self.get_serializer(data=request.data, context={"request": request})

        try:
            # Validação adicional de dados sensíveis
            social_name = request.data.get("social_name", "").strip()
            if not social_name:
                logger.warning(
                    "Person onboarding failed - nome social obrigatório",
                    extra={
                        "user_id": user.id,
                        "ip_address": ip_address,
                        "action": "person_onboarding_no_social_name",
                    },
                )
                return Response({"error": "Nome social é obrigatório."}, status=status.HTTP_400_BAD_REQUEST)

            # Verificar se nome social já existe
            if Person.objects.filter(social_name=social_name).exists():
                logger.warning(
                    "Person onboarding failed - nome social já existe",
                    extra={
                        "user_id": user.id,
                        "social_name": social_name,
                        "ip_address": ip_address,
                        "action": "person_onboarding_social_name_exists",
                    },
                )
                return Response({"error": "Este nome social já está em uso."}, status=status.HTTP_400_BAD_REQUEST)

            # Validate serializer data
            if not serializer.is_valid():
                validation_errors = serializer.errors
                logger.warning(
                    "Full person onboarding validation failed",
                    extra={
                        "user_id": user.id,
                        "validation_errors": json.dumps(validation_errors, ensure_ascii=False),
                        "request_data_keys": list(request.data.keys()),
                        "ip_address": ip_address,
                        "action": "full_person_onboarding_validation_failed",
                    },
                )
                return Response(
                    {"error": "Validation failed", "details": validation_errors}, status=status.HTTP_400_BAD_REQUEST
                )

            logger.debug(
                "Full person onboarding data validated successfully",
                extra={
                    "user_id": user.id,
                    "data_fields": list(request.data.keys()),
                    "social_name": social_name,
                    "age": request.data.get("age"),
                    "action": "full_person_onboarding_validated",
                },
            )

            # Create person with atomic transaction
            with transaction.atomic():
                logger.debug(
                    "Starting atomic transaction for person creation",
                    extra={"user_id": user.id, "action": "full_person_onboarding_transaction_start"},
                )

                # Validação final antes da criação
                validate_user_has_no_existing_profiles(user, "person")

                serializer.create(request.data)

                # Get the created person for detailed logging
                created_person = Person.objects.get(user=user)
                logger.info(
                    "Full person onboarding completed successfully",
                    extra={
                        "user_id": user.id,
                        "person_id": created_person.person_id,
                        "social_name": created_person.social_name,
                        "age": getattr(created_person, "age", None),
                        "birth_datetime": (
                            created_person.birth_datetime.isoformat()
                            if hasattr(created_person, "birth_datetime") and created_person.birth_datetime
                            else None
                        ),
                        "use_dark_mode": getattr(created_person, "use_dark_mode", False),
                        "ip_address": ip_address,
                        "action": "full_person_onboarding_success",
                    },
                )

                return Response(
                    {"message": "Onboarding completed successfully", "person_id": created_person.person_id},
                    status=status.HTTP_201_CREATED,
                )

        except Http404 as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except ValidationError as ve:
            logger.warning(
                "Full person onboarding validation failed with ValidationError",
                extra={
                    "user_id": user.id,
                    "validation_errors": str(ve),
                    "request_data_keys": list(request.data.keys()),
                    "ip_address": ip_address,
                    "action": "full_person_onboarding_validation_error",
                },
            )
            return Response({"error": str(ve)}, status=status.HTTP_400_BAD_REQUEST)
        except IntegrityError as ie:
            logger.error(
                "Integrity error during person onboarding",
                extra={
                    "user_id": user.id,
                    "error": str(ie),
                    "social_name": request.data.get("social_name"),
                    "ip_address": ip_address,
                    "action": "full_person_onboarding_integrity_error",
                },
                exc_info=True,
            )
            return Response(
                {"error": "Os dados fornecidos conflitam com registros existentes."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error(
                "Critical error during full person onboarding",
                extra={
                    "user_id": user.id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "request_data": request.data,
                    "ip_address": ip_address,
                    "action": "full_person_onboarding_critical_error",
                },
                exc_info=True,
            )
            return Response(
                {"error": "An unexpected error occurred during onboarding"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@extend_schema(
    tags=["Complete Onboarding"],
    summary="Complete Provider Registration",
    description="""
    Processo de registro completo para perfis de Provider com criação de conta de usuário.
    
    **RESTRIÇÕES DE SEGURANÇA:**
    - **Email Único**: Email deve ser único no sistema
    - **Registro Profissional Único**: Registro profissional deve ser único
    - **Validação de Domínio**: Domínios de email suspeitos são bloqueados
    - **Transação Atômica**: Criação de User e Provider em transação única
    
    **Recursos Abrangentes de Registro:**
    - Cria tanto conta de User quanto perfil de Provider
    - Valida credenciais profissionais
    - Configura informações completas do provider
    - Lida com ativação de conta e permissões
    - Transação atômica garante consistência de dados
    
    **Processo de Criação de Conta:**
    1. **Validação de Usuário**: Validação de unicidade e formato de email
    2. **Validação Profissional**: Verificação de número de registro
    3. **Criação de Perfil**: Configuração completa do perfil do provider
    4. **Ativação de Conta**: Configuração da conta do usuário com permissões adequadas
    5. **Configuração de Relacionamento**: Vincula usuário ao perfil do provider
    """,
    request=FullProviderCreateSerializer,
    responses={
        201: {"description": "Registro de Provider completado com sucesso"},
        400: {"description": "Erro de validação ou registro duplicado"},
        404: {"description": "Dados duplicados ou domínio não permitido"},
        500: {"description": "Erro do servidor durante registro"},
    },
)
class FullProviderViewSet(FlexibleViewSet):
    """
    Registro Completo de Provider

    Lida com registro abrangente de Provider incluindo criação de conta de usuário
    e configuração completa de perfil profissional em transações atômicas.
    """

    http_method_names = ["post"]
    queryset = Provider.objects.none()
    permission_classes = [AllowAny]

    def create(self, request):
        ip_address = request.META.get("REMOTE_ADDR", "Unknown")
        user_agent = request.META.get("HTTP_USER_AGENT", "Unknown")
        email = request.data.get("email", "").strip().lower()
        professional_registration = request.data.get("professional_registration", "").strip()
        social_name = request.data.get("social_name", "").strip()

        logger.info(
            "Full provider registration initiated",
            extra={
                "ip_address": ip_address,
                "user_agent": user_agent,
                "email": email,
                "professional_registration": professional_registration,
                "social_name": social_name,
                "specialty": request.data.get("specialty"),
                "request_data_size": len(str(request.data)),
                "request_fields": list(request.data.keys()) if request.data else [],
                "action": "full_provider_registration_start",
            },
        )

        # VALIDAÇÕES DE SEGURANÇA PRELIMINARES
        try:
            # Validar email e registro profissional
            if not email:
                return Response({"error": "Email é obrigatório."}, status=status.HTTP_400_BAD_REQUEST)

            # Validar limites e restrições de registro
            validate_user_registration_limits(email)

            # Validar dados de registro
            validate_provider_registration_data(email, professional_registration)

        except Http404 as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

        # Validações adicionais
        if not social_name:
            logger.warning(
                "Provider registration failed - nome social obrigatório",
                extra={
                    "email": email,
                    "ip_address": ip_address,
                    "action": "provider_registration_no_social_name",
                },
            )
            return Response({"error": "Nome social é obrigatório."}, status=status.HTTP_400_BAD_REQUEST)

        # Verificar se nome social já existe para providers
        if Provider.objects.filter(social_name=social_name).exists():
            logger.warning(
                "Provider registration failed - nome social já existe",
                extra={
                    "email": email,
                    "social_name": social_name,
                    "ip_address": ip_address,
                    "action": "provider_registration_social_name_exists",
                },
            )
            return Response(
                {"error": "Este nome social já está em uso por outro profissional."}, status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(data=request.data, context={"request": request})

        # Validate the data with detailed error logging
        if not serializer.is_valid():
            errors = serializer.errors
            logger.warning(
                "Full provider registration validation failed",
                extra={
                    "validation_errors": json.dumps(errors, ensure_ascii=False),
                    "email": email,
                    "professional_registration": professional_registration,
                    "request_data_keys": list(request.data.keys()),
                    "ip_address": ip_address,
                    "action": "full_provider_registration_validation_failed",
                },
            )
            return Response(
                {
                    "message": "Validation failed",
                    "errors": errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            try:
                logger.debug(
                    "Starting atomic transaction for provider creation",
                    extra={
                        "email": email,
                        "professional_registration": professional_registration,
                        "social_name": social_name,
                        "action": "full_provider_registration_transaction_start",
                    },
                )

                # Validações finais dentro da transação
                validate_provider_registration_data(email, professional_registration)

                result = serializer.save()
                response_data = ProviderRetrieveSerializer(result["provider"]).data

                # Log successful creation with comprehensive details
                provider = result["provider"]
                user = result.get("user")

                logger.info(
                    "Full provider registration completed successfully",
                    extra={
                        "provider_id": provider.provider_id,
                        "user_id": user.id if user else None,
                        "social_name": provider.social_name,
                        "professional_registration": getattr(provider, "professional_registration", None),
                        "specialty": getattr(provider, "specialty", None),
                        "email": user.email if user else None,
                        "use_dark_mode": getattr(provider, "use_dark_mode", False),
                        "is_active": user.is_active if user else None,
                        "ip_address": ip_address,
                        "action": "full_provider_registration_success",
                    },
                )

                return Response(
                    {
                        "message": "Provider created successfully",
                        "data": response_data,
                        "provider_id": provider.provider_id,
                    },
                    status=status.HTTP_201_CREATED,
                )

            except Http404 as e:
                transaction.set_rollback(True)
                logger.error(
                    "Provider registration blocked - validation failed within transaction",
                    extra={
                        "error": str(e),
                        "email": email,
                        "professional_registration": professional_registration,
                        "ip_address": ip_address,
                        "action": "full_provider_registration_blocked",
                    },
                )
                return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
            except IntegrityError as ie:
                transaction.set_rollback(True)
                logger.error(
                    "Database integrity error during provider creation - transaction rolled back",
                    extra={
                        "error": str(ie),
                        "email": email,
                        "professional_registration": professional_registration,
                        "social_name": social_name,
                        "ip_address": ip_address,
                        "action": "full_provider_registration_integrity_error",
                    },
                    exc_info=True,
                )
                return Response(
                    {"error": "Registration data conflicts with existing records."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            except Exception as e:
                transaction.set_rollback(True)
                logger.error(
                    "Critical error during provider creation - transaction rolled back",
                    extra={
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "email": email,
                        "professional_registration": professional_registration,
                        "request_data": request.data,
                        "ip_address": ip_address,
                        "action": "full_provider_registration_critical_error",
                    },
                    exc_info=True,
                )
                return Response(
                    {"error": "Internal server error occurred during registration."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
