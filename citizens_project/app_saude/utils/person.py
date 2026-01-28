import logging

from app_saude.models import FactRelationship, Person
from app_saude.utils.concept import get_concept_by_code
from django.http import Http404
from django.shortcuts import get_object_or_404

logger = logging.getLogger(__name__)


def get_person_or_404(user):
    """
    Valida se a pessoa existe. Retorna a pessoa ou 404.
    """
    person = Person.objects.filter(user=user).first()
    if not person:
        logger.error(f"Usuário {user} não vinculado a nenhuma pessoa.")
        raise Http404("Nenhuma pessoa está vinculada a este usuário.")
    return person


def get_person_and_linked_providers(request_user):
    """
    Retorna o person logado e os IDs dos providers vinculados a ele.
    """
    person = get_object_or_404(Person, user=request_user)

    linked_providers_ids = FactRelationship.objects.filter(
        fact_id_1=person.person_id,
        domain_concept_1_id=get_concept_by_code("PERSON").concept_id,
        domain_concept_2_id=get_concept_by_code("PROVIDER").concept_id,
        relationship_concept_id=get_concept_by_code("PERSON_PROVIDER").concept_id,
    ).values_list("fact_id_2", flat=True)

    return person, set(linked_providers_ids)


def validate_user_is_person(user):
    """
    Valida se o usuário tem perfil de Person.
    Retorna o Person ou levanta Http404.
    """
    try:
        return get_object_or_404(Person, user=user)
    except Http404:
        logger.warning(
            "Acesso negado - usuário não é person",
            extra={
                "user_id": user.id,
                "email": user.email,
                "action": "access_denied_not_person",
            },
        )
        raise Http404("Acesso negado. Esta funcionalidade é exclusiva para pacientes.")
