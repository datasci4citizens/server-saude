import logging

from django.http import Http404

from app_saude.models import Person

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
