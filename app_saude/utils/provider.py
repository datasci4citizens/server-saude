from django.http import Http404
from django.shortcuts import get_object_or_404

from app_saude.models import FactRelationship, Person, Provider  # ajuste conforme necessário


def get_provider_and_linked_persons(request_user):
    """
    Retorna o provider logado e os IDs das pessoas vinculadas a ele.
    """
    provider = get_object_or_404(Provider, user=request_user)
    provider_id = provider.provider_id

    linked_person_ids = FactRelationship.objects.filter(
        fact_id_2=provider_id,
        domain_concept_1_id=9202,  # Person
        domain_concept_2_id=9201,  # Provider
        relationship_concept_id=9200001,  # Person linked to Provider
    ).values_list("fact_id_1", flat=True)

    return provider, set(linked_person_ids)


def get_provider_and_linked_person_or_404(request_user, person_id):
    """
    Valida se a pessoa está vinculada ao provider logado. Retorna a pessoa ou 404.
    """
    provider, linked_ids = get_provider_and_linked_persons(request_user)
    if int(person_id) not in linked_ids:
        raise Http404("Esta pessoa não está vinculada a este profissional.")
    return provider, Person.objects.get(pk=person_id)
