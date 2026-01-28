import logging

from app_saude.models import FactRelationship, Person, Provider  # ajuste conforme necessário
from django.http import Http404
from django.shortcuts import get_object_or_404

from .concept import get_concept_by_code

logger = logging.getLogger(__name__)


def get_provider_and_linked_persons(request_user):
    """
    Retorna o provider logado e os IDs das pessoas vinculadas a ele.
    """
    provider = get_object_or_404(Provider, user=request_user)

    linked_persons_ids = FactRelationship.objects.filter(
        fact_id_2=provider.provider_id,
        domain_concept_1_id=get_concept_by_code("PERSON"),
        domain_concept_2_id=get_concept_by_code("PROVIDER"),
        relationship_concept_id=get_concept_by_code("PERSON_PROVIDER"),
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


def get_provider_full_name(provider_id):
    """
    Retorna o nome completo do provider.
    """
    print("get_provider_full_name", provider_id)
    provider = Provider.objects.filter(provider_id=provider_id).first()
    if provider:
        return provider.social_name if provider.social_name else provider.user.get_full_name()
    return None


def validate_user_is_provider(user):
    """
    Valida se o usuário tem perfil de Provider.
    Retorna o Provider ou levanta Http404.
    """
    try:
        return get_object_or_404(Provider, user=user)
    except Http404:
        logger.warning(
            "Acesso negado - usuário não é provider",
            extra={
                "user_id": user.id,
                "email": user.email,
                "action": "access_denied_not_provider",
            },
        )
        raise Http404("Acesso negado. Esta funcionalidade é exclusiva para profissionais.")
