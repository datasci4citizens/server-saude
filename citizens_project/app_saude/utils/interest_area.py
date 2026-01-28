# from app_saude.models import FactRelationship, Observation
# from app_saude.serializers import InterestAreaSerializer, InterestAreaTriggerSerializer
# from app_saude.utils.concept import get_concept_by_code


# def get_interest_areas_and_triggers(interest_areas: list):
#     results = []
#     for interest_area in interest_areas:
#         interest_data = InterestAreaSerializer(interest_area).data

#         relationships = FactRelationship.objects.filter(
#             domain_concept_1_id=get_concept_by_code("INTEREST_AREA").concept_id,
#             fact_id_1=interest_area.observation_id,
#             relationship_concept_id=get_concept_by_code("AOI_TRIGGER").concept_id,
#         )

#         trigger_ids = relationships.values_list("fact_id_2", flat=True)

#         # Searching for triggers related to the interest area
#         triggers = Observation.objects.filter(observation_id__in=trigger_ids).select_related("observation_concept")

#         interest_data["triggers"] = InterestAreaTriggerSerializer(triggers, many=True).data
#         results.append(interest_data)
#     return results
