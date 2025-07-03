import logging
import uuid
from datetime import timedelta

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
from ..utils.person import *
from ..utils.provider import *

User = get_user_model()
logger = logging.getLogger("app_saude")


def validate_unlink_authorization(user, person_id, provider_id):
    """
    Valida se o usuário tem autorização para fazer unlink.
    Regras:
    - Person só pode unlinkar a si mesmo
    - Provider só pode unlinkar pessoas vinculadas a ele
    """
    # Verifica se usuário é Person
    try:
        person = Person.objects.get(user=user)
        # Person só pode unlinkar a si mesmo
        if person.person_id != person_id:
            logger.warning(
                "Tentativa de unlink não autorizada - person tentando unlinkar outro person",
                extra={
                    "user_id": user.id,
                    "user_person_id": person.person_id,
                    "target_person_id": person_id,
                    "action": "unauthorized_unlink_attempt_person",
                },
            )
            raise Http404("Você só pode remover seus próprios vínculos.")
        return person, None
    except Person.DoesNotExist:
        pass

    # Verifica se usuário é Provider
    try:
        provider = Provider.objects.get(user=user)
        # Provider só pode unlinkar pessoas vinculadas a ele
        if provider.provider_id != provider_id:
            logger.warning(
                "Tentativa de unlink não autorizada - provider tentando unlinkar de outro provider",
                extra={
                    "user_id": user.id,
                    "user_provider_id": provider.provider_id,
                    "target_provider_id": provider_id,
                    "action": "unauthorized_unlink_attempt_provider",
                },
            )
            raise Http404("Você só pode remover vínculos de seus próprios pacientes.")

        # Verifica se a pessoa está realmente vinculada a este provider
        _, linked_persons_ids = get_provider_and_linked_persons(user)
        if person_id not in linked_persons_ids:
            logger.warning(
                "Tentativa de unlink não autorizada - pessoa não vinculada",
                extra={
                    "user_id": user.id,
                    "provider_id": provider.provider_id,
                    "person_id": person_id,
                    "action": "unauthorized_unlink_person_not_linked",
                },
            )
            raise Http404("Esta pessoa não está vinculada a você.")

        return None, provider
    except Provider.DoesNotExist:
        pass

    # Se chegou aqui, o usuário não é nem Person nem Provider
    logger.warning(
        "Tentativa de unlink não autorizada - usuário sem perfil",
        extra={
            "user_id": user.id,
            "email": user.email,
            "action": "unauthorized_unlink_no_profile",
        },
    )
    raise Http404("Acesso negado. Você precisa ter um perfil de paciente ou profissional.")


@extend_schema(
    tags=["Person-Provider Linking"],
    summary="Generate Provider Link Code",
    description="""
    Gera um código temporário de 6 dígitos para vinculação Person-Provider.
    
    **RESTRIÇÃO DE ACESSO:** Apenas usuários com perfil de Provider podem usar esta funcionalidade.
    
    **Sistema de Código de Vinculação:**
    - **Propósito**: Método seguro para Persons se conectarem com Providers
    - **Formato**: Código alfanumérico de 6 caracteres (ex: 'A1B2C3')
    - **Expiração**: Válido por 10 minutos a partir da geração
    - **Uso**: Código de uso único que expira após Person vincular
    
    **Recursos de Segurança:**
    - **Limitado por Tempo**: Códigos expiram automaticamente após 10 minutos
    - **Uso Único**: Código se torna inválido após vinculação bem-sucedida
    - **Específico do Provider**: Cada código é vinculado a um Provider específico
    - **Trilha de Auditoria**: Toda geração e uso de código é registrado
    """,
    responses={
        200: LinkingCodeSerializer,
        401: {"description": "Authentication required"},
        404: {"description": "Provider profile not found or access denied"},
    },
)
class GenerateProviderLinkCodeView(APIView):
    """
    Geração de Código de Vinculação do Provider

    Gera códigos temporários seguros para sistema de vinculação Person-Provider.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        ip_address = request.META.get("REMOTE_ADDR", "Unknown")

        # VALIDAÇÃO DE SEGURANÇA: Só providers podem gerar códigos
        provider = validate_user_is_provider(user)

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

            serializer = LinkingCodeSerializer(data={"code": code, "expires_at": expiry_time, "expires_in_minutes": 10})

            if serializer.is_valid():
                return Response(serializer.validated_data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
    summary="Get Provider Information by Link Code",
    description="""
    Recupera informações do Provider usando um código de vinculação para preview antes da vinculação.
    
    **RESTRIÇÃO DE ACESSO:** Apenas usuários com perfil de Person podem usar esta funcionalidade.
    
    **Funcionalidade de Preview:**
    - Permite que Person visualize detalhes do Provider antes de estabelecer conexão
    - Valida código de vinculação sem consumi-lo
    - Retorna informações abrangentes do perfil do Provider
    - Permite tomada de decisão informada antes da vinculação
    """,
    request=PersonLinkProviderRequestSerializer,
    responses={
        200: ProviderRetrieveSerializer,
        400: {"description": "Invalid or expired code"},
        401: {"description": "Authentication required"},
        404: {"description": "Person profile not found or access denied"},
    },
)
class ProviderByLinkCodeView(APIView):
    """
    Busca de Informações do Provider

    Recupera detalhes do Provider usando códigos de vinculação para funcionalidade de preview.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        ip_address = request.META.get("REMOTE_ADDR", "Unknown")
        code = request.data.get("code")

        # VALIDAÇÃO DE SEGURANÇA: Só persons podem fazer preview de providers
        person = validate_user_is_person(user)

        logger.debug(
            "Provider lookup by link code requested",
            extra={
                "user_id": user.id,
                "person_id": person.person_id,
                "person_name": person.social_name,
                "code": code,
                "ip_address": ip_address,
                "action": "provider_lookup_by_code_requested",
            },
        )

        if not code:
            logger.warning(
                "Provider lookup failed - no code provided",
                extra={
                    "user_id": user.id,
                    "person_id": person.person_id,
                    "ip_address": ip_address,
                    "action": "provider_lookup_no_code",
                },
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
                        "person_id": person.person_id,
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
                    "person_id": person.person_id,
                    "person_name": person.social_name,
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
                    "person_id": person.person_id,
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
    summary="Link Person to Provider",
    description="""
    Estabelece uma conexão entre Person e Provider usando um código de vinculação.
    
    **RESTRIÇÃO DE ACESSO:** Apenas usuários com perfil de Person podem usar esta funcionalidade.
    
    **Processo de Vinculação:**
    1. **Validação de Código**: Verifica se código existe e não expirou
    2. **Busca de Provider**: Identifica Provider associado com código
    3. **Criação de Relacionamento**: Cria relacionamento Person-Provider
    4. **Invalidação de Código**: Marca código como usado para prevenir reuso
    5. **Log de Auditoria**: Registra todas as atividades de vinculação
    """,
    request=PersonLinkProviderRequestSerializer,
    responses={
        200: ProviderPersonLinkStatusSerializer,
        400: {"description": "Invalid or expired code"},
        401: {"description": "Authentication required"},
        404: {"description": "Person profile not found or access denied"},
    },
)
class PersonLinkProviderView(APIView):
    """
    Vinculação Person-Provider

    Lida com vinculação segura entre Persons e Providers usando códigos temporários.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        ip_address = request.META.get("REMOTE_ADDR", "Unknown")
        code = request.data.get("code")

        # VALIDAÇÃO DE SEGURANÇA: Só persons podem se vincular a providers
        person = validate_user_is_person(user)

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

            serializer = ProviderPersonLinkStatusSerializer(
                data={
                    "status": "linked",
                    "provider_id": provider.provider_id,
                    "provider_name": provider.social_name,
                    "relationship_created": created,
                }
            )

            if serializer.is_valid():
                return Response(serializer.validated_data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
    summary="Unlink Person from Provider",
    description="""
    Remove a conexão entre um Person e Provider.
    
    **⚠️ OPERAÇÃO CRÍTICA - AFETA RELACIONAMENTOS DE SERVIÇO ⚠️**
    
    **REGRAS DE AUTORIZAÇÃO:**
    - **Person**: Só pode desvincular a si mesmo de providers
    - **Provider**: Só pode desvincular persons que estão vinculados a ele
    - **Outros usuários**: Não têm autorização para fazer unlink
    
    **Processo de Desvinculação:**
    1. **Validação de Autorização**: Verifica se usuário pode fazer unlink
    2. **Validação de Relacionamento**: Confirma que relacionamento existe
    3. **Verificação de Dependência**: Garante remoção segura do relacionamento
    4. **Remoção de Relacionamento**: Deleta conexão Person-Provider
    5. **Log de Auditoria**: Registra todas as atividades de desvinculação com contexto completo
    """,
    request=PersonProviderUnlinkRequestSerializer,
    responses={
        200: {"description": "Person successfully unlinked from Provider"},
        400: {"description": "Invalid request or relationship doesn't exist"},
        401: {"description": "Authentication required"},
        404: {"description": "Person, Provider not found, or unauthorized access"},
    },
)
class PersonProviderUnlinkView(APIView):
    """
    Desvinculação Person-Provider

    Lida com remoção segura de relacionamentos Person-Provider com trilha de auditoria completa.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, person_id, provider_id):
        user = request.user
        ip_address = request.META.get("REMOTE_ADDR", "Unknown")
        user_agent = request.META.get("HTTP_USER_AGENT", "Unknown")

        # VALIDAÇÃO DE SEGURANÇA: Verificar autorização para fazer unlink
        person_user, provider_user = validate_unlink_authorization(user, person_id, provider_id)

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

        # Determinar tipo de usuário que está fazendo unlink
        user_type = "person" if person_user else "provider"

        logger.warning(
            "Person-Provider unlinking requested - CRITICAL ACTION",
            extra={
                "user_id": user.id,
                "user_type": user_type,
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
                        "user_type": user_type,
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
                    "user_type": user_type,
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
                        "user_type": user_type,
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

                serializer = ProviderPersonLinkStatusSerializer(
                    data={
                        "status": "unlinked",
                        "relationships_removed": deleted_count,
                        "person_id": person_id,
                        "provider_id": provider_id,
                    }
                )

                if serializer.is_valid():
                    return Response(serializer.validated_data, status=status.HTTP_200_OK)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(
                "Unexpected error during Person-Provider unlinking",
                extra={
                    "user_id": user.id,
                    "user_type": user_type,
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
    Recupera todos os Providers que estão atualmente vinculados ao Person autenticado.
    
    **RESTRIÇÃO DE ACESSO:** Apenas usuários com perfil de Person podem usar esta funcionalidade.
    
    **Consulta de Relacionamento:**
    - Retorna todos os relacionamentos ativos de Provider para o Person
    - Inclui informações completas do perfil do Provider
    - Ordenado por vinculação mais recente primeiro
    - Filtra perfis de Provider inativos ou deletados
    """,
    responses={
        200: ProviderRetrieveSerializer(many=True),
        401: {"description": "Authentication required"},
        404: {"description": "Person profile not found or access denied"},
    },
)
class PersonProvidersView(APIView):
    """
    Providers Vinculados do Person

    Recupera todos os providers atualmente vinculados ao person autenticado.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        ip_address = request.META.get("REMOTE_ADDR", "Unknown")

        # VALIDAÇÃO DE SEGURANÇA: Só persons podem ver seus providers
        person = validate_user_is_person(user)

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
    Recupera todos os Persons atualmente vinculados ao Provider autenticado com informações de resumo abrangentes.
    
    **RESTRIÇÃO DE ACESSO:** Apenas usuários com perfil de Provider podem usar esta funcionalidade.
    
    **Informações Ampliadas do Person:**
    - **Perfil Básico**: ID do Person, nome e detalhes de contato
    - **Cálculo de Idade**: Calculado automaticamente a partir da data de nascimento ou ano
    - **Data da Última Visita**: Consulta/visita mais recente com este provider
    - **Data da Última Ajuda**: Solicitação de ajuda mais recente desta person
    - **Histórico de Serviços**: Resumo de interações passadas
    """,
    responses={
        200: ProviderPersonSummarySerializer(many=True),
        401: {"description": "Authentication required"},
        404: {"description": "Provider profile not found or access denied"},
    },
)
class ProviderPersonsView(APIView):
    """
    Persons Vinculados do Provider com Informações de Resumo

    Recupera resumo abrangente de todos os persons vinculados ao provider autenticado.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        ip_address = request.META.get("REMOTE_ADDR", "Unknown")

        # VALIDAÇÃO DE SEGURANÇA: Só providers podem ver seus persons
        provider = validate_user_is_provider(user)
        provider_id = provider.provider_id

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
            # Use helper function to get linked persons
            _, linked_persons_ids = get_provider_and_linked_persons(user)

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
