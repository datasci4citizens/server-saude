from app_saude.models import Concept


def get_concept_by_code(concept_code: str) -> Concept:
    return Concept.objects.get(concept_code=concept_code)
