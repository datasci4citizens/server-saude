from app_saude.models import Concept


def get_concept_by_id(concept_id: int) -> Concept:
    print(f"Fetching concept with ID: {concept_id}")
    return Concept.objects.get(concept_id=concept_id)


def get_concept_by_code(concept_code: str) -> Concept:
    print(f"Fetching concept with code: {concept_code}")
    return Concept.objects.get(concept_code=concept_code)
