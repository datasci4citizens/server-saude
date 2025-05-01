from django.contrib import admin

from .models import *

admin.site.register(Vocabulary)
admin.site.register(ConceptClass)
admin.site.register(Concept)
admin.site.register(ConceptSynonym)
admin.site.register(Domain)
admin.site.register(Location)
admin.site.register(Person)
admin.site.register(Provider)
admin.site.register(CareSite)
admin.site.register(DrugExposure)
admin.site.register(Observation)
admin.site.register(VisitOccurrence)
admin.site.register(Measurement)
admin.site.register(FactRelationship)
